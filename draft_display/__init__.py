"""gh-create-issue サブエージェントの成果物（handoff）をオーナーへ直送する SubagentStop フック。

本文を ``systemMessage`` としてチャットへ表示する（主文脈経由で二重に消費しないため）。
「再掲不要」は skill wrapper の規定で主文脈へ伝える（PostToolUse は非同期移譲で
SubagentStart より前に発火するため使わない）。
"""
