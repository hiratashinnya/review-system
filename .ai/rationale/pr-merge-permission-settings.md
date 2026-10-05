# PR merge 権限を AI から外した経緯

## Issue #542 の決定

Issue #542 は、merge 専用 classifier と PreToolUse/PostToolUse hook を撤去し、AI ロールと主文脈の merge を native permission の直接形 prefix 拒否と、両 platform の共有 command hook による global option／wrapper／API／検査可能な間接実行形式の判定で抑止して、実際の merge をオーナーの手動操作にする決定を実装した。オーナーは blocker report を確認してから GitHub UI 等で判断する。report は時点情報であり、merge permit を発行せず merge API を呼ばない。

以前の仕組みは `pr_merge_gate.classifier` と PreToolUse/PostToolUse hook がコマンドを分類し、blocker evidence を再検証していた。classifier の誤分類と hook 経路の保守負担を解消するため、コマンド分類を permission boundary に移し、blocker の fresh re-evaluation は owner-facing report として残した。以前の運用手順と classifier contract は [`docs/archive/pr-merge-hook-runbook-2026-10-02.md`](../../docs/archive/pr-merge-hook-runbook-2026-10-02.md) と [`docs/archive/pr-merge-gate-classifier-policy-v1.17.md`](../../docs/archive/pr-merge-gate-classifier-policy-v1.17.md) に保存した。

## 2026-10-02 の是正判断 — 読み取りを巻き込む広域 deny を撤回

初回実装では Codex execpolicy の表現力不足を補うため、`git -C`、`gh -R`、`gh --repo` で始まる呼び出しと `gh api` をまとめて拒否した。Claude 側にも `git -C` と `gh api` の広い deny が入った。その結果、`git -C <repo> status`、`gh --repo <repo> pr view`、通常の `gh api` 読み取りまで拒否された。これは「AI のうっかり merge を防ぐ」という目的に不要な読み取り制限なので、オーナー判断で撤回した。

代わりに、Claude の native deny は `git * merge` / `gh * pr merge` のようにサブコマンド前の global options を挟む狭い glob に限定する。Codex の prefix ルールは直接形だけに保ち、両方の既存 `agent-command-gate` hook で env / 絶対パス / RTK wrapper と既知の global options を字句的に読み飛ばして判定する。API は REST merge route と HTTP method、GraphQL merge mutation を読む。通常の GET と無関係な GraphQL query を許可し、解析が曖昧な場合は理由を付けて拒否する。

Claude の native glob は完全な parser ではないため、引数に merge という独立語を含む一部の非 merge 呼び出しを拾う可能性が残る。対象を `git` / `gh pr` の形に絞り、より広い `git -C` / `gh api` 拒否より偽陽性を小さくする判断とした。

## 現行の権限境界

- Claude の `.claude/settings.json` と Codex の `.codex/rules/default.rules` は、直接形の merge command prefix を拒否する。Claude settings と Codex connector configuration は、それぞれの GitHub merge tools も無効にする。
- 両方の既存 `agent-command-gate` hook が全ロールの shell command text を字句検査し、Git/gh global options、env、絶対パス、RTK wrapper、REST merge route、GraphQL merge mutations、検査可能な間接実行形式を判定する。読み取り GET と無関係な query は許可する。
- Native command rules は直接形の prefix を対象とし、global options や各種 wrapper、API request の判定は両 hook が担う。詳しい保証範囲・失敗時の挙動・残る制約は [`docs/tools/pr-merge-gate.md`](../../docs/tools/pr-merge-gate.md) に記録する。これらは OS-level sandbox ではなく、意図的な alternate invocation を防止する保証はしない。

## 受容した静的検査の境界

2026-10-03 の F-542-22 判断では、目的を AI のうっかり merge 防止に置き、意図的な迂回を保証対象外として受容した。Git alias、shell function、別 executable、script 内の実行は、実行環境や対象コードを解釈しなければ展開できず、command-text 検査だけでは静的に確定できない。これらを網羅的に解決する実行時機構は追加せず、最終の強制手段を GitHub 側の branch protection とする。

