# PR merge 権限を AI から外した経緯

## Issue #542 の決定

Issue #542 は、AI が merge 直前に操作する classifier/hook を撤去し、AI ロールと主文脈の merge 権限を platform-native permission で拒否して、実際の merge をオーナーの手動操作にする決定を実装した。オーナーは blocker report を確認してから GitHub UI 等で判断する。report は時点情報であり、merge permit を発行せず merge API を呼ばない。

以前の仕組みは `pr_merge_gate.classifier` と PreToolUse/PostToolUse hook がコマンドを分類し、blocker evidence を再検証していた。classifier の誤分類と hook 経路の保守負担を解消するため、コマンド分類を permission boundary に移し、blocker の fresh re-evaluation は owner-facing report として残した。以前の運用手順と classifier contract は [`docs/archive/pr-merge-hook-runbook-2026-10-02.md`](../../docs/archive/pr-merge-hook-runbook-2026-10-02.md) と [`docs/archive/pr-merge-gate-classifier-policy-v1.17.md`](../../docs/archive/pr-merge-gate-classifier-policy-v1.17.md) に保存した。

## 現行の権限境界

- Claude は `.claude/settings.json` の `permissions.deny` で shell merge spellings と GitHub merge tools を拒否する。
- Codex は `.codex/rules/default.rules` の execpolicy で直接・RTK 経由の shell merge forms を拒否し、GitHub connector の merge tools は `.codex/config.toml` で無効化する。
- Codex prefix matching では `git -C`, `gh -R`, `gh --repo` を subcommand だけに限定して拒否できない。そのため、これらの leading prefixes で始まる non-merge commands も拒否する。前置 global options の並べ替え、attached options、alternate executable path は保証範囲外であり、運用上の具体的な限界は [`docs/tools/pr-merge-gate.md`](../../docs/tools/pr-merge-gate.md) に記録する。
- `agent-command-gate` はロール別の push 等の制限を続けるが、merge permission の正本ではない。command text/prefix policies は OS-level sandbox ではなく、意図的な alternate invocation を防止する保証はしない。

## 版の扱い

旧 classifier の最終 contract は `classifier_version: 1.17` である。Issue #542 で classifier 自体を撤去したため、その版は archive で履歴として固定し、現行の retired notice は `policy_version: 1.18` とした。`1.18` は notice の版であり、稼働 classifier の版ではない。
