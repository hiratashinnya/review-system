# Issue #345「issue-start gate が Claude Code on the web 環境で常に API_PERMISSION となり /issue-pipeline を起動できない」

- URL: https://github.com/hiratashinnya/review-system/issues/345
- 状態: closed（2026-11-18取得）
- 本文: 20078文字/ 337行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #344, #293, #303, #5, #296, #297, #317, #322, #129, #1
- PR参照: #322
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 再現 | ### gate 単体でも同じ | ### 原因 | ### 影響 | ## Scope | ### 起票時に挙げた3候補の実測評価（2026-08-11・公式ドキュメント調査＋実機測定） | ### ［A］の選択肢 全体像（2026-08-11 Claude Code (AI) が整理・オーナー提案の3案を含む） | #### ④⑤の評価（2026-08-11 GitHub 公式ドキュメントで trigger を確認） | ### ④' が既存アーキテクチャに適合すること（実装量の見積り根拠） | #### ④' の snapshot 生成コスト測定（2026-08-12 実測・Claude Code (AI)）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - **［B］到達できない環境を検出したときの挙動を決める**（現状は `API_PERMISSION` で fail-close。**fail-close を維持するのか、到達不能を別 reason に分離するのか**を明示的に決める。少なくとも「届かない」を「権限がない」と表示する誤分類は解消する）
- | **proxy 対応** | **既に実装済み・追加実装の余地なし** | `blocker_gate` は `install_opener`/`build_opener` を使わず素の `urlopen` を呼ぶ（`github.py:78`）。素の `urlopen` は既定 opener＝`ProxyHandler` を含み、`HTTPS_PROXY` 等の環境変数を**既に尊重している** |
- | blocker が **close/reopen** された | `issues` の `closed`/`reopened` | **使える** | 低（stale でも fail-close 側に倒れる） |
- | **`blocked_by` の追加・削除** | `issue_dependencies`（`blocked_by_added` 等）が**存在する** | **使えない**——`issue_dependencies` は Actions の trigger 一覧に無い。`issues` の activity types（`opened`/`edited`/`closed`/`reopened`/`labeled`/`field_added` 等20
- open issues: 62
- **→ 既存 REST collector の再利用では、承認済みの「cron 5分／staleness 上限 10分」は成立しない。** 加えて呼び出し数は open Issue 数に比例するため、リポジトリの成長でさらに悪化する。
- GraphQL の `Issue` 型に依存関係フィールドが存在することを introspection で確認した（`blockedBy` / `blocking` / `subIssues` / `parent` / `issueDependenciesSummary`）。実際に1クエリで全 open Issue とその直接依存を取得した結果：
- **→ GraphQL なら承認済みの「cron 5分／staleness 上限 10分」がそのまま成立する（枠の 0.5%）。** 推移閉包は全 open Issue の直接依存が1回で揃うため **snapshot 上でオフラインに計算できる**（blocker が closed Issue でも `state` が同時に返るため判定可能）。
- **エージェントに「引き金を引かせるだけ」で、書込は hook が行う**設計にすれば、エージェントによる内容の捏造は防げる（hook は生のツール応答を見るため）。残る裁量は「いつ・どの Issue について引くか」であり、**対象 Issue 番号と取得時刻を結果に束縛し、不一致・期限切れは fail-close** することで実用に耐える見込み。前提として `agent-command-gate.sh` を MCP ツール名へ拡張した #303 の実

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
