# Issue #857「feat(triage): 1a/1b/2aのレビュー指摘を承認済みポリシーで安全に自動確定する」

- URL: https://github.com/hiratashinnya/review-system/issues/857
- 状態: open（2026-11-18取得）
- 本文: 5028文字/ 56行。全文: `../raw/issues-2026-11.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #785, #784, #691, #832, #786, #683, #783, #781, #513, #523, #375, #409, #310, #856
- PR参照: なし
- 主見出し: ## 目的・利用者価値 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 対象 harness | ## Project / metadata の未設定事項
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - `.ai/guidance/triage-policy-v1.json` は現在 `status:draft` / `auto_apply_enabled:false`、`enabled_phases:["review","remediation_review"]`、各feature flag false。上位工程を無承認で自動有効化する根拠はない。
-    - **fix-here**：AC/承認済み設計/必須契約違反や退行など、根拠を確認できる実害のみ。**未修正findingはopenのまま**で、`resolved` にせず、次工程へ進めない。
-    - **owner-review**：未決仕様、AC/設計の新規要求、reviewerとtriagerの矛盾、根拠不足、前提脅威未確認、スコープ変更、重大リスク等はオーナー判断へ戻す。棄却**候補**を自動棄却・waiver・cleanとして扱わない。
- - [ ] 1a/1b/2aそれぞれに、`fix-here` が未修正findingをopenに保つ正常例と、`advisory` が `harm:none`・正本参照の充足時だけ確定する正常例がある。`harm:real`→advisoryを拒否する。
- - [ ] 根拠不足・矛盾・前提脅威不一致・新規要求・重大リスク・未承認scope変更を自動棄却/waiver/cleanとせず、理由付きowner-reviewへ集約できる。
- - **実装前提（blocked-by候補）**：#784「finding-triagerをレビュー工程へ提案モードで結線する」、#785「trusted自動仕分け確定とadvisory判定・STOP整合」、#832「triagerの到達経路・前提脅威の独立評価」、#786「検証済みhandoffによる自動deferred」（deferred適用部分）。
- 現在の接続から GitHub Projects の候補・field/options・更新権限を確認/設定できないため、Project item、Status、Workstream、Priority、Horizon、Review date、およびnative parent/blocked-by/relatedは未設定。ラベルは確認済みの既存labelのみを使用し、依存・関係は上記本文で記録する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
