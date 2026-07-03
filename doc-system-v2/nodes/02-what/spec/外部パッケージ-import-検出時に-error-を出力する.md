**前提条件**: spec-inspector の実装ソースファイル群が1件以上存在し、静的解析が完了している。
**入力/トリガ**: CI が外部パッケージへの `import` 文を1件以上検出する。
**期待動作**: 外部パッケージ import を検出したとき、当該行を指す ERROR を1件出力する。
**例**: `import yaml` が `src/parser.py` 行3に存在 → `ERROR|src/parser.py:3|NFR-2-check|(none)|external package import: yaml` を出力。
