"""プロンプト雛形の現行版（定数）。design/07・08・DD7。

`reviewer version`・版スタンプ・lint が同じ定数を参照（DRY）。MAJOR=構造/型→対応ロジック改修、
MINOR=文言のみ。MAJOR を上げる時は対応ハンドラ世代と同時に更新する。
"""
from __future__ import annotations

TEMPLATE_VERSIONS: dict[str, str] = {
    "role": "1.0",
    "review": "3.1",          # L1 評価（主・版スタンプに載る）
    "contradiction": "1.0",   # L2
    "type-estimate": "1.0",   # L3
    "merge": "1.0",           # L4
    "feedback-draft": "1.0",  # L5
    "scaffold": "1.0",        # L6
}

# 版スタンプに載せる主たる評価雛形版
REVIEW_VERSION = f"review:{TEMPLATE_VERSIONS['review']}"
