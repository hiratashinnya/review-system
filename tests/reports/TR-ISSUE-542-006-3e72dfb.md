---
id: TR-ISSUE-542-006-3e72dfb
type: TR
version: 1
condition: boundary
result: FAIL
log_ref: tests/logs/TR-ISSUE-542-006-3e72dfb.txt
---

# 目的

F-542-42 の固定 hook 件数期待を修正し、外側 checkout の設定に依存しない独立 clone で CI 相当の再検証を行う。

# 環境

- 修正前の開始点は `3e72dfb05da88885c63330427b20f88ad5161501`。`git clone --no-hardlinks . tmp/_rr/ci-like` で独立 clone を作成した。
- clone の `HOME` は空ディレクトリ、`TMPDIR` と `PYTHONPYCACHEPREFIX` は clone 配下の `tmp/_rr/` に設定した。
- 修正後は worktree で変更した5ファイルを clone に適用し、各ファイルを `cmp` して全て同一であることを確認した。clone 内の追加 commit は行わず、同内容を適用して検証した。

# 確認結果

| 状態 | 実行 | 件数 | failures | errors | skipped |
|---|---|---:|---:|---:|---:|
| 修正前・元 worktree | F-542-42 の5テストを選択実行 | 5 | 0 | 0 | 0 |
| 修正前・独立 clone | `test_codex_hook_trust` と `test_codex_hook_trust_hook` | 19 | 6 | 0 | 0 |
| 修正前・独立 clone | `python3 -m unittest discover -s tests/unit` | 2,059 | 9 | 2 | 12 |
| 修正後・独立 clone | F-542-42 の5テストを選択実行 | 5 | 0 | 0 | 0 |
| 修正後・独立 clone | trust、hook、repository の3 test module | 24 | 0 | 0 | 0 |
| 修正後・独立 clone | `python3 -m unittest discover -s tests/unit` | 2,059 | 2 | 2 | 12 |
| PR #584 の CI run 37726550642 | `unittest` job（提供ログ） | 2,059 | 5 | 0 | 19 |

修正前 clone の failures 9件は、F-542-42 の5件、`test_missing_hooks_json_is_undetermined_not_anomaly`、`test_git_managed_external_directory_falls_back_to_given_path`、issue-start の2件だった。修正後 clone では F-542-42 の5件と Codex hook trust の一時 repo 2件が通り、issue-start の2件が残った。2 errors は修正前後とも同一の Codex profile と Claude MCP のテストである。

F-542-42 の失敗名は次のとおり。修正前 clone では全て失敗し、修正後 clone では全て成功した。

- `test_fewer_discovered_hooks_than_defined_exits_one`
- `test_user_hook_does_not_hide_missing_project_hook`
- `test_user_hooks_do_not_hide_missing_project_hooks`
- `test_zero_discovered_hooks_reports_project_trust_problem`
- `test_missing_project_trust_emits_warning`

# 原因と修正

`.codex/hooks.json` の handler はこの branch では4件、外側の main checkout では6件だった。実装は `resolve_main_checkout()` が選んだ checkout の `hooks.json` から定義件数を数える。修正前のテスト helper は worktree の `ROOT` を渡していたため、linked worktree では外側 main checkout の設定と fake Codex を使い、6件の期待が偶然成立した。通常の CI clone ではその branch checkout が main となり、実際の4件が読み込まれて5つの固定 assertion が失敗した。空の `HOME` を使った独立 clone でも同じ5件が失敗したため、差の原因は `~/.codex/config.toml` ではなく Git の main checkout 解決と `hooks.json` である。

テストは branch の `hooks.json` を一時の独立 Git repository に複製し、検査対象と期待件数を同じ fixture に固定した。期待値は test support が JSON の handler 配列を独立に数え、実装の count 関数を期待値に再利用しない。fixture mode 名の `project-five-user-one` と `project-six-user-untrusted` も、件数を前提にしない名前へ変更した。TMPDIR が checkout 内にある検証では一時 repo が親 checkout を誤認しないよう、test subprocess に TMPDIR の `GIT_CEILING_DIRECTORIES` を設定した。

