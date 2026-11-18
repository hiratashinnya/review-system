# Issue #181「Codex CLI に issue-implementer/pr-reviewer の push/merge 境界を機械強制する仕組みがない」

- URL: https://github.com/hiratashinnya/review-system/issues/181
- 状態: closed（2026-11-18取得）
- 本文: 1372文字/ 21行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #131, #180, #132, #133, #179, #129
- PR参照: #132, #133
- 主見出し: ## 発見経緯 | ## リスク内容 | ## 深刻度 | ## 受け入れ基準（調査→可能なら実装、不可能なら明文化） | ## 関連
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `.codex/agents/issue-implementer.toml`（該当行付近）・`.codex/agents/pr-reviewer.toml`（該当行付近）は、この push/merge 境界を **「Codex ではプロンプト規律として遵守する（機械的強制は別途導入されるまで前提にしない）」** と明記している。
-    - 持たない場合：実装不可能である根拠（公式ドキュメント等）を明記した上で、既知の限界として Issue #129 と同様の形で明文化し、`.codex/agents/issue-implementer.toml`/`pr-reviewer.toml` の記述を「機械強制なし・プロンプト規律のみ」の現状のまま維持するか、あるいはラッパースクリプト等の代替緩和策を検討し、選択肢＋推奨をオーナーに提示する（独断で「対応不要」と結論づけない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
