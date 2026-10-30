---
id: TD-agy-runtime-628
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TD-agy-runtime-628-r1.txt
---
# 目的

実機1.3.5の duration 観測を受理版1.3.3へ転用せず、未確認停止を検査する。

# 前提

PR #627 head `f09f3d099952e9da8293ae88da3749b2c276973e` が下段。
実機 agy は 1.3.5、既存出力契約の検証版は 1.3.3。
設定合成・安全設定・全 UC の根拠は未完了であり、通常 run の解除は検査対象外。

# 手順

1. `python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` を実行する。
2. 本番 runtime が `print_timeout_format_unverified` で process を呼ばないことを検査する。合成 process 試験は従来の数値文字列と外側 timeout の数値だけを確認し、実機互換性の証拠としない。
3. `python3 -m maintainability_lint check` と `python3 -m asset_parity check` を実行する。
4. 無課金の local slash command `/usage`、`/config`、`/permissions` で実機証跡を取得する。

# 期待結果

未起動 regression は成功する。合成 process 試験の成功は実機互換性を保証しない。
通常 run は未確認理由で未起動を維持する。
`test_agy_delegate_merge_guard` は #628 全 AC 未達のため既存の意図的失敗を維持する。
local slash command は conversation ID 空・turn 数 0・token 使用量 0。
既存設定への書込、認証ファイル読取、モデル推論は行わない。

## 実測（R1 是正ソース）

- TD版: 1。同一PR内の未merge版への是正のため版を維持。実装commit: `7bba0c5d3698a1c0d30091683b1006ff5fa6780c`。テスト前にcommitし測定中ソース変更なし。
- 実行日: 2026-10-22、WSL2 Ubuntu、uv一時環境Python 3.13。LLMレビュー雛形版/content_hashは対象外。
- 全量: `uv run --with coverage coverage run -m unittest discover -s tests -p test_*.py`。2421件、754.439秒、failures=2、exit 1。ログは上記log_ref。個人pathは置換。
- 失敗1: 本番 runtime merge guard。設定層・合成・起動環境・duration の未確認8理由。Issue #628未完了を示し期待値反転/skip/削除なし。
- 失敗2: `SettingsLayersTests.test_all_layers_read_only_audit_and_runtime_merge_still_unverified`。runtimeへ追加した `print_timeout_format_unverified` に既存テストの厳密な停止理由リストが追随していない。R1のテスト追随漏れとして主文脈へ報告し、追加是正前の失敗履歴を保持する。
- targeted process: `python3 -m unittest discover -s tests/unit -p test_agy_delegate_process.py`、5件PASS。新規の本番未起動試験を含む。合成processの成功は実機1.3.3互換性の証明ではない。
- maintainability_lint: violations=0、accepted_debt=77、baseline変更なし。asset_parity: 49件、MISSING=0、既存staleness18。
- coverage HTML生成成功、TOTAL 5294 statements / 613 miss / 88%。agy_delegateは設定対象外で変更箇所のcoverageではない。docidx未import警告あり。生成物はcommit対象外。
- 初回のuv起動はsandbox cache lockの読取専用エラーでテスト未起動。sandbox外で上記測定を一度実施した。

## 是正結果と残制約

1.3.5実測を1.3.3へ転用したs付与を撤回し、duration未確認を本番停止へ追加した。F-628-02はR2独立レビューで解消確認。追加のテスト追随漏れは上記FAIL2として未解消のまま報告する。
F-628-01は未解消。通常run停止、merge guard赤、実機5UC未実施、#607のbridge撤去不可を維持する。専用Windows userの本人セッションが未整備であり、受領した `/home/hiras/ws_agy/test` はWSL作業dirのみ。既存Windows実行user/profileは隔離されていない。認証読取/コピー、既存globalの変更は行っていない。
過去の `TR-agy-runtime-628-3e7d61b.md` は是正前commit専用の履歴であり、本測定の結果ではない。
