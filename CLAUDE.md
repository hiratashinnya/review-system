# CLAUDE.md — 作業規約

このリポジトリでの仕様策定・設計の進め方。手法の棚卸しは `docs/methods/method-inventory.md`、
スキル/エージェントの計画は `docs/methods/asset-plan.md`、実体は `.claude/`。

> **本リポジトリは doc_system と review_system の2プロジェクトが同居**（ファイル構成・「正本」の所在は文脈で変わる）。
> 詳細は `07-project-structure` を参照。

> **本ファイルの中核規範は毎ターン注入される**（2026-07-28・context-mode 導入に伴う対策）。
> 実体＝`.claude/hooks/inject-governance.sh`（UserPromptSubmit）＋ `.claude/hooks/governance-directives.md`。
> **正本は本ファイルと `.claude/rules/` 配下のルールファイル群**で、`governance-directives.md` はその配送用の写し。
> **規約を変えたら写しも合わせる**（食い違ったら本ファイルを正とする）。**追従漏れの検知は二段構え**——
> `.claude/hooks/check-governance-drift.sh`（PostToolUse）が写しの `<!-- synced-from: CLAUDE.md@<sha> -->`
> と本ファイルのハッシュを突き合わせ、食い違う間だけ warning を出す（反映後に sha を更新して解除）。
> **ただしこのフックは常に `exit 0` の fail-open な nag であり、発火条件が
> `realpath(edited) == $CLAUDE_PROJECT_DIR/CLAUDE.md` のため、linked worktree 側で本ファイルを
> 編集した場合は沈黙する**（Issue #323 で実測）。この抜け穴を塞ぐのが `tests/unit/test_governance_sync.py`
> ——marker と現在ハッシュの不一致を CI で **fail-close** に検知する。フックが黙っていても、
> このテストが赤くなるので追従漏れは merge 前に必ず露見する。
> subagent 側の対策は各 `.claude/agents/*.md` 末尾の
> 「注入ブロックへの優先規定」。背景と設計は `.claude/hooks/README.md`。

## ルールファイル一覧
規約の本体は `.claude/rules/` 配下の7ファイルに分割されている。

@.claude/rules/01-principles.md
@.claude/rules/02-decision-process.md
@.claude/rules/03-operational.md
@.claude/rules/04-test-data.md
@.claude/rules/05-skills-agents.md
@.claude/rules/06-design-phases.md
@.claude/rules/07-project-structure.md