2026-10-04 の F-542-24 判断では、エスケープされた入れ子の旧形式 backtick substitution も意図的な迂回形として保証対象外にした。Issue の目的は AI のうっかり merge を機械的に防ぐことであり、意図的な迂回策を網羅して潰すことではないため、この finding に対するコード変更は行わない。迂回を含めて拒否する最終手段は GitHub 側の branch protection とする。

2026-10-04 の F-542-29 判断では、GraphQL inline fragment 内に merge mutation field を置く形も意図的な迂回に近いものとして保証対象外にした。コード変更は行わない。Issue の目的は AI のうっかり merge を機械的に防ぐことであり、意図的な迂回策を網羅して潰すことではない。最終的な強制手段は GitHub 側の branch protection とする。

F-542-03 では AC 2／AC 10 の根拠として、実際のローカル hook 入力テスト、Claude settings テスト、Codex native checker の結果をオーナーが受け入れた。Claude の live permission engine と製品セッションでの role dispatch は測定していない。この受容は利用可能なローカル証拠の範囲に対する判断であり、製品セッションの実測を意味しない。

## 現行説明から移した判断履歴

2026-10-03 の是正で、以下の経緯・理由を現行手順、inventory、hook コメントから本 rationale に集約した。現行文書には現在の権限、動作、制約を残し、日付と判断経緯は本 rationale に記録する。

### ネイティブ規則の表現範囲と受容した偽陽性

Codex の prefix rule は直接の command prefix だけを比較し、後続の global option と引数は調べない。このため global option、wrapper、絶対パスを含む shell 呼び出しは command hook が判定する。Claude の glob は正規表現ではないため、global option を挟む GitHub CLI の狭いパターンでも引数中の同じ語列に一致することがある。Git の `git * merge` 系は `git show merge` も拾うため撤去し、global option 付き Git 呼び出しは hook 判定に寄せた。GitHub 側の一部 glob に残る偽陽性は、ネイティブの直接形カバーを維持する判断時に受容した。

### ロール境界コメントに含まれていた根拠

- Issue #308 と #341 の是正では、gated role を許可テーブルへ登録し忘れると hook の例外処理で fail-open し得ることが判明した。これを受け、必須 role table の自己検査と hook 実行失敗時の deny を設けた。`issue-fixer` だけに `karte` を追加し、`ingest-review` は指摘側の操作として主文脈に限定した。
- Issue #354 PR-4 では、既存の検証済み PR branch を掴む `adopt-branch` を issue-fixer に追加した。初回実装の issue-implementer は新規 branch を作るため同じ権限を持たない。
- Issue #495 の判断により、scope 外 finding も構造化 finding として記録し、status と verdict の評価対象に含める。
- Issue #129 で、shell hook は sandbox ではなく、agent type の詐称や hook 外の実行経路を阻止できない制約を明記した。
- Issue #303 で、agent-command-gate の matcher を context-mode MCP 実行ツールにも拡張した。現行 inventory は対応する実行面だけを記載する。

### 退役 notice と版履歴

現行 classifier policy は retired notice として `policy_version: 1.18` を持つ。旧 classifier contract は `classifier_version: 1.17` として archive に保存し、当該 notice の確認日は 2026-10-02 とした。retired notice は Issue #542 による classifier と pre-use/post-use 配線の撤去後に追加した。Issue 番号、移行理由、版遷移の説明は履歴としてここに保管する。

## 版の扱い

旧 classifier の最終 contract は `classifier_version: 1.17` である。Issue #542 で classifier 自体を撤去したため、その版は archive で履歴として固定し、現行の retired notice は `policy_version: 1.18` とした。`1.18` は notice の版であり、稼働 classifier の版ではない。

本是正は同じ未 merge Issue #542 内の設計・実装補正であり、`policy_version: 1.18` は本来 classifier の retired notice の版である。新たな classifier 契約を作らず、その notice をもう一度 bump する変更でもないため、版を据え置いた。
