---
id: TD-agy-runtime-628
version: 1
condition: failure
---
# 目的

実機で発見した agy の duration 引数不一致を回帰検査し、設定・版の未確認停止を維持する。

# 前提

PR #627 head `f09f3d099952e9da8293ae88da3749b2c276973e` が下段。
実機 agy は 1.3.5、既存出力契約の検証版は 1.3.3。
設定合成・安全設定・全 UC の根拠は未完了であり、通常 run の解除は検査対象外。

# 手順

1. `python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` を実行する。
2. subprocess 境界で duration が `<秒数>s`、外側 timeout が秒数 + 10 の数値であることを検査する。
3. `python3 -m maintainability_lint check` と `python3 -m asset_parity check` を実行する。
4. 無課金の local slash command `/usage`、`/config`、`/permissions` で実機証跡を取得する。

# 期待結果

新規 regression は成功し、prompt と cwd は既存入力を保つ。
通常 run は未確認理由で未起動を維持する。
`test_agy_delegate_merge_guard` は #628 全 AC 未達のため既存の意図的失敗を維持する。
local slash command は conversation ID 空・turn 数 0・token 使用量 0。
既存設定への書込、認証ファイル読取、モデル推論は行わない。
