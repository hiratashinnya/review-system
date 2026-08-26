# codex-review — 設計経緯・制約（rationale・非規範）

> **これは規範ではない。** 正本は `.claude/skills/codex-review/SKILL.md` であり、本文はこの Claude 専用 skill の設計背景を保管する。

この skill は in-repo の Claude review を置き換えるものではなく、別モデルファミリの第二意見を追加で得るための入口として設計した。`pr-reviewer` は in-repo の review／コメント／merge を担い、`agy-delegate` は agy MCP 経由の Gemini 委譲を担うため、`codex-review` は `codex exec` を使う OpenAI CLI 経路に限定している。

別プロセスで実行するため、Claude の token/session limit に影響しない追加のレビュー経路になる。ただし `codex` CLI、ChatGPT login、ローカル rollout 保存先に依存するため、クラウドやヘッドレス実行へ移植しない。この配置・非移植判断は `.ai/Individually-managed-lists.md` にも記録されている。

