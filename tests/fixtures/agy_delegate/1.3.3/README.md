# agy 1.3.3 実測記録

2026-10-13、WSL <home>/.local/bin/agy、スクラッチ cwd、--output-format json --model gemini-3.8-flash-low --print-timeout <t> -p <prompt>。
出典: 提供済み実測（2026-10-13、agy 1.3.3、WSL/Linux scratch cwd、成功/拒否/timeoutは --model gemini-3.8-flash-low 指定） の stdout / stderr / exit をそのまま envelope に保存。quota_error はモデル指定前のデフォルトモデル枯渇ケース。
設定ファイル・合成規則は未実測。これらは正規化の証拠であり、wrapper の実機起動や許可検査合格の証拠ではない。
/usage は完全 JSON が提供されていないため fixture を作らない。追加 command と空 ID の拒否は合成境界テストで確認する。

設定内容の読取なし。全設定層適用/合成・WSL→Windows変換・wrapper通常UCは未測定。詳細根拠は [.ai rationale](../../../../.ai/rationale/agy-delegate.md) に追跡保存する。wrapperはmodel指定なしで起動する差があり、版probe形式も合成でのみ確認している。
