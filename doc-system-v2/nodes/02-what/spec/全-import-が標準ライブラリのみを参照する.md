**前提条件**: spec-inspector の実装ソースファイル群が1件以上存在し、静的解析が完了している。
**入力/トリガ**: CI が全ソースファイルの `import X` 文および `from X import Y` 文を抽出する。
**期待動作**: 全ソースファイルの import 文を解析したとき、外部パッケージ（PyYAML・requests・pydantic 等）への依存が 0 件であることを判定する。
**例**: `src/inspector.py` の全 import が `import sys`, `import os`, `import re`, `import pathlib`, `import json` のみ → 外部依存 0 件 → 違反なし。
