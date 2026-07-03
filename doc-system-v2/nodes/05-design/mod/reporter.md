**パス**: `spec_inspector/reporter.py`
**責務**: P-4（レポート生成・G# 採番・終了コード決定・P-4-1〜P-4-4）を実現する。
**公開 I/F**: `render_report(violations) -> str`, `exit_code(violations) -> int`
**依存**: domain（ViolationRecord）
**依存方向**: core ← domain