# 固定件数の全数確認

- 現行 assertion に残っていた `定義 6 件` と `発見 5 件` のリテラル、ならびに `project-five-user-one` / `project-six-user-untrusted` の旧 fixture 名は解消した。
- `user-only-six` は fake user hooks を6件生成するシナリオであり、project hook 数への期待ではないため維持した。
- `test_codex_hook_trust_repository.py` と hook path/fallback test の2・3・4・5件は、それぞれ `write_hooks()` が作る独立 synthetic fixture と対応する期待値で、branch の `.codex/hooks.json` の実数ではないため維持した。
- 既存 TR/log の過去時点における6件記録と、archive 内の撤去済み hook 手順は履歴記録として変更していない。

# 以前「基点由来」と記録された8ケース

同じ独立 clone・空 HOME・checkout 内 TMPDIR で選択実行した結果を示す。

| テスト | 修正前 | 修正後 | 観測 |
|---|---|---|---|
| `test_missing_hooks_json_is_undetermined_not_anomaly` | FAIL | PASS | TMPDIR 配下の temp dir が親 checkout を認識。ceiling 設定後は入力 repo に fallback。 |
| `test_git_managed_external_directory_falls_back_to_given_path` | FAIL | PASS | 同じ親 checkout 誤認。ceiling 設定後は given path に fallback。 |
| `test_nonprivate_manifest_and_ledger_leaf_modes_fail_closed`（`ledger-foreign-group`） | FAIL | FAIL | `MANIFEST_INVALID: unsafe group-writable directory` が先に発生。 |
| `test_nonprivate_manifest_and_ledger_leaf_reject_nss_lookup_failure`（`leaf=ledger`） | FAIL | FAIL | 同じ group-writable directory の検査で先に失敗。 |
| `test_watcher_parses_reached` | PASS | PASS | 選択実行で通過。 |
| `test_watcher_parses_reached_past_epoch` | PASS | PASS | 選択実行で通過。 |
| `test_installed_codex_profile_normal_and_negative_matrix_is_model_free` | ERROR | ERROR | installed CLI が `daemon_auto_start system_proxy_fallback unified_exec_tty` を未知 feature と報告。 |
| `test_claude_review_blocks_workspace_outside_default_before_commands` | ERROR | ERROR | mock の `current_block()` が空 tuple を返し、2値 unpack で `ValueError`。 |

この検証条件では8ケース中、修正前に4 failures・2 errors が再現し、2件は通過した。修正後は hook trust の一時 repo 2件も通り、issue-start の2 failures・profile/MCP の2 errors が残った。提供された PR CI ログにはこれら8ケースの失敗はなく、記録された failures は F-542-42 の5件である。

F-542-12 は `/tmp` worktree の sandbox 前提を扱う既存 finding で、今回の checkout 内 TMPDIR による親 Git repo 誤認とは別の事象である。`tmp/_handoff/karte-542-r32.md` は変更していない。

# 追加検証

- `python3 -m maintainability_lint check`: exit 0、violations 0、accepted-debt 125。
- `git diff --check`: pass。
- test code 変更に伴い `uv run --with coverage` を試したが、`pypi.org` の DNS 解決が3回 retry 後に失敗し、coverage を取得できなかった。coverage の代替 install は行っていない。

# オーナー判断が要る点

独立 clone の full unit suite には issue-start の2 failures と Codex profile / Claude MCP の2 errors が残る。選択肢は、(1) #542 の範囲へ追加して今回まとめて扱う、(2) 今回の F-542-42 は分離したまま、これら4ケースを別の是正範囲として扱う、の2つ。F-542-42 の限定された原因と独立した環境条件であることから、推奨は (2)。この判断はここでは確定していない。
