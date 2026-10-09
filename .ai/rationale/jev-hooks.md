# Jev hooks の検証記録配置

実行可能な TC は CI が直接探索する `tests/jev_hooks/` に置き、TD/TR/ログは汎用ハーネスの実装と対応づけやすい `jev_hooks/verify/` に置く。これにより、テスト発見の入口を既存のテスト階層に保ちながら、ハーネス固有の検証記録を review_system の製品検証記録と混在させない。
