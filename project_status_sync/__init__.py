"""GitHub Project の `Status` を blocker snapshot から同期する（Issue #460）。

判定ロジックは自前で持たず、``blocker_gate.evaluator`` をそのまま呼ぶ。
gate と board が別の答えを出すこと自体が本 Issue の解こうとしている問題なので、
「同じ意味の実装を2つ持つ」形にはしない。使い方は ``README.md``。
"""
