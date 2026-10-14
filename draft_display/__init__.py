"""gh-create-issue サブエージェントの成果物（handoff）をオーナーへ直送する SubagentStop フック。

本文を ``systemMessage`` としてチャットへ表示し、同じ出力の ``additionalContext`` で主文脈へ
「表示済み・再掲不要」または「表示できなかった」を伝える（PostToolUse は非同期移譲で
SubagentStart より前に発火するため使わない）。
"""
