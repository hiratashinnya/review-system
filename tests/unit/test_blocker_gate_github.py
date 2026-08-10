"""GitHub read-only collector の pagination/error integration fixtures。"""

import base64
import json
from pathlib import Path
import tempfile
from typing import Any
import unittest

from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot
from pr_merge_gate.audit import append_decision
from pr_merge_gate.classifier import MergeOperation
from pr_merge_gate.gate import evaluate_merge_operation


def response(
    value: Any, headers: Any = None, status: int = 200
) -> tuple[int, Any, bytes]:
    return status, headers or {}, json.dumps(value).encode("utf-8")


class FakeTransport:
    def __init__(self, responses, post_responses=()):
        self.responses = responses
        self.post_responses = list(post_responses)
        self.get_calls = []
        self.post_calls = []

    def get(self, url, headers):
        self.get_calls.append((url, dict(headers)))
        return self.responses[url]

    def post(self, url, headers, body):
        self.post_calls.append((url, dict(headers), body))
        if self.post_responses:
            return self.post_responses.pop(0)
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
        "title": "PR title",
        "body": "",
        "headRefName": "topic",
        "headRepositoryOwner": {"login": "example"},
        "commits": {"totalCount": 1},
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


WAIVER_POLICY = b"schema: blocker-gate-policy/v1\n"
WAIVER_FILE = b"schema: blocker-gate-waiver/v1\n"
WAIVER_PATH = ".github/blocker-gate/waivers/BW-20260801-001.yml"


def signature_page(
    approval: str,
    *,
    oid: Any = None,
    is_valid: Any = True,
    state: Any = "VALID",
    signer_login: Any = "owner-login",
    was_signed_by_github: Any = False,
):
    signer = None if signer_login is None else {"login": signer_login}
    return {
        "data": {
            "repository": {
                "nameWithOwner": "example/repo",
                "object": {
                    "oid": approval if oid is None else oid,
                    "signature": {
                        "isValid": is_valid,
                        "state": state,
                        "signer": signer,
                        "wasSignedByGitHub": was_signed_by_github,
                    },
                },
            }
        }
    }


