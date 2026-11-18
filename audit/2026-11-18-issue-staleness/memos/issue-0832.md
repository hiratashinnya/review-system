# Issue #832「improvement(triage): triager が reviewer の到達経路・前提脅威の根拠を独立評価し、棄却候補を理由コード付きで owner-review に集約提示する」

- URL: https://github.com/hiratashinnya/review-system/issues/832
- 状態: open（2026-11-18取得）
- 本文: 3809文字/ 57行。全文: `../raw/issues-2026-11.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #830, #785, #691, #781, #816, #783, #784, #856, #723, #370
- PR参照: #816
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 対象 harness | ## 2026-11-17 既存評価契約の上位工程への適用（#691）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- 実運用で起きない指摘や、うっかりミス対策に悪意耐性を求める指摘で、レビューが収束しない。reviewer が書いた到達経路・前提脅威の根拠（#830）を finding-triager が独立に評価し、根拠が成り立たない finding を「棄却候補」として理由コード付きで owner-review に集約提示する。reviewer の harm は変えない。処置は owner が決めるため**件数は減らず、提示の集約が効果**で、非ブロッキング化は #7
- - draft PR #816（#783・37 files）の `finding_triager/assessment.py` は証拠カテゴリ ac/vd_cp/design/change と facts を厳密一致で検査し、`triage_policy/contract.py` は `VERSION="1.0"` 固定。評価入力の追加は schema/policy の版上げで、#816 のファイルに及ぶ。
- - 前提脅威の参照先: 「hook／gate は sandbox ではない」等の限界が複数文書にあるが、単一の脅威前提の置き場は未確認。
- 1. triager の評価契約に、reviewer の到達経路・前提脅威の根拠の独立評価（成り立つ／不足／参照先なし）を追加する。reviewer の記述を鵜呑みにしない。対象は既存の `review/remediation_review` に加え、#691 の2026-11-17決定に基づく上位工程 `verification_design`（1a）・`solution_planning`（1b）・`test_design`（2a）の**提案評価**も
- - [ ] 棄却候補と fix-here 規則（contract_violation 等が真）・reviewer_conflict・high_risk の優先関係と、triager 自身の harm 判定との相互作用を決め、決定表テストで固定する。表は (a) 理論上のみ (b) 悪意前提のみで文書化された前提の外 (c) うっかり経路で到達可能 (d) 権限境界の迂回かつ到達可能 (e) 根拠欠落、を含み、期待は (a)(b) だけが棄却候補、(c)(d
- - 親: #691（オーナー決定）。blocked-by: #783（PR #816 の merge。ファイルが重なる）、#830（reviewer 側の根拠記載契約）。
- - 単なる未記載や「根拠なし」は自動で指摘を捨てる根拠にならない。前提脅威が成り立たないことの積極的な根拠がある場合のみ、棄却**候補**として理由コードを提示する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
