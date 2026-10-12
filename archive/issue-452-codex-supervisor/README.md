# Issue #452 Codex supervisor のテスト設計・テスト結果（退役・履歴保全）

Issue #452 が導入した Codex repo supervisor 方式は Issue #538 の PR-A で退役した。
本ディレクトリは、その検証証跡のうちテスト設計（TD）とテスト結果（TR）を `git mv` で移したものである
（`.claude/rules/01-principles.md`「PR8「消さない」の適用範囲」区分1。前例は `archive/issue-start-manifest-v1/`）。

| 置き場 | 移設元 | 中身 |
|---|---|---|
| `designs/` | `tests/designs/TD-issue-start-452*.md` | テスト設計（TD） |
| `reports/` | `tests/reports/TD-issue-start-452-*.md` | テスト結果（TR） |

- 各ファイルの本文は移設時に書き換えていない。本文中の `tests/designs/…`・`tests/reports/…` は移設前のパスを指す。
- テストログは移していない。各 TR の `log_ref`（リポジトリルート相対の `tests/logs/TD-issue-start-452-*.txt`）は
  移設後もそのまま解決できる。
- ここにある TR は旧方式の検証記録である。supervisor は P4（実起動検証）未達のまま退役しており、
  退役によって PASS・resolved へ読み替えない。
- 退役した実行契約は `.ai/rationale/codex-supervisor-retirement-538.md`、現在の状態は
  `docs/methods/codex-workspace-binding.md` を参照する。
