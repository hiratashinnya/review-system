import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from pr_merge_gate.classifier import (
    CLASSIFIER_VERSION,
    classify_pre_use,
    repository_from_cwd,
)


def bash(command, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return payload


class PreUseClassifierTests(unittest.TestCase):
    def test_actual_fire_fixture_payloads_match_frozen_classifier_expectations(self):
        fixture = json.loads(
            (
                Path(__file__).parents[1]
                / "fixtures"
                / "pr_merge_actual_fire_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            fixture["schema_version"],
            "pr-merge-actual-fire-probes/1",
        )
        self.assertEqual(
            fixture["expected_audit"]["schema_version"],
            "pr-merge-audit/4",
        )
        self.assertEqual(
            fixture["expected_audit"]["classifier_version"],
            CLASSIFIER_VERSION,
        )
        for probe in fixture["probes"]:
            with self.subTest(probe=probe["id"]):
                classified = classify_pre_use(probe["payload"])
                self.assertEqual(
                    (classified.kind, classified.reason),
                    (
                        probe["expected_classifier"]["kind"],
                        probe["expected_classifier"]["reason"],
                    ),
                )

    def test_direct_wrapped_and_global_repo_cli_are_bound(self):
        cases = (
            ("gh -R example/repo pr merge 12 --squash --match-head-commit " + "a" * 40, "cli-direct"),
            ("rtk proxy command -- gh pr merge 12 --repo example/repo --rebase", "cli-wrapped"),
        )
        for command, transport in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(classified.kind, "merge")
                self.assertEqual(classified.operation.repository, "example/repo")
                self.assertEqual(classified.operation.pr_number, 12)
                self.assertEqual(classified.operation.transport, transport)

    def test_method_omission_auto_merge_and_shell_bypass_fail_close(self):
        cases = (
            ("gh -R example/repo pr merge 12", "error", "MERGE_METHOD_UNKNOWN"),
            ("gh -R example/repo pr merge 12 --squash --auto", "block", "AUTO_MERGE_DENIED"),
            ("gh -R example/repo pr merge 12 --squash; true", "error", "CLASSIFIER_UNKNOWN"),
        )
        for command, kind, reason in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual((classified.kind, classified.reason), (kind, reason))

    def test_token_normalization_closes_quote_escape_and_endpoint_bypasses(self):
        cases = (
            'gh -R example/repo pr "merge" 12 --squash',
            "gh -R example/repo pr mer\\ge 12 --squash",
            'gh api -X PUT repos/example/repo/pulls/12/mer""ge -f merge_method=squash',
        )
        for command in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(classified.kind, "merge")

    def test_unknown_alias_wrapper_and_merge_like_extension_fail_close(self):
        cases = (
            "gh alias exec land pr merge 12 --squash",
            "custom-wrapper gh -R example/repo pr merge 12 --squash",
            "gh extension exec land example/repo#12",
        )
        for command in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )

    def test_dynamic_alias_merge_shape_fails_closed_but_clear_nonmerge_passes(self):
        for command in (
            "$GH pr merge 12 --squash",
            "g pr merge 12 --squash",
            "g -R example/repo pr merge 12 --rebase",
            "$GM merge 12 --squash",
            "${GM} merge 12 --rebase",
            "GM merge 12 --squash",
            "GM='gh pr' $GM merge 12 --squash",
            "env GM='gh pr' $GM merge 12 --squash",
            "command -- $GM merge 12 --squash",
            "g merge 12 --squash",
            "bash -c 'g merge 12 --squash'",
            "function g(){ gh pr \"$@\"; }; g merge 12 --squash",
        ):
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )
        self.assertIsNone(classify_pre_use(bash("echo pr merge")))
        self.assertIsNone(classify_pre_use(bash("echo merge 12 --squash")))
        self.assertIsNone(classify_pre_use(bash("git merge 12 --squash")))
        self.assertIsNone(classify_pre_use(bash("git status")))

    def test_dynamic_evaluation_and_merge_arguments_fail_closed_at_expansion_boundary(self):
        unsafe = (
            '$CMD',
            '${CMD}',
            'command -- "$CMD"',
            'env CMD=ignored $CMD',
            'eval "$CMD"',
            'bash -c "$CMD"',
            "sh -lc '${CMD}'",
            'bash script.sh',
            'gh api -X PUT "$ENDPOINT" -f merge_method=squash',
            'gh api -X PUT repos/o/r/pulls/12/"$ACTION" -f merge_method=squash',
            'gh api -X PUT repos/o/r/pulls/12/merge -f merge_method=squash -f commit_message="$BODY"',
            'gh api graphql -f query="$QUERY"',
            'g api "$ENDPOINT"',
            'g "$GROUP" "$COMMAND"',
        )
        for command in unsafe:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertIsNotNone(classified)
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )

        safe = (
            'echo "$CMD"',
            'printf "%s\\n" "$BODY"',
            'git show "$REF"',
            'env VALUE=literal echo "$VALUE"',
            "eval 'echo literal'",
            "bash -c 'echo \"$HOME\"'",
            "bash -c 'gh issue view \"$ISSUE\"'",
            "gh issue view \"$ISSUE\"",
            "gh api user -f 'literal=$BODY'",
        )
        for command in safe:
            with self.subTest(command=command):
                self.assertIsNone(classify_pre_use(bash(command)))

    def test_shell_control_alias_and_substitution_fixture_is_closed(self):
        fixture = json.loads(
            (
                Path(__file__).parents[1]
                / "fixtures"
                / "pr_merge_classifier_shell_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(fixture["schema_version"], "pr-merge-classifier-shell-corpus/1")
        self.assertEqual(fixture["classifier_version"], CLASSIFIER_VERSION)
        case_ids = {case["id"] for case in fixture["cases"]}
        self.assertTrue(
            {
                "git-bisect-run-gh-merge",
                "safe-git-bisect-run-literal",
                "trusted-absolute-git-bisect-run-shell-merge",
                "trusted-absolute-git-shell-alias-merge",
                "safe-trusted-absolute-git-status",
                "safe-trusted-absolute-git-bisect-run-literal",
                "ambiguous-relative-git-status",
                "ambiguous-untrusted-absolute-git-bisect-run",
                "absolute-bash-command-string-merge",
                "safe-absolute-bash-literal",
                "ambiguous-path-qualified-shell-like-command",
                "git-rebase-attached-abbreviated-long-exec",
                "git-clone-abbreviated-upload-pack-evaluator",
                "git-fetch-abbreviated-upload-pack-evaluator",
                "git-pull-abbreviated-upload-pack-evaluator",
                "git-push-abbreviated-receive-pack-evaluator",
                "git-grep-abbreviated-pager-evaluator",
                "git-option-terminator-long-option-data",
                "safe-git-fetch-update-head-ok-short-u",
                "safe-git-pull-update-head-ok-short-u",
                "safe-git-push-set-upstream-short-u",
                "safe-git-rebase-strategy-option-uppercase-x",
                "env-path-bare-git-status",
                "prefix-path-bare-git-status",
                "compound-path-assignment-bare-git-status",
                "prefix-git-exec-path-trusted-absolute-git",
                "git-external-command-environment-payload",
                "env-path-known-safe-bare-executable",
                "path-prefix-absolute-git-status-denied",
                "env-path-absolute-git-status-denied",
                "safe-prefix-locale-bare-git-status",
                "safe-env-locale-bare-git-status",
                "scoped-path-absolute-git-compound-denied",
                "compound-locale-assignment-is-conservative",
                "ignore-environment-absolute-git-status-denied",
                "env-option-terminator-path-bare-git",
                "option-terminator-path-absolute-git-status-denied",
                "env-option-terminator-git-environment",
                "ignore-environment-locale-absolute-git-status-denied",
                "command-wrapper-export-compound",
                "locale-prefix-export-compound",
                "builtin-wrapper-unset-compound",
                "command-wrapper-hash-compound",
                "command-wrapper-alias-compound",
                "path-absolute-git-push-child-helper",
                "path-absolute-git-fetch-child-helper",
                "path-absolute-git-pull-child-helper",
                "path-absolute-git-clone-child-helper",
                "ignore-environment-absolute-git-push-child-helper",
                "git-environment-safe-data-command",
                "trap-literal-merge-exit",
                "trap-dynamic-exit",
                "trap-option-literal-merge-exit-compound",
                "function-definition-merge-later",
                "standalone-alias-state",
                "safe-trap-text-data",
                "path-absolute-git-status-help-viewer",
                "path-absolute-git-global-paginate-status",
                "path-absolute-git-global-help",
                "path-absolute-git-configured-fsmonitor-status",
                "path-absolute-git-editor-shape",
                "printf-variable-path-compound",
                "builtin-printf-variable-path-compound",
                "command-printf-variable-path-compound",
                "safe-printf-option-terminator-data",
                "read-stateful-compound",
                "readarray-stateful-compound",
                "mapfile-stateful-compound",
                "declare-stateful-compound",
                "typeset-stateful-compound",
                "local-stateful-compound",
                "let-stateful-compound",
                "set-stateful-compound",
                "shopt-stateful-compound",
                "source-stateful-compound",
                "dot-stateful-compound",
                "eval-stateful-compound",
                "safe-locale-absolute-git-compound",
            }
            <= case_ids
        )
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                classified = classify_pre_use(bash(case["command"]))
                if case["expected"] == "none":
                    self.assertIsNone(classified)
                else:
                    self.assertIsNotNone(classified)
                    self.assertEqual(
                        (classified.kind, classified.reason),
                        ("error", "CLASSIFIER_UNKNOWN"),
                    )

    def test_known_safe_alias_and_extension_list_shapes_are_not_merge(self):
        for command in (
            "gh alias list",
            "gh alias list --shell",
            "gh extension list",
            "gh extension list --help",
        ):
            with self.subTest(command=command):
                self.assertIsNone(classify_pre_use(bash(command)))
        self.assertEqual(classify_pre_use(bash("gh alias exec land")).kind, "error")
        self.assertEqual(classify_pre_use(bash("gh extension exec land")).kind, "error")

    def test_graphql_inline_file_and_indirection_bypass_corpus_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "merge.graphql").write_text(
                "mutation { mergePullRequest(input: {}) { clientMutationId } }",
                encoding="utf-8",
            )
            cases = (
                "gh api graphql -F query=@merge.graphql -F pullRequestId=PR_ID",
                "gh api graphql -F 'query=@merge.graphql' -F mergeMethod=SQUASH",
                'gh api graphql -F query=@mer""ge.graphql',
                "gh api graphql -f 'query=mutation { mergePullRequest(input: {}) { clientMutationId } }'",
                "gh api graphql -F query=@-",
                "gh api graphql -F query=@missing.graphql",
                "gh api graphql -F 'query=$QUERY'",
                "gh api graphql --input payload.json",
            )
            for command in cases:
                with self.subTest(command=command):
                    classified = classify_pre_use(bash(command, root), cwd=root)
                    self.assertEqual(classified.kind, "error")
                    self.assertEqual(classified.reason, "CLASSIFIER_UNKNOWN")

            (root / "auto.graphql").write_text(
                "mutation { enablePullRequestAutoMerge(input: {}) { clientMutationId } }",
                encoding="utf-8",
            )
            auto = classify_pre_use(
                bash("gh api graphql -F query=@auto.graphql", root), cwd=root
            )
            self.assertEqual((auto.kind, auto.reason), ("block", "AUTO_MERGE_DENIED"))

    def test_quoted_shell_punctuation_does_not_create_a_false_bypass(self):
        classified = classify_pre_use(
            bash('gh -R example/repo pr merge 12 --squash --body "text; still one arg"')
        )
        self.assertEqual(classified.kind, "merge")

    def test_rest_merge_endpoint_and_connector_are_bound(self):
        rest = classify_pre_use(
            bash(
                "gh api -X PUT repos/example/repo/pulls/12/merge "
                "-f merge_method=squash -f sha=" + "b" * 40
            )
        )
        self.assertEqual((rest.kind, rest.operation.transport), ("merge", "rest"))
        connector = classify_pre_use(
            {
                "tool_name": "mcp__codex_apps__github_merge_pull_request",
                "tool_input": {
                    "repository_full_name": "example/repo",
                    "pr_number": 12,
                    "merge_method": "merge",
                    "commit_title": "title",
                    "commit_message": "fixes #7",
                    "expected_head_sha": "c" * 40,
                },
            }
        )
        self.assertEqual((connector.kind, connector.operation.transport), ("merge", "connector"))

    def test_connector_auto_merge_and_unknown_merge_tool_are_denied(self):
        auto = classify_pre_use(
            {
                "tool_name": "mcp__codex_apps__github_enable_auto_merge",
                "tool_input": {"repository_full_name": "example/repo", "pr_number": 12},
            }
        )
        unknown = classify_pre_use(
            {"tool_name": "mcp__future__merge_pull_request", "tool_input": {}}
        )
        self.assertEqual((auto.kind, auto.reason), ("block", "AUTO_MERGE_DENIED"))
        self.assertEqual((unknown.kind, unknown.reason), ("error", "CLASSIFIER_UNKNOWN"))

    def test_non_merge_tool_is_outside_this_gate(self):
        self.assertIsNone(classify_pre_use(bash("gh issue view 12")))
        self.assertIsNone(classify_pre_use({"tool_name": "Read", "tool_input": {"path": "x"}}))


class RepositoryBindingTests(unittest.TestCase):
    def test_repository_from_cwd_requires_exact_worktree_and_github_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            def runner(argv, **kwargs):
                if argv == ["git", "rev-parse", "--show-toplevel"]:
                    output = str(root) + "\n"
                else:
                    self.assertEqual(argv, ["git", "remote", "get-url", "origin"])
                    output = "git@github.com:example/repo.git\n"
                return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

            actual = repository_from_cwd(
                {"cwd": str(root)}, cwd=root, runner=runner
            )
            self.assertEqual(actual, "example/repo")


if __name__ == "__main__":
    unittest.main()
