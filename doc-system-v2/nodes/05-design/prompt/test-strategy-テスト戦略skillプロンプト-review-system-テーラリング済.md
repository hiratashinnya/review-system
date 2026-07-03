skill `test-strategy`（review-system テーラリング済・active）を在グラフ化した skill 軸 PROMPT ノード。汎用標準の不変条件を継承し本 PJ のノブを埋めた、実装をどうテストするかを計画するプロンプト。実体＝`.claude/skills/test-strategy/SKILL.md`（由来＝`.claude/standards/test-strategy`・tailoring-registry）。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: doc-system の TD/TC/TR 3層に対応した本 PJ のテスト戦略を適用させる。public 関数ごとの unittest、TD（テスト設計 Markdown）＋TC（Python unittest コード）＋TR（result/log_ref フロントマター付きテスト結果）、テスト前コミット、Claude Code e2e も同じ3点セットで残す（PR8 失敗も残す・隠蔽/上書き禁止）。
**入力変数**: 実装対象の public 関数群（domain/core/parsing/prompts）／非決定シーム（`adapters/fake.py` の FakePlatformAdapter）／モジュール構成（design/02）／版スタンプ素材（S6）。
**出力形式**: TD（`tests/designs/<id>.md`・condition 付き）／TC（`tests/unit/`）／TR（`tests/reports/<id>-<commit>.md`・result/log_ref＋ヘッダに TD版/commit/プロンプト雛形版/基準content_hash/実行日時）／ログ（`tests/logs/<id>-<commit>.txt`）。1サイクル手順（コミット→unittest→TR 作成→FAIL 記録→e2e）。
**注意事項**: 失敗も残す（隠蔽・上書き禁止＋根本原因/対処を併記・PR8）。3点セットの対応を保つ。アダプタ境界＝テスト境界で core を決定化（非決定は LLM のみ＝PlatformPort の裏）。ランナーは `python -m unittest`（標準ライブラリのみ）。carrier=skill（slash command `/test-strategy`・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
