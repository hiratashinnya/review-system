# Issue #855「SendMessage による agent 再開が issue-start 系の gate／継続検査の対象外である件の、実害調査と対策」

- URL: https://github.com/hiratashinnya/review-system/issues/855
- 状態: open（2026-11-18取得）
- 本文: 7074文字/ 96行。全文: `../raw/issues-2026-11.jsonl`
- AC: 8件（未チェック: 8）
- Issue参照: #847, #829, #662, #694, #409, #606, #375, #517, #502, #559
- PR参照: #847
- 主見出し: ## 目的・背景 | ## Spike 定義 | ## 現状と根拠 | ### 確認済み（起票時に read-only で再読。checkout main 080d2ecf、2026-11-17） | ### 依頼元（主文脈）の観測。起票者は再確認していない | ### 推論（コード読みからの推論で未実測。調査で確認する） | ## Scope | ## Out of scope | ## Acceptance criteria | ## 対象 harness | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- issue-pipeline の作者ロール（ac-designer／change-planner／test-writer／issue-implementer／issue-fixer）を `Task|Agent` で dispatch するときは、PreToolUse の issue-start gate が前作者の回収・解放、remote exact OID、台帳の最新 owner、branch 束縛 marker を検査する。一方、停止した subage
-    | B | 対象外を意図として文書化する（再開は同一 context の続行で、検査の前提が違うと規範に明記） | 変更が最小 | a・b が実害なら放置になる。hook は sandbox ではなく、文書だけでは防げない |
-    | D | SendMessage 再開を禁止し、再 dispatch に一本化する | 検査が一箇所に収まる | 同一 role の再 dispatch は、上限停止 receipt が無い限り現状拒否される見込み（#662 が前提。上限停止では #829 により検査付きで可能）。再 dispatch では停止の都度、再開前の agent の文脈が失われる |
-    調査前の暫定見立て（調査結果で覆る）：C を軸に B を併記する。dispatch 検査の主眼は「別の作者への引き継ぎ」の取り違え防止で、同一 agent の続行には前提が合わない。一方で a・b は同一 agent でも起きうる。失敗コストは、許可しすぎは merge 後まで気づきにくく、拒否しすぎは即時に顕在化する非対称なので、実測で実害が出た項目は検査側へ倒す。
- - Parent／sub-issue／blocked-by／blocking：なし（設定しない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
