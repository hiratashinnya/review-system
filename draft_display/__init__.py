"""gh-create-issue サブエージェントの成果物（handoff）をオーナーへ直送するフック群。

SubagentStop で本文を ``systemMessage`` としてチャットへ表示し、PostToolUse で主文脈へ
「表示済み・再掲不要」を ``additionalContext`` として注入する（本文を主文脈経由で
二重に消費しないため）。
"""
