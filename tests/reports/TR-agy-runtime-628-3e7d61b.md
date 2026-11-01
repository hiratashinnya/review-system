---
id: TD-agy-runtime-628
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TD-agy-runtime-628-3e7d61b-full.txt
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

## 実測

- TD版: 1。実装対象commit: `3e7d61b8b07304a6ec67d99e6fc1bb5c96d157fa`。対象ソースはテスト前にcommit、実行中変更なし。
- 実行日: 2026-10-22、WSL2 Ubuntu。雛形版/基準content_hash: 対象外（LLMレビューの実行ではない）。
- 全量: `uv run --with coverage coverage run -m unittest discover -s tests -p "test_*.py"`、uv一時環境Python 3.13、2420件、667.780秒、failures=1、exit 1。
- 失敗: `unit.test_agy_delegate_merge_guard.RuntimeMergeGuardTests.test_production_runtime_has_no_unverified_stop_reasons`。既存7未確認理由が残る。期待値反転/skip/削除なし。
- agy関連: 直接 `python3 -m unittest discover -s tests/unit -p "test_agy_delegate*.py"`、Python 3.12、136件、50.017秒、同じ失敗1件。
- 変更したprocess試験4件は成功。これは subprocess 引数境界の検査であり、実機1.3.3のduration受理を証明しない。
- maintainability_lint: violations=0、accepted_debt=77、baseline変更なし。asset_parity: 49 assets、MISSING=0、既存staleness=18表示。
- coverage: HTML生成成功（`htmlcov/index.html`、未追跡）。設定対象TOTAL 5294 statements / 613 miss / 88%。`agy_delegate`は対象外のため、この数値を変更箇所のカバレッジと扱わない。
- 全量ログ中 `docidx was never imported` のCoverageWarningあり。
- local実機の初回観測は方法文書とセッションtool出力に記録。追跡ログへの再取得は `/usage` が外側30秒でTimeoutExpired。成功JSONは保存されていない。失敗記録: `tests/logs/TD-agy-runtime-628-local-20261022.json`。
- 全量ログのユーザー固有パスは `<workspace>` / `<linux-home>` に置換した。

## 根本原因・対処・残制約

全量失敗の原因は、設定合成・起動環境の受入証明が未完了なこと。既存globalは13件の追加command allowとcorpus deny欠落があり、通常runは停止維持。既存設定の無認可変更や認証ファイルコピーは行わない。
実機で確認した版は1.3.5、wrapperが受理する版は1.3.3。1.3.3の単位付きtimeoutの受理証跡は未取得。ここも独立レビューと是正へ渡す。
実機UC5種・起動adapter・層adapter・merge guard緑は未達。安全な環境整備のオーナー回答待ちであり、Issue #628完了とは判定しない。
