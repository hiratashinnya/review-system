# Issue #792「[重複実装の統合] karte ingest の owner scope 適用・karte_notify の shell 解析・review envelope 語彙を1箇所へ（#375 / PR #697 レビュー由来）」

- URL: https://github.com/hiratashinnya/review-system/issues/792
- 状態: open（2026-11-18取得）
- 本文: 7153文字/ 96行。全文: `../raw/issues-2026-11.jsonl`
- AC: 14件（未チェック: 14）
- Issue参照: #697, #375, #512, #751, #531, #523, #785, #696, #745
- PR参照: #697
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### (1) F-375-04: ingest policy の動作モードと owner scope 適用の重複 | ### (2) F-375-06: 通知フックの shell 解析の二重実装 | ### (3) F-375-13: review envelope 語彙の複製 | ## Scope | ## Out of scope | ## 型別の補足（maintenance） | ## Acceptance criteria | ### (1) F-375-04 | ### (2) F-375-06 | ### (3) F-375-13
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 通知は fail-open（`karte_notify/hook.py` は対象外・判定不能で無出力 exit 0）。gate が受理するのに tokenizer／正規表現が見落とす形では、通知が**黙って欠落**し、利用者に欠落が見えない。
- - 既存の意図的受容: `trigger.py` のコメントは「エイリアス・別実行形は対象外（取りこぼしても fail-open で実害が小さい方に倒す）」と明記している（#512）。本 Issue はこの受容を維持する範囲と覆す範囲を明示したうえで統合方式を選ぶ。覆す根拠は、Codex reviewer 検出が gate 級の tokenizer 方式のため、同じ関数内で認識感度が不揃いになり、#512 が塞ごうとした「判定がオーナーへ届かない」穴を新た
- - [ ] 通知は fail-open（対象外・判定不能で無出力 exit 0）を維持している。
- - 前提: 対象コード（`karte/ingest_review.py`・`karte/reviewer_policy.py`・`karte_notify/codex_reviewer_trigger.py`・`karte/review_envelope.py` ほか）は PR #697 とその下段 #696 の stack にあり、main へ統合されるまで着手できない。PR は GitHub の blocked-by の対象外で、#375 は PR #

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
