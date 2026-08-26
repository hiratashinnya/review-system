import json
import subprocess
import tempfile
import tomllib
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
        root = Path(__file__).parents[2]
        fixture = json.loads(
            (
                root
                / "tests"
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
            "pr-merge-audit/5",
        )
        self.assertEqual(
            fixture["expected_audit"]["classifier_version"],
            CLASSIFIER_VERSION,
        )
        for probe in fixture["probes"]:
            with self.subTest(probe=probe["id"]):
                if "expected_product_config" in probe:
                    expected = probe["expected_product_config"]
                    config = tomllib.loads((root / expected["path"]).read_text(encoding="utf-8"))
                    tool = config["apps"][expected["app_id"]]["tools"][expected["tool_key"]]
                    self.assertEqual(tool["enabled"], expected["enabled"])
                    self.assertNotIn("payload", probe)
                    self.assertFalse(expected["audit_expected"])
                    continue
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
                "if-control-state-mutation",
                "while-control-state-mutation",
                "for-control-state-mutation",
                "case-control-state-mutation",
                "function-keyword-control-structure",
                "nested-shell-control-state-mutation",
                "safe-control-keyword-arguments",
                "safe-single-quoted-control-keyword-data",
                "safe-git-control-keyword-path-data",
                "safe-linear-echo-printf",
                "safe-redirect-stderr-to-stdout",
                "safe-redirect-stderr-to-devnull",
                "safe-redirect-stdout-to-file",
                "safe-append-redirect-to-file",
                "safe-numbered-fd-redirects",
                "safe-both-streams-redirect",
                "safe-noclobber-override-redirect",
                "safe-input-redirect",
                "safe-redirect-then-pipe",
                "safe-quoted-redirect-character-data",
                "heredoc-shell-merge",
                "herestring-shell-merge",
                "output-process-substitution-merge",
                "redirect-target-command-substitution",
                "redirect-target-backtick-substitution",
                "redirect-missing-target",
                "redirected-compound-merge-leaf",
                "redirected-brace-group-merge",
                "redirected-subshell-merge",
                "redirected-shell-command-string-merge",
                "redirected-git-bisect-run-merge",
                "redirect-adjacent-control-keyword-still-detected",
                "redirect-only-leaf-empty-after-strip",
                "exec-only-redirect-leaf-empty-after-strip",
                "redirect-only-leaf-in-compound-still-detected",
                "exec-only-redirect-leaf-in-compound-still-detected",
                "safe-head-cd-literal-absolute",
                "safe-head-cd-literal-relative",
                "safe-head-cd-literal-parent",
                "safe-head-cd-literal-quoted-space",
                "safe-head-cd-literal-standalone",
                "safe-head-cd-literal-semicolon-nonmerge",
                "head-cd-expansion-operand",
                "head-cd-braced-expansion-operand",
                "head-cd-command-substitution-operand",
                "head-cd-tilde-operand",
                "head-cd-glob-operand",
                "head-cd-option-operand",
                "head-cd-previous-directory-operand",
                "head-cd-two-operand-substitution",
                "head-cd-without-operand",
                "head-cd-with-path-assignment-prefix",
                "head-cd-with-command-wrapper",
                "non-head-cd-literal-leaf",
                "head-cd-literal-then-cli-merge",
                "head-cd-literal-then-bare-merge",
                "head-cd-literal-then-rest-merge",
                "head-cd-literal-then-nested-shell-merge",
                "head-cd-literal-then-auto-merge",
                "head-cd-literal-then-state-mutation-then-merge",
                "safe-quoted-heredoc-marker-single",
                "safe-quoted-heredoc-marker-double",
                "safe-quoted-heredoc-marker-inside-word",
                "safe-quoted-heredoc-marker-with-apostrophe",
                "safe-quoted-herestring-marker-data",
                "unquoted-heredoc-still-closed",
                "unquoted-herestring-still-closed",
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
        for tool_name in (
            "mcp__codex_apps__github_merge_pull_request",
            "codex_apps.github.merge_pull_request",
        ):
            with self.subTest(tool_name=tool_name):
                connector = classify_pre_use(
                    {
                        "tool_name": tool_name,
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

    def test_github_mcp_owner_repo_connector_shape_is_bound(self):
        """GitHub MCP server が実際に提供する `{owner, repo, pullNumber, ...}` 形式
        （形式B）を束縛する。旧実装は `repository_full_name`/`pr_number` 形式（形式A）
        しか受理せず、この形式のmerge要求を必ず `CLASSIFIER_UNKNOWN` で拒否していた
        （Issue #447）。"""
        for tool_name in (
            "mcp__github__merge_pull_request",
            "github_merge_pull_request",
        ):
            with self.subTest(tool_name=tool_name):
                connector = classify_pre_use(
                    {
                        "tool_name": tool_name,
                        "tool_input": {
                            "owner": "example",
                            "repo": "repo",
                            "pullNumber": 12,
                            "merge_method": "squash",
                            "commit_title": "title",
                            "commit_message": "fixes #7",
                        },
                    }
                )
                self.assertEqual(
                    (connector.kind, connector.operation.transport), ("merge", "connector")
                )
                self.assertEqual(connector.operation.repository, "example/repo")
                self.assertEqual(connector.operation.pr_number, 12)
                self.assertEqual(connector.operation.merge_method, "squash")

    def test_owner_repo_connector_shape_accepts_optional_expected_head(self):
        connector = classify_pre_use(
            {
                "tool_name": "mcp__github__merge_pull_request",
                "tool_input": {
                    "owner": "example",
                    "repo": "repo",
                    "pullNumber": 12,
                    "merge_method": "merge",
                    "expected_head_sha": "c" * 40,
                },
            }
        )
        self.assertEqual((connector.kind, connector.operation.transport), ("merge", "connector"))
        self.assertEqual(connector.operation.expected_head_oid, "c" * 40)

    def test_both_connector_shapes_share_one_identity_validation_path(self):
        """新しい形式Bの分岐だけ検証が緩くならないことを固定する。repository名の
        正規表現・PR番号の正整数判定・merge methodの3値・override型・expected headの
        OID形式は両形式で同じコードパスを通る（Issue #447）。"""
        base = {
            "owner": "example",
            "repo": "repo",
            "pullNumber": 12,
            "merge_method": "merge",
        }
        cases = (
            ({**base, "owner": "exa/mple"}, "TARGET_AMBIGUOUS"),
            ({**base, "owner": ""}, "TARGET_AMBIGUOUS"),
            ({**base, "repo": "repo.git"}, "TARGET_AMBIGUOUS"),
            ({**base, "repo": "re po"}, "TARGET_AMBIGUOUS"),
            ({**base, "owner": 12}, "TARGET_AMBIGUOUS"),
            ({**base, "pullNumber": 0}, "TARGET_AMBIGUOUS"),
            ({**base, "pullNumber": -1}, "TARGET_AMBIGUOUS"),
            ({**base, "pullNumber": "12"}, "TARGET_AMBIGUOUS"),
            ({**base, "pullNumber": True}, "TARGET_AMBIGUOUS"),
            ({"owner": "example", "repo": "repo", "merge_method": "merge"}, "TARGET_AMBIGUOUS"),
            ({**base, "merge_method": "fast-forward"}, "MERGE_METHOD_UNKNOWN"),
            ({"owner": "example", "repo": "repo", "pullNumber": 12}, "MERGE_METHOD_UNKNOWN"),
            ({**base, "commit_title": 7}, "MERGE_OVERRIDE_AMBIGUOUS"),
            ({**base, "commit_message": []}, "MERGE_OVERRIDE_AMBIGUOUS"),
            ({**base, "expected_head_sha": "z" * 40}, "IDENTITY_MISMATCH"),
            ({**base, "expected_head_sha": 12}, "IDENTITY_MISMATCH"),
        )
        for tool_input, reason in cases:
            with self.subTest(tool_input=tool_input):
                classified = classify_pre_use(
                    {"tool_name": "mcp__github__merge_pull_request", "tool_input": tool_input}
                )
                self.assertEqual((classified.kind, classified.reason), ("error", reason))

    def test_mixed_and_unknown_connector_keys_fail_close(self):
        """形式Aと形式Bのidentity keyが混在した呼び出し（chimera）は優先順位を付けず
        fail-closeする。どちらかを採ると、ゲートが束縛したPRと下流connectorが実行する
        PRが別物になり得る（Issue #447）。未知キーの混入も同じく拒否する。"""
        for tool_input in (
            {"owner": "example", "repo": "repo", "pr_number": 12, "merge_method": "merge"},
            {
                "repository_full_name": "example/repo",
                "pr_number": 12,
                "pullNumber": 99,
                "merge_method": "merge",
            },
            {
                "repository_full_name": "example/repo",
                "owner": "other",
                "repo": "repo",
                "pullNumber": 12,
                "merge_method": "merge",
            },
            {"repository_full_name": "example/repo", "owner": "other", "merge_method": "merge"},
            {
                "owner": "example",
                "repo": "repo",
                "pullNumber": 12,
                "merge_method": "merge",
                "auto_merge": True,
            },
            {
                "repository_full_name": "example/repo",
                "pr_number": 12,
                "merge_method": "merge",
                "pullNumberr": 12,
            },
        ):
            with self.subTest(tool_input=tool_input):
                classified = classify_pre_use(
                    {"tool_name": "mcp__github__merge_pull_request", "tool_input": tool_input}
                )
                self.assertEqual(
                    (classified.kind, classified.reason), ("error", "CLASSIFIER_UNKNOWN")
                )

    def test_owner_repo_shape_auto_merge_is_still_denied(self):
        auto = classify_pre_use(
            {
                "tool_name": "mcp__github__enable_pull_request_auto_merge",
                "tool_input": {"owner": "example", "repo": "repo", "pullNumber": 12},
            }
        )
        self.assertEqual((auto.kind, auto.reason), ("block", "AUTO_MERGE_DENIED"))

    def test_connector_auto_merge_and_unknown_merge_tool_are_denied(self):
        auto = classify_pre_use(
            {
                "tool_name": "codex_apps.github.enable_auto_merge",
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

    def test_gh_project_subcommands_are_outside_this_gate(self):
        """`gh project` は merge と無関係だが、旧 allowlist に無く CLASSIFIER_UNKNOWN
        で誤ブロックされていた（Issue #412）。GitHub Projects v2 の読み書きに使う
        代表的な subcommand が素通りすることを固定する。"""
        self.assertIsNone(
            classify_pre_use(bash("gh project list --owner example --format json"))
        )
        self.assertIsNone(classify_pre_use(bash("gh project view 1 --owner example")))
        self.assertIsNone(
            classify_pre_use(bash("gh project item-add 1 --owner example --url x"))
        )

    def test_simple_redirections_do_not_block_unrelated_read_only_commands(self):
        """単純な file/fd redirection（`2>&1`・`2>/dev/null`・`> file` 等）は実行語を
        差し替えられない data sink なので、merge と無関係な read-only command が
        CLASSIFIER_UNKNOWN で誤ブロックされない（Issue #428）。Issue 本文に実測記録の
        ある3コマンドを含む。"""
        for command in (
            'grep -n "pr-merge-gate" .claude/settings.json 2>/dev/null',
            "gh issue view 412 --json body,title -q .body 2>&1",
            "gh project list --owner example --format json 2>&1",
            "gh issue view 412 2>&1 | head -c 6000",
            "gh issue list > issues.txt",
            "gh issue list >> issues.txt",
            "gh issue list >| issues.txt",
            "gh issue list &> out.txt",
            "gh issue list &>> out.txt",
            "gh issue list 1>out.txt 2>err.txt",
            "gh issue list 2> /dev/null",
            "git status --short 2>&1",
            "git apply < patch.diff",
            "echo done >&2",
            "echo done >& log.txt",
            "printf '%s\\n' body > body.txt",
            "python3 -m unittest discover -s tests/unit 2>&1",
        ):
            with self.subTest(command=command):
                self.assertIsNone(classify_pre_use(bash(command)))

    def test_redirection_relaxation_keeps_merge_bearing_structures_closed(self):
        """redirection 緩和後も、merge を隠し得る構造（heredoc/herestring・process
        substitution・subshell/brace group・command substitution・target 欠落）は
        CLASSIFIER_UNKNOWN のまま。redirection を付けた素の merge は素通りではなく
        merge/block として束縛され続ける（Issue #428 の受入条件）。"""
        closed = (
            "bash <<EOF\ngh pr merge 1 --squash\nEOF",
            "bash <<< 'gh pr merge 1 --squash'",
            "echo <(gh pr merge 1 --squash)",
            "echo data >(gh pr merge 1 --squash)",
            'echo "$(gh pr merge 1 --squash)" > /dev/null',
            "echo `gh pr merge 1 --squash` > /dev/null",
            "gh issue view 1 > $(gh pr merge 1 --squash)",
            "gh issue view 1 > `gh pr merge 1 --squash`",
            "gh issue view 1 >",
            "gh issue view 1 2>",
            "bash -c 'gh pr merge 1 --squash' > /dev/null",
            "{ gh pr merge 1 --squash; } > /dev/null",
            "(gh pr merge 1 --squash) > /dev/null",
            "gh issue view 1 > /dev/null; gh pr merge 1 --squash 2>&1",
            "gh issue view 1 2>&1 | gh pr merge 1 --squash",
            "git bisect run gh pr merge 1 --squash 2>/dev/null",
            "git -c alias.p='!gh pr merge 1 --squash' p 2>&1",
            "$GH pr merge 12 --squash > /dev/null",
        )
        for command in closed:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertIsNotNone(classified)
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )

        for command in (
            "gh -R example/repo pr merge 12 --squash > /dev/null",
            "gh -R example/repo pr merge 12 --squash 2>&1",
            "gh -R example/repo pr merge 12 --squash 2>/dev/null",
            "gh -R example/repo pr merge 12 --squash &> merge.log",
            "gh api -X PUT repos/example/repo/pulls/12/merge -f merge_method=squash > out.json",
        ):
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(classified.kind, "merge")
                self.assertEqual(classified.operation.repository, "example/repo")
                self.assertEqual(classified.operation.pr_number, 12)

        auto = classify_pre_use(
            bash("gh -R example/repo pr merge 12 --squash --auto 2>/dev/null")
        )
        self.assertEqual((auto.kind, auto.reason), ("block", "AUTO_MERGE_DENIED"))

    def test_redirect_only_leaves_pass_through_but_stay_closed_inside_a_compound(self):
        """PR #429（Issue #428）で `_split_shell_commands()` にredirection除去を
        入れた副作用として、除去後に実行語が空になるleaf（`> file` 単体・`exec > file`）が
        素通り（`None`）になった。安全性は検証済みだが固定回帰テストが無かった
        （F-428-2・Issue #430）。単体のredirect-only/exec-only leafは意図どおり素通りし、
        同じ空leafがcompound構造の一部としてmerge操作と同居する場合は引き続き
        fail-close（CLASSIFIER_UNKNOWN）だが、その発火機構は2ケースで異なる（F-430-01）：
        `> file; gh pr merge 1 --squash` は redirection strip 後に先頭leafが空文字になり
        `_split_shell_commands` 自身がNoneを返す一方、`exec > file; gh pr merge 1 --squash`
        は先頭leafが非空（`"exec"`）で残るため `_split_shell_commands` は
        `["exec", "gh pr merge 1 --squash"]` を返し、`classify_pre_use` のcompound leaf
        分類ループがmerge leafを検出してCLASSIFIER_UNKNOWNにする。"""
        for command in ("> file", "exec > file", ">> file", "exec >> file"):
            with self.subTest(command=command):
                self.assertIsNone(classify_pre_use(bash(command)))

        for command in (
            "> file; gh pr merge 1 --squash",
            "exec > file; gh pr merge 1 --squash",
        ):
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertIsNotNone(classified)
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )


    def test_head_cd_to_a_literal_path_no_longer_blocks_unrelated_commands(self):
        """先頭leafの `cd <literal-path>` は誤ブロックしない（Issue #435 項目4(1)）。

        `cd` は `_SHELL_STATE_COMMANDS` の一員として一律 CLASSIFIER_UNKNOWN に落ちて
        いたが、classifier 1.14 の実測で最頻の誤ブロック形が `cd /abs/path && <非merge>`
        だった。cwdは後続leafの**実行実体**を選ばないので、operandにexpansion・glob・
        tilde・option・prefix assignment・wrapperが無い形だけを開ける。
        """
        for command in (
            "cd /home/example/repo && git status --short",
            "cd /home/example/repo; git status",
            "cd tests/unit && gh issue view 1",
            "cd .. && git status",
            "cd '/tmp/with space' && git status",
            "cd /home/example/repo",
            "cd /home/example/repo && python3 -m unittest discover -s tests/unit 2>&1",
        ):
            with self.subTest(command=command):
                self.assertIsNone(classify_pre_use(bash(command)))

    def test_head_cd_relaxation_cannot_hide_a_merge_or_a_dynamic_operand(self):
        """`cd` 緩和でmergeを隠せない・operandを動的にできない（Issue #435 項目4(1)）。

        under-block（mergeの見逃し）が出ないことを固定する。compound内のmerge leafは
        従来どおり CLASSIFIER_UNKNOWN であり、`cd` の位置・operandの形・prefix・wrapper
        のいずれかが証明可能な範囲を外れたら閉じたままになる。
        """
        for command in (
            "cd /home/example/repo && gh -R example/repo pr merge 1 --squash",
            "cd /home/example/repo && gh pr merge 1 --squash",
            "cd /home/example/repo && gh -R example/repo pr merge 1 --squash --auto",
            "cd /home/example/repo && bash -c 'gh pr merge 1 --squash'",
            "cd /home/example/repo && git bisect run gh pr merge 1 --squash",
            "cd /home/example/repo && gh api -X PUT repos/example/repo/pulls/1/merge "
            "-f merge_method=squash",
            "cd /home/example/repo; gh pr merge 1 --squash",
            "cd /home/example/repo && export PATH=/tmp && git status",
            "gh issue view 1 && cd /tmp",
            "echo start && cd /tmp && git status",
            "cd $HOME && git status",
            'cd "${REPO}" && git status',
            'cd "$(pwd)" && git status',
            "cd ~/ws && git status",
            "cd /tmp/*/repo && git status",
            "cd -P /tmp && git status",
            "cd - && git status",
            "cd /tmp /var && git status",
            "cd && git status",
            "PATH=/tmp cd /tmp && git status",
            "command cd /tmp && git status",
            "exec cd /tmp && git status",
        ):
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertIsNotNone(classified)
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )

    def test_quoted_heredoc_markers_are_data_but_real_heredocs_stay_closed(self):
        """quote内の `<<` を heredoc と誤認しない（Issue #435 項目4(2)）。

        quote内の `<<` / `<<<` はdata（コマンド引数の文字）であって redirection operator
        ではないため、実行語を持ち込めない。逆にquoteの外の `<<` / `<<<` は本物の
        heredoc/herestringで、受け手がstdinを評価する実行体（`bash` 等）ならmergeを
        隠せるため CLASSIFIER_UNKNOWN のまま閉じる（緩和しない）。
        """
        for command in (
            "echo 'diff <<a>> b'",
            'git commit -m "fix: parse a<<b"',
            "echo a'<<'b",
            'echo a"<<"b',
            "gh issue comment 1 --body \"it's a << b\"",
            "grep -n '<<<' notes.md",
            "gh issue list --search 'a<<b'",
            'echo "$BRANCH << done"',
            "printf '%s' '<<EOF'",
        ):
            with self.subTest(command=command):
                self.assertIsNone(classify_pre_use(bash(command)))

        for command in (
            "cat << EOF",
            "bash <<EOF\ngh pr merge 1 --squash\nEOF",
            "bash <<< 'gh pr merge 1 --squash'",
            "python3 -m json.tool <<< '{}'",
            "echo a << b",
        ):
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertIsNotNone(classified)
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )


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
