"""GitHub read-only collector の pagination/error integration fixtures。"""

import base64
import json
import unittest

from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot


def response(value, headers=None, status=200):
    return status, headers or {}, json.dumps(value).encode("utf-8")


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.get_calls = []
        self.post_calls = []

    def get(self, url, headers):
        self.get_calls.append((url, dict(headers)))
        return self.responses[url]

    def post(self, url, headers, body):
        self.post_calls.append((url, dict(headers), body))
        return self.responses[(url, body)]


class GraphQLTransport(FakeTransport):
    def __init__(self, pages):
        super().__init__({})
        self.pages = list(pages)

    def post(self, url, headers, body):
        self.post_calls.append((url, dict(headers), body))
        return response(self.pages.pop(0))


def pr_page(**overrides):
    pr = {
        "id": "PR50",
        "number": 50,
        "state": "OPEN",
        "isDraft": False,
        "headRefOid": "0" * 40,
        "baseRefName": "release",
        "closingIssuesReferences": {
            "nodes": [],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        },
    }
    pr.update(overrides)
    return {
        "data": {
            "repository": {
                "id": "R1",
                "nameWithOwner": "example/repo",
                "defaultBranchRef": {"name": "main"},
                "pullRequest": pr,
            }
        }
    }


class GitHubCollectorTests(unittest.TestCase):
    def test_rest_relation_pagination_is_completed(self):
        base = "https://api.github.com/repos/example/repo/issues"
        blocker_page_2 = base + "/10/dependencies/blocked_by?per_page=100&page=2"
        transport = FakeTransport(
            {
                base + "/10": response({"number": 10, "node_id": "I10", "state": "open", "state_reason": None, "parent_issue_url": None, "repository_url": "https://api.github.com/repos/example/repo"}),
                base + "/10/dependencies/blocked_by?per_page=100": response([], {"Link": f'<{blocker_page_2}>; rel="next"'}),
                blocker_page_2: response([{"number": 9, "repository_url": "https://api.github.com/repos/example/repo"}]),
                base + "/10/sub_issues?per_page=100": response([]),
                base + "/9": response({"number": 9, "node_id": "I9", "state": "closed", "state_reason": "completed", "parent_issue_url": None, "repository_url": "https://api.github.com/repos/example/repo"}),
                base + "/9/dependencies/blocked_by?per_page=100": response([]),
                base + "/9/sub_issues?per_page=100": response([]),
            }
        )
        snapshot = GitHubCollector("token", transport).collect_issue("example/repo", 10)
        self.assertTrue(snapshot["pages_complete"])
        self.assertEqual(snapshot["nodes"]["example/repo#10"]["blocked_by"], ["example/repo#9"])
        self.assertIn(blocker_page_2, [call[0] for call in transport.get_calls])
        result = evaluate_snapshot(snapshot)
        self.assertEqual(result["result"], "ALLOW")

    def test_permission_and_invalid_json_are_error_not_empty_graph(self):
        url = "https://api.github.com/repos/example/repo/issues/10"
        cases = (
            ((403, {}, b"{}"), "API_PERMISSION"),
            ((200, {}, b"not-json"), "API_PARTIAL_RESPONSE"),
        )
        for raw, reason in cases:
            with self.subTest(reason=reason):
                transport = FakeTransport({url: raw})
                snapshot = GitHubCollector(None, transport).collect_issue("example/repo", 10)
                self.assertIn(reason, snapshot["errors"])
                result = evaluate_snapshot(snapshot)
                self.assertEqual(result["result"], "ERROR")
                self.assertFalse(result["permit_issued"])

    def test_api_version_and_authorization_headers_are_bound(self):
        url = "https://api.github.com/repos/example/repo/issues/10"
        transport = FakeTransport({url: (403, {}, b"{}")})
        GitHubCollector("secret", transport).collect_issue("example/repo", 10)
        headers = transport.get_calls[0][1]
        self.assertEqual(headers["X-GitHub-Api-Version"], "2026-03-10")
        self.assertEqual(headers["Authorization"], "Bearer secret")

    def test_pr_identity_binding_is_closed_and_consistent_on_every_cursor(self):
        valid = GitHubCollector(None, GraphQLTransport([pr_page()])).collect_pull_request(
            "example/repo", 50, "rebase"
        )
        allowed = evaluate_snapshot(valid)
        self.assertEqual(
            (allowed["result"], allowed["primary_reason"]),
            ("ALLOW", "NO_CLOSING_EFFECT"),
        )
        for mutation in (
            {"headRefOid": None},
            {"baseRefName": None},
            {"id": None},
            {"number": 51},
        ):
            with self.subTest(mutation=mutation):
                snapshot = GitHubCollector(
                    None, GraphQLTransport([pr_page(**mutation)])
                ).collect_pull_request("example/repo", 50, "rebase")
                result = evaluate_snapshot(snapshot)
                self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
                self.assertFalse(result["permit_issued"])

        missing_default = pr_page()
        missing_default["data"]["repository"]["defaultBranchRef"] = {"name": None}
        result = evaluate_snapshot(
            GitHubCollector(
                None, GraphQLTransport([missing_default])
            ).collect_pull_request("example/repo", 50, "rebase")
        )
        self.assertEqual(result["result"], "ERROR")
        self.assertFalse(result["permit_issued"])

        first = pr_page()
        first["data"]["repository"]["pullRequest"]["closingIssuesReferences"]["pageInfo"] = {
            "hasNextPage": True,
            "endCursor": "cursor-1",
        }
        inconsistent = GitHubCollector(
            None, GraphQLTransport([first, pr_page(headRefOid="1" * 40)])
        ).collect_pull_request("example/repo", 50, "rebase")
        result = evaluate_snapshot(inconsistent)
        self.assertEqual(result["result"], "ERROR")
        self.assertFalse(result["permit_issued"])

    def test_waiver_materials_are_read_from_fresh_default_head_and_rules(self):
        api = "https://api.github.com/repos/example/repo"
        head, tree, policy_sha, waiver_sha, approval = (
            "0" * 40,
            "1" * 40,
            "2" * 40,
            "3" * 40,
            "4" * 40,
        )
        policy = b"schema: blocker-gate-policy/v1\n"
        waiver = b"schema: blocker-gate-waiver/v1\n"
        waiver_path = ".github/blocker-gate/waivers/BW-20260801-001.yml"
        transport = FakeTransport(
            {
                api: response({"full_name": "example/repo", "node_id": "R1", "default_branch": "main"}),
                api + "/git/ref/heads/main": response({"ref": "refs/heads/main", "object": {"type": "commit", "sha": head}}),
                api + f"/git/commits/{head}": response({"sha": head, "tree": {"sha": tree}}),
                api + f"/git/trees/{tree}?recursive=1": response(
                    {
                        "sha": tree,
                        "truncated": False,
                        "tree": [
                            {"path": ".github/blocker-gate/policy.yml", "type": "blob", "sha": policy_sha},
                            {"path": waiver_path, "type": "blob", "sha": waiver_sha},
                        ],
                    }
                ),
                api + f"/git/blobs/{policy_sha}": response(
                    {"sha": policy_sha, "encoding": "base64", "content": base64.b64encode(policy).decode("ascii")}
                ),
                api + f"/git/blobs/{waiver_sha}": response(
                    {"sha": waiver_sha, "encoding": "base64", "content": base64.b64encode(waiver).decode("ascii")}
                ),
                api + "/rules/branches/main": response(
                    [
                        {"type": "deletion", "ruleset_id": 7},
                        {"type": "non_fast_forward", "ruleset_id": 7},
                    ]
                ),
                api + "/rulesets/7": response(
                    {"id": 7, "enforcement": "active", "bypass_actors": []}
                ),
                api + f"/commits?path=.github%2Fblocker-gate%2Fwaivers%2FBW-20260801-001.yml&sha={head}&per_page=1": response(
                    [
                        {
                            "sha": approval,
                            "author": {"login": "owner-login"},
                            "commit": {"verification": {"verified": True}},
                        }
                    ]
                ),
                api + f"/compare/{approval}...{head}": response({"status": "ahead"}),
            }
        )
        collection = GitHubCollector(None, transport).collect_waiver_materials("example/repo")
        self.assertEqual(collection.errors, ())
        self.assertEqual(len(collection.materials), 1)
        material = collection.materials[0]
        self.assertEqual((material.policy_bytes, material.waiver_bytes), (policy, waiver))
        self.assertEqual(
            (material.evidence.default_branch, material.evidence.default_head),
            ("main", head),
        )
        self.assertTrue(material.evidence.signature_verified)
        self.assertTrue(material.evidence.history_bypass_free)


if __name__ == "__main__":
    unittest.main()
