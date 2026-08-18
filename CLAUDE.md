# CLAUDE.md — 作業規約

このリポジトリでの仕様策定・設計の進め方。手法の棚卸しは `docs/methods/method-inventory.md`、
スキル/エージェントの計画は `docs/methods/asset-plan.md`、実体は `.claude/`。

> **本リポジトリは doc_system と review_system の2プロジェクトが同居**（ファイル構成・「正本」の所在は文脈で変わる）。
> 詳細は `.claude/rules/07-project-structure.md`「このリポジトリ＝2つのプロジェクトが同居（混同注意）」を参照。

> **本ファイルの中核規範は毎ターン注入される**（2026-07-28・context-mode 導入に伴う対策）。
> 実体＝`.claude/hooks/inject-governance.sh`（UserPromptSubmit）＋ `.claude/hooks/governance-directives.md`。
> **正本は本ファイルと `.claude/rules/` 配下のルールファイル群**で、`governance-directives.md` はその配送用の写し。
> **規約を変えたら写しも合わせる**（食い違ったら正本を正とする）。**追従漏れの検知は二段構え**——
> `.claude/hooks/check-governance-drift.sh`（PostToolUse）が写しの `<!-- synced-from: CLAUDE.md@<sha> -->`
> と**正本集合（本ファイル＋`.claude/rules/*.md`）の連結ハッシュ**を突き合わせ、食い違う間だけ
> warning を出す（反映後に sha を更新して解除）。**ハッシュ対象を集合にしたのは Issue #387 の是正**
> ——規範本文を `.claude/rules/` へ分割した後も本ファイル単体を見張っていると、規範の大半を占める
> rules 側の変更に対してフックもテストも一切反応しない。
> **ただしこのフックは常に `exit 0` の fail-open な nag であり、発火条件が
> 「編集対象の realpath が正本集合のいずれかに一致すること」のため、linked worktree 側で正本を
> 編集した場合は沈黙する**（Issue #323 で実測）。この抜け穴を塞ぐのが `tests/unit/test_governance_sync.py`
> ——marker と現在ハッシュの不一致に加え、`.claude/rules/*.md` と下記 `@` import 行の集合が
> 双方向一致することも CI で **fail-close** に検知する。フックが黙っていても、
> このテストが赤くなるので追従漏れは merge 前に必ず露見する。
> subagent 側の対策は各 `.claude/agents/*.md` 末尾の
> 「注入ブロックへの優先規定」。背景と設計は `.claude/hooks/README.md`。

> **「CLAUDE.md」は総称として読む**（Issue #387）。本ファイル・他の資産・コード docstring・ノード本文で
> 「CLAUDE.md」「CLAUDE.md の規約」「CLAUDE.md「〇〇」」と書かれている場合、特記なき限り
> **本ファイル ＋ 下記 `@` で import される `.claude/rules/*.md` 全体**を指す。節名で名指しされた規範は
> その集合の中で一意に解決できる（節名はルールファイル間で重複しない）。
> **ただし新規に書く参照は、ファイル境界を越えるものに限り `.claude/rules/NN-*.md` の実パスを併記する**
> ——総称で読めることと、読み手が一発で当該ファイルへ行けることは別だから。
> 行番号での引用（`CLAUDE.md L86` 等）は分割で無効になったので使わない（節名で参照する）。

## ルールファイル一覧
規約の本体は `.claude/rules/` 配下のファイル群に分割されている。**ここに `@` 行が無いルールファイルは
誰にも配送されない**ため、rules を追加・削除・改名したら同一 PR でこの一覧も更新する
（`tests/unit/test_governance_sync.py` が双方向一致を fail-close に検査する）。

@.claude/rules/01-principles.md
@.claude/rules/02-decision-process.md
@.claude/rules/03-operational.md
@.claude/rules/04-test-data.md
@.claude/rules/05-skills-agents.md
@.claude/rules/06-design-phases.md
@.claude/rules/07-project-structure.md
