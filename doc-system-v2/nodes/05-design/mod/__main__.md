**パス**: `spec_inspector/__main__.py`
**責務**: 合成ルート + CLI エントリポイント（DI 結線・コマンドライン引数解析）。
**公開 I/F**: `main(argv) -> int`
**依存**: adapters / core / domain（全層を結線。Protocol 実装の注入はここでのみ行う）
**依存方向**: __main__ ← adapters / core