def waiver_transport(*, rules=None, rulesets=None, signature=None):
    api = "https://api.github.com/repos/example/repo"
    head, tree, policy_sha, waiver_sha, approval = (
        "0" * 40,
        "1" * 40,
        "2" * 40,
        "3" * 40,
        "4" * 40,
    )
    branch_rules = [
        {
            "type": "deletion",
            "ruleset_source_type": "Repository",
            "ruleset_source": "example/repo",
            "ruleset_id": 7,
        },
        {
            "type": "non_fast_forward",
            "ruleset_source_type": "Repository",
            "ruleset_source": "example/repo",
            "ruleset_id": 7,
        },
    ]
    if rules is not None:
        branch_rules = rules
    rule_details = {
        7: {
            "id": 7,
            "target": "branch",
            "source_type": "Repository",
            "source": "example/repo",
            "enforcement": "active",
            "bypass_actors": [],
            "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
        }
    }
    if rulesets is not None:
        rule_details = rulesets
    responses = {
        api: response(
            {
                "full_name": "example/repo",
                "node_id": "R1",
                "default_branch": "main",
            }
        ),
        api + "/git/ref/heads/main": response(
            {"ref": "refs/heads/main", "object": {"type": "commit", "sha": head}}
        ),
        api + f"/git/commits/{head}": response(
            {"sha": head, "tree": {"sha": tree}}
        ),
        api + f"/git/trees/{tree}?recursive=1": response(
            {
                "sha": tree,
                "truncated": False,
                "tree": [
                    {
                        "path": ".github/blocker-gate/policy.yml",
                        "type": "blob",
                        "sha": policy_sha,
                    },
                    {"path": WAIVER_PATH, "type": "blob", "sha": waiver_sha},
                ],
            }
        ),
        api + f"/git/blobs/{policy_sha}": response(
            {
                "sha": policy_sha,
                "encoding": "base64",
                "content": base64.b64encode(WAIVER_POLICY).decode("ascii"),
            }
        ),
        api + f"/git/blobs/{waiver_sha}": response(
            {
                "sha": waiver_sha,
                "encoding": "base64",
                "content": base64.b64encode(WAIVER_FILE).decode("ascii"),
            }
        ),
        api + "/rules/branches/main?per_page=100": response(branch_rules),
        api
        + f"/commits?path=.github%2Fblocker-gate%2Fwaivers%2FBW-20260801-001.yml&sha={head}&per_page=1": response(
            [
                {
                    "sha": approval,
                    "author": {"login": "spoofed-author"},
                    "commit": {"verification": {"verified": True}},
                }
            ]
        ),
        api + f"/compare/{approval}...{head}": response({"status": "ahead"}),
    }
    for ruleset_id, ruleset in rule_details.items():
        responses[
            api + f"/rulesets/{ruleset_id}?includes_parents=true"
        ] = response(ruleset)
    return FakeTransport(
        responses,
        post_responses=(
            response(signature_page(approval) if signature is None else signature),
        ),
    )


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
            ((401, {}, b"{}"), "API_PERMISSION"),
            ((403, {}, b"{}"), "API_PERMISSION"),
            ((403, {"X-RateLimit-Remaining": "0"}, b"{}"), "API_UNAVAILABLE"),
            ((403, {"x-ratelimit-remaining": "0"}, b"{}"), "API_UNAVAILABLE"),
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
        self.assertEqual(
            [name for name, value in headers.items() if "secret" in value],
            ["Authorization"],
        )

    def test_graphql_rate_limit_exhaustion_is_api_unavailable(self):
        transport = FakeTransport(
            {},
            post_responses=[
                (403, {"X-RateLimit-Remaining": "0"}, b'{"message":"rate limit"}')
            ],
        )
        snapshot = GitHubCollector("graphql-secret", transport).collect_pull_request(
            "example/repo", 50, "rebase"
        )
        result = evaluate_snapshot(snapshot)
        self.assertEqual((result["result"], result["primary_reason"]), ("ERROR", "API_UNAVAILABLE"))
        self.assertNotIn("graphql-secret", json.dumps(snapshot) + json.dumps(result))
        self.assertNotIn("graphql-secret", transport.post_calls[0][2].decode("utf-8"))

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
        transport = waiver_transport()
        collection = GitHubCollector(None, transport).collect_waiver_materials("example/repo")
        self.assertEqual(collection.errors, ())
        self.assertEqual(len(collection.materials), 1)
        material = collection.materials[0]
        self.assertEqual(
            (material.policy_bytes, material.waiver_bytes),
            (WAIVER_POLICY, WAIVER_FILE),
        )
        self.assertEqual(
            (material.evidence.default_branch, material.evidence.default_head),
            ("main", "0" * 40),
        )
        self.assertTrue(material.evidence.signature_verified)
        self.assertTrue(material.evidence.history_bypass_free)
        self.assertEqual(material.evidence.signer_login, "owner-login")
        self.assertTrue(transport.post_calls)

    def test_waiver_signer_is_bound_to_graphql_signature_not_rest_author(self):
        transport = waiver_transport(
            signature=signature_page("4" * 40, signer_login="different-signer")
        )
        collection = GitHubCollector(None, transport).collect_waiver_materials(
            "example/repo"
        )
        self.assertEqual(collection.errors, ())
        self.assertEqual(
            collection.materials[0].evidence.signer_login, "different-signer"
        )

    def test_signature_null_unknown_and_oid_mismatch_fail_close(self):
        signatures = (
            signature_page("4" * 40, signer_login=None),
            signature_page("4" * 40, state="UNKNOWN"),
            signature_page("4" * 40, is_valid=False),
            signature_page("4" * 40, is_valid="true"),
            signature_page("4" * 40, was_signed_by_github=None),
            signature_page("4" * 40, oid="5" * 40),
        )
        for signature in signatures:
            with self.subTest(signature=signature):
                collection = GitHubCollector(
                    None, waiver_transport(signature=signature)
                ).collect_waiver_materials("example/repo")
                self.assertTrue(collection.errors)
                self.assertEqual(collection.materials, ())

    def test_branch_rules_must_form_one_closed_ruleset_identity(self):
        repository_rule = {
            "ruleset_source_type": "Repository",
            "ruleset_source": "example/repo",
        }
        cases = (
            [
                {"type": "deletion", **repository_rule},
                {
                    "type": "non_fast_forward",
                    **repository_rule,
                    "ruleset_id": 7,
                },
            ],
            [
                {"type": "deletion", **repository_rule, "ruleset_id": 7},
                {
                    "type": "non_fast_forward",
                    **repository_rule,
                    "ruleset_id": 8,
                },
            ],
            [
                {"type": "deletion", **repository_rule, "ruleset_id": 7},
                {
                    "type": "non_fast_forward",
                    **repository_rule,
                    "ruleset_id": 7,
                },
                {"type": "future_unknown_rule", **repository_rule, "ruleset_id": 7},
            ],
            [
                {
                    "type": "deletion",
                    "ruleset_source_type": "Repository",
                    "ruleset_source": "other/repo",
                    "ruleset_id": 7,
                },
                {
                    "type": "non_fast_forward",
                    **repository_rule,
                    "ruleset_id": 7,
                },
            ],
            [
                {"type": "deletion", **repository_rule, "ruleset_id": True},
                {
                    "type": "non_fast_forward",
                    **repository_rule,
                    "ruleset_id": True,
                },
            ],
        )
        for rules in cases:
            with self.subTest(rules=rules):
                collection = GitHubCollector(
                    None, waiver_transport(rules=rules)
                ).collect_waiver_materials("example/repo")
                if all("ruleset_id" in rule for rule in rules) and len(
                    {rule["ruleset_id"] for rule in rules}
                ) > 1:
                    self.assertEqual(collection.errors, ())
                    proof = collection.materials[0].evidence
                    self.assertFalse(proof.deletion_protected)
                    self.assertFalse(proof.non_fast_forward_protected)
                else:
                    self.assertEqual(
                        collection.errors, ("API_PARTIAL_RESPONSE",)
                    )
                    self.assertEqual(collection.materials, ())

    def test_ruleset_detail_must_match_source_and_be_active_without_bypass(self):
        base = {
            "id": 7,
            "target": "branch",
            "source_type": "Repository",
            "source": "example/repo",
            "enforcement": "active",
            "bypass_actors": [],
            "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
        }
        cases = (
            {**base, "source": "other/repo"},
            {**base, "enforcement": "evaluate"},
            {**base, "bypass_actors": [{"actor_type": "Team"}]},
            {**base, "rules": [{"type": "deletion"}]},
        )
        for ruleset in cases:
            with self.subTest(ruleset=ruleset):
                collection = GitHubCollector(
                    None, waiver_transport(rulesets={7: ruleset})
                ).collect_waiver_materials("example/repo")
                if (
                    ruleset["source"] == "example/repo"
                    and ruleset["rules"]
                    == [{"type": "deletion"}, {"type": "non_fast_forward"}]
                ):
                    self.assertEqual(collection.errors, ())
                    proof = collection.materials[0].evidence
                    self.assertFalse(
                        proof.ruleset_active
                        and proof.history_bypass_free
                        and proof.deletion_protected
                        and proof.non_fast_forward_protected
                    )
                else:
                    self.assertEqual(
                        collection.errors, ("API_PARTIAL_RESPONSE",)
                    )

    def test_unverified_squash_commit_messages_setting_fails_closed(self):
        api = "https://api.github.com/repos/example/repo"
        transport = GraphQLTransport([pr_page(baseRefName="main", headRefOid="1" * 40)])
        transport.responses.update(
            {
                api: response(
                    {
                        "full_name": "example/repo",
                        "node_id": "R1",
                        "squash_merge_commit_title": "PR_TITLE",
                        "squash_merge_commit_message": "COMMIT_MESSAGES",
                    }
                ),
                api + "/pulls/50/commits?per_page=100": response(
                    [
                        {
                            "sha": "1" * 40,
                            "commit": {
                                "message": "Fixes: #7",
                                "tree": {"sha": "2" * 40},
                            },
                            "parents": [],
                        }
                    ]
                ),
                api + "/issues/7": response(
                    {
                        "number": 7,
                        "node_id": "I7",
                        "state": "open",
                        "state_reason": None,
                        "parent_issue_url": None,
                        "repository_url": api,
                    }
                ),
                api + "/issues/7/dependencies/blocked_by?per_page=100": response([]),
                api + "/issues/7/sub_issues?per_page=100": response([]),
            }
        )

        snapshot = GitHubCollector(None, transport).collect_pull_request(
            "example/repo", 50, "squash"
        )
        result = evaluate_snapshot(snapshot)

        self.assertEqual(snapshot["graphql_closing_set"], [])
        self.assertEqual(snapshot["delivered_message_closing_set"], [])
        self.assertEqual(snapshot["roots"], [])
        self.assertIn("MERGE_MESSAGE_AMBIGUOUS", snapshot["errors"])
        self.assertEqual((result["result"], result["permit_issued"]), ("ERROR", False))
        self.assertEqual(result["binding"]["pr_state"], "OPEN")
        self.assertFalse(result["binding"]["pr_is_draft"])
        self.assertIsNotNone(
            snapshot["binding"]["repository_merge_settings_fingerprint"]
        )

    def test_default_branch_commit_tail_must_equal_graphql_head(self):
        api = "https://api.github.com/repos/example/repo"
        transport = GraphQLTransport(
            [pr_page(baseRefName="main", headRefOid="0" * 40)]
        )
        transport.responses[
            api + "/pulls/50/commits?per_page=100"
        ] = response(
            [
                {
                    "sha": "1" * 40,
                    "commit": {"message": "message", "tree": {"sha": "2" * 40}},
                    "parents": [],
                }
            ]
        )
        snapshot = GitHubCollector(None, transport).collect_pull_request(
            "example/repo", 50, "rebase"
        )
        result = evaluate_snapshot(snapshot)
        self.assertIn("IDENTITY_MISMATCH", snapshot["errors"])
        self.assertEqual((result["result"], result["permit_issued"]), ("ERROR", False))

    def test_default_branch_commit_source_must_be_complete_and_fully_paginated(self):
        api = "https://api.github.com/repos/example/repo"
        commits_url = api + "/pulls/50/commits?per_page=100"
        cases = (
            ("empty", response([]), "MESSAGE_SOURCE_INCOMPLETE"),
            (
                "partial",
                response(
                    [
                        {
                            "sha": "1" * 40,
                            "commit": {"message": "message"},
                            "parents": [],
                        }
                    ]
                ),
                "MESSAGE_SOURCE_INCOMPLETE",
            ),
            (
                "pagination-cycle",
                response(
                    [
                        {
                            "sha": "1" * 40,
                            "commit": {
                                "message": "message",
                                "tree": {"sha": "2" * 40},
                            },
                            "parents": [],
                        }
                    ],
                    {"Link": f'<{commits_url}>; rel="next"'},
                ),
                "PAGINATION_INCOMPLETE",
            ),
        )
        for label, commits_response, reason in cases:
            with self.subTest(label=label):
                transport = GraphQLTransport(
                    [pr_page(baseRefName="main", headRefOid="1" * 40)]
                )
                transport.responses[commits_url] = commits_response
                snapshot = GitHubCollector(None, transport).collect_pull_request(
                    "example/repo", 50, "rebase"
                )
                result = evaluate_snapshot(snapshot)
                self.assertIn(reason, snapshot["errors"])
                self.assertEqual(
                    (result["result"], result["permit_issued"]),
                    ("ERROR", False),
                )

    def test_commit_total_count_rejects_missing_middle_and_duplicate_but_allows_full_pages(self):
        api = "https://api.github.com/repos/example/repo"
        commits_url = api + "/pulls/50/commits?per_page=100"
        second_url = commits_url + "&page=2"

        def item(character):
            return {
                "sha": character * 40,
                "commit": {
                    "message": f"message-{character}",
                    "tree": {"sha": "f" * 40},
                },
                "parents": [],
            }

        for label, commit_items, reason in (
            ("missing-middle", [item("a"), item("c")], "IDENTITY_MISMATCH"),
            ("duplicate", [item("a"), item("c"), item("c")], "MESSAGE_SOURCE_INCOMPLETE"),
        ):
            with self.subTest(label=label):
                transport = GraphQLTransport(
                    [
                        pr_page(
                            baseRefName="main",
                            headRefOid="c" * 40,
                            commits={"totalCount": 3},
                        )
                    ]
                )
                transport.responses[commits_url] = response(commit_items)
                snapshot = GitHubCollector(None, transport).collect_pull_request(
                    "example/repo", 50, "rebase"
                )
                result = evaluate_snapshot(snapshot)
                self.assertIn(reason, snapshot["errors"])
                self.assertEqual(result["result"], "ERROR")
                self.assertEqual(result["binding"]["expected_commit_count"], 3)

        transport = GraphQLTransport(
            [
                pr_page(
                    baseRefName="main",
                    headRefOid="c" * 40,
                    commits={"totalCount": 3},
                )
            ]
        )
        transport.responses[commits_url] = response(
            [item("a"), item("b")],
            {"Link": f'<{second_url}>; rel="next"'},
        )
        transport.responses[second_url] = response([item("c")])
        result = evaluate_snapshot(
            GitHubCollector(None, transport).collect_pull_request(
                "example/repo", 50, "rebase"
            )
        )
        self.assertEqual((result["result"], result["permit_issued"]), ("ALLOW", True))
        self.assertEqual(result["binding"]["expected_commit_count"], 3)

    def test_graphql_total_count_is_known_and_stable_and_page_errors_preserve_page1_binding(self):
        first_connection = {
            "nodes": [],
            "pageInfo": {"hasNextPage": True, "endCursor": "C1"},
        }
        next_connection = {
            "nodes": [],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
        first = pr_page(
            baseRefName="main",
            headRefOid="a" * 40,
            commits={"totalCount": 2},
            closingIssuesReferences=first_connection,
        )
        cases = (
            (
                "api-error",
                [first, {"errors": [{"type": "FORBIDDEN"}]}],
                "API_PARTIAL_RESPONSE",
            ),
            (
                "cursor-cycle",
                [
                    first,
                    pr_page(
                        baseRefName="main",
                        headRefOid="a" * 40,
                        commits={"totalCount": 2},
                        closingIssuesReferences=first_connection,
                    ),
                ],
                "PAGINATION_INCOMPLETE",
            ),
            (
                "head-change",
                [
                    first,
                    pr_page(
                        baseRefName="main",
                        headRefOid="b" * 40,
                        commits={"totalCount": 2},
                        closingIssuesReferences=next_connection,
                    ),
                ],
                "IDENTITY_MISMATCH",
            ),
            (
                "count-change",
                [
                    first,
                    pr_page(
                        baseRefName="main",
                        headRefOid="a" * 40,
                        commits={"totalCount": 3},
                        closingIssuesReferences=next_connection,
                    ),
                ],
                "IDENTITY_MISMATCH",
            ),
        )
        for label, pages, reason in cases:
            with self.subTest(label=label):
                snapshot = GitHubCollector(
                    None, GraphQLTransport(pages)
                ).collect_pull_request("example/repo", 50, "rebase")
                result = evaluate_snapshot(snapshot)
                self.assertIn(reason, snapshot["errors"])
                self.assertFalse(snapshot["pages_complete"])
                self.assertEqual((result["result"], result["mode"]), ("ERROR", "pr-merge"))
                self.assertEqual(result["binding"]["head_oid"], "a" * 40)
                self.assertEqual(result["binding"]["base_ref_name"], "main")
                self.assertEqual(result["binding"]["default_branch"], "main")
                self.assertEqual(result["binding"]["expected_commit_count"], 2)
                self.assertEqual(result["binding"]["pr_state"], "OPEN")
                self.assertFalse(result["binding"]["pr_is_draft"])
                self.assertFalse(result["permit_issued"])

        unknown_count = GitHubCollector(
            None,
            GraphQLTransport(
                [pr_page(commits={"totalCount": None})]
            ),
        ).collect_pull_request("example/repo", 50, "rebase")
        self.assertIn("API_PARTIAL_RESPONSE", unknown_count["errors"])
        self.assertFalse(evaluate_snapshot(unknown_count)["permit_issued"])

    def test_partial_graphql_binding_flows_through_gate_and_audit_as_error_evidence(self):
        operation_fp = "sha256:" + "1" * 64
        first = pr_page(
            baseRefName="main",
            headRefOid="a" * 40,
            commits={"totalCount": 2},
            closingIssuesReferences={
                "nodes": [],
                "pageInfo": {"hasNextPage": True, "endCursor": "C1"},
            },
        )
        snapshot = GitHubCollector(
            None,
            GraphQLTransport([first, {"errors": [{"type": "FORBIDDEN"}]}]),
        ).collect_pull_request(
            "example/repo",
            50,
            "rebase",
            operation_fingerprint=operation_fp,
        )

        class SnapshotCollector:
            def collect_pull_request(self, *args, **kwargs):
                return snapshot

        gate_evidence = evaluate_merge_operation(
            MergeOperation(
                "example/repo",
                50,
                "rebase",
                "cli-direct",
                None,
                None,
                None,
                operation_fp,
            ),
            collector_factory=lambda token: SnapshotCollector(),
        )
        self.assertEqual((gate_evidence["result"], gate_evidence["reason"]), (
            "ERROR", "API_PARTIAL_RESPONSE"
        ))
        gate_evidence.update(
            {
                "classifier_version": "1.5",
                "hook_asset_hash": "sha256:" + "9" * 64,
                "hook_event_id": "tool-partial",
                "invocation_id": "invocation-partial",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(gate_evidence, path=target)
            record = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(record["blocker_result"], "ERROR")
        self.assertEqual(record["head_oid"], "a" * 40)
        self.assertEqual(record["expected_commit_count"], 2)
        self.assertEqual(record["base_ref_name"], "main")
        self.assertEqual(record["default_branch"], "main")
        self.assertEqual(record["pr_state"], "OPEN")
        self.assertFalse(record["pr_is_draft"])
        self.assertFalse(record["permit_issued"])
        self.assertFalse(record["operation_dispatched"])
        self.assertFalse(record["merge_api_called"])

    def test_head_and_commit_tail_change_together_changes_fresh_binding(self):
        api = "https://api.github.com/repos/example/repo"

        class ChangingCommitsTransport(GraphQLTransport):
            def __init__(self):
                super().__init__(
                    [
                        pr_page(baseRefName="main", headRefOid="a" * 40),
                        pr_page(baseRefName="main", headRefOid="b" * 40),
                    ]
                )
                self.commit_batches = ["a" * 40, "b" * 40]

            def get(self, url, headers):
                self.get_calls.append((url, dict(headers)))
                if url == api + "/pulls/50/commits?per_page=100":
                    oid = self.commit_batches.pop(0)
                    return response(
                        [
                            {
                                "sha": oid,
                                "commit": {
                                    "message": f"message-{oid[0]}",
                                    "tree": {"sha": "2" * 40},
                                },
                                "parents": [],
                            }
                        ]
                    )
                raise AssertionError(url)

        collector = GitHubCollector(None, ChangingCommitsTransport())
        first = evaluate_snapshot(
            collector.collect_pull_request("example/repo", 50, "rebase")
        )
        second = evaluate_snapshot(
            collector.collect_pull_request("example/repo", 50, "rebase")
        )
        self.assertEqual((first["result"], second["result"]), ("ALLOW", "ALLOW"))
        self.assertNotEqual(first["binding"]["head_oid"], second["binding"]["head_oid"])
        self.assertNotEqual(
            first["binding"]["message_source_fingerprint"],
            second["binding"]["message_source_fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
