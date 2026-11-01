---
id: TD-agy-runtime-628
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TD-agy-runtime-628-r3-related.txt
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

## 実測（R3 テスト追随是正）

- TD版: 1。同一PR内の是正につき版を維持。source: `c447deaa799090cbda1403f0b98023d15d635a62`。テスト前にcommitし測定中変更なし。実行日: 2026-10-22、WSL2 Ubuntu、Python 3.12。雛形版/content_hashは対象外。
- `python3 -m unittest discover -s tests/unit -p test_agy_delegate*.py`: 137件、50.184秒、失敗1件、exit1。
- 唯一の失敗は本番runtime merge guard。F-628-01の未確認8理由を保持するための失敗であり、skip/削除/期待値反転なし。
- F-628-04の設定層試験は成功。全理由参照を横断し、現行の厳密list追随箇所は1箇所。他のcontains検査は維持、旧TR/logは元sourceの履歴として保持。
- maintainability_lint: violations=0、accepted_debt=77、baseline変更なし。asset_parity: 49件、MISSING=0、既存staleness18。
- 本sourceで全量/coverageは再計測していない。直前の全量測定はsource7bba0c5の2421件/754.439秒/FAIL2であり `TR-agy-runtime-628-r1.md` と対応logに保持した。全量PASSは主張しない。
- task内で全量coverage/HTML/reportを実施済み。今回の差分はテストの厳密期待list1箇所のみで本番コード不変、F01により全PASS不能のため、主文脈の検証方針に従い全agy関連137件を実行して追随漏れが解消したことを確認した。既存coverage88%とHTMLは前sourceの結果であり本sourceの測定結果ではない。

## 結果と残制約

F-628-04は修正し関連全件で該当試験の成功を確認した。独立再レビューへ引き渡す。
F-628-01は未解消。本番起動停止/実機5UC未実施/#607撤去不可を維持する。オーナー回答の `/home/hiras/ws_agy/test` はWSL作業dirのみで、専用Windows userは未作成と判明した。既存global/認証ファイルの変更・コピーはしていない。
