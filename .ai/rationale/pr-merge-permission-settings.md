# PR merge 権限を AI から外した経緯

## Issue #542 の決定

Issue #542 は、AI が merge 直前に操作する classifier/hook を撤去し、AI ロールと主文脈の merge 権限を platform-native permission で拒否して、実際の merge をオーナーの手動操作にする決定を実装した。オーナーは blocker report を確認してから GitHub UI 等で判断する。report は時点情報であり、merge permit を発行せず merge API を呼ばない。

以前の仕組みは `pr_merge_gate.classifier` と PreToolUse/PostToolUse hook がコマンドを分類し、blocker evidence を再検証していた。classifier の誤分類と hook 経路の保守負担を解消するため、コマンド分類を permission boundary に移し、blocker の fresh re-evaluation は owner-facing report として残した。以前の運用手順と classifier contract は [`docs/archive/pr-merge-hook-runbook-2026-10-02.md`](../../docs/archive/pr-merge-hook-runbook-2026-10-02.md) と [`docs/archive/pr-merge-gate-classifier-policy-v1.17.md`](../../docs/archive/pr-merge-gate-classifier-policy-v1.17.md) に保存した。

## 2026-10-02 の是正判断 — 読み取りを巻き込む広域 deny を撤回

初回実装では Codex execpolicy の表現力不足を補うため、`git -C`、`gh -R`、`gh --repo` で始まる呼び出しと `gh api` をまとめて拒否した。Claude 側にも `git -C` と `gh api` の広い deny が入った。その結果、`git -C <repo> status`、`gh --repo <repo> pr view`、通常の `gh api` 読み取りまで拒否された。これは「AI のうっかり merge を防ぐ」という目的に不要な読み取り制限なので、オーナー判断で撤回した。

代わりに、Claude の native deny は `git * merge` / `gh * pr merge` のようにサブコマンド前の global options を挟む狭い glob に限定する。Codex の prefix ルールは直接形だけに保ち、両方の既存 `agent-command-gate` hook で env / 絶対パス / RTK wrapper と既知の global options を字句的に読み飛ばして判定する。API は REST merge route と HTTP method、GraphQL merge mutation を読む。通常の GET と無関係な GraphQL query を許可し、解析が曖昧な場合は理由を付けて拒否する。

Claude の native glob は完全な parser ではないため、引数に merge という独立語を含む一部の非 merge 呼び出しを拾う可能性が残る。対象を `git` / `gh pr` の形に絞り、より広い `git -C` / `gh api` 拒否より偽陽性を小さくする判断とした。

## 現行の権限境界

- Claude は `.claude/settings.json` の `permissions.deny` で直接・global-option shell merge forms と GitHub merge tools を拒否する。
- Codex は `.codex/rules/default.rules` の execpolicy で直接形を拒否する。GitHub connector merge tools は `.codex/config.toml` で無効にする。
- 両方の既存 `agent-command-gate` hook が全ロールの shell command text を字句検査し、Git/gh global options、env、絶対パス、RTK wrapper、REST merge route、GraphQL merge mutations を補う。読み取り GET と無関係な query は許可する。
- Codex prefix のみでは後続引数を判定できないため、`git -C` 等を native rule で拒否しない。詳しい保証範囲・失敗時の挙動・残る制約は [`docs/tools/pr-merge-gate.md`](../../docs/tools/pr-merge-gate.md) に記録する。これらは OS-level sandbox ではなく、意図的な alternate invocation を防止する保証はしない。

## 版の扱い

旧 classifier の最終 contract は `classifier_version: 1.17` である。Issue #542 で classifier 自体を撤去したため、その版は archive で履歴として固定し、現行の retired notice は `policy_version: 1.18` とした。`1.18` は notice の版であり、稼働 classifier の版ではない。

本是正は同じ未 merge Issue #542 内の設計・実装補正であり、`policy_version: 1.18` は本来 classifier の retired notice の版である。新たな classifier 契約を作らず、その notice をもう一度 bump する変更でもないため、版を据え置いた。
