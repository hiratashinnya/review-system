# CLAUDE.md — 作業規約

> **D-001 — リポジトリの目的**
>
> 本リポジトリの目的は、オーナーが AI 駆動開発のノウハウを獲得すること。review_system はその題材であって目的ではない。製品の進捗はこのリポジトリの成功指標ではない。ハーネスを作り込んで品質・進捗・コストを改善すること、およびアンチパターンを経験すること自体に価値がある。獲得したノウハウの転用先は車載 ECU であり、品質担保はマストである。

このリポジトリでの仕様策定・設計の進め方。手法の棚卸しは `docs/methods/method-inventory.md`、
スキル/エージェントの計画は `docs/methods/asset-plan.md`、実体は `.claude/`。

> **本リポジトリは doc_system と review_system の2プロジェクトが同居**（ファイル構成・「正本」の所在は文脈で変わる）。
> 詳細は `.claude/rules/07-project-structure.md`「このリポジトリ＝2つのプロジェクトが同居（混同注意）」を参照。

> **本ファイルの中核規範は毎ターン注入される**（2026-07-28・context-mode 導入に伴う対策）。
> 実体＝`.claude/hooks/inject-governance.sh`（UserPromptSubmit）＋ `.claude/hooks/governance-directives.md`。
> **正本は本ファイル、`.claude/rules/` 配下のルールファイル群、公式 import する `.ai/guidance/common.md`、
> 主文脈専用の `.claude/main-context/*.md`（後述「主文脈専用の規定」）**で、`governance-directives.md` はその配送用の写し。
> **規約を変えたら写しも合わせる**（食い違ったら正本を正とする）。**追従漏れの検知は二段構え**——
> `.claude/hooks/check-governance-drift.sh`（PostToolUse）が写しの `<!-- synced-from: CLAUDE.md@<sha> -->`
> と**正本集合（本ファイル＋`.claude/rules/*.md`＋`.ai/guidance/common.md`＋`.claude/main-context/*.md`）の連結ハッシュ**を突き合わせ、食い違う間だけ
> warning を出す（反映後に sha を更新して解除）。**ハッシュ対象を集合にしたのは Issue #387 の是正**
> ——規範本文を `.claude/rules/` へ分割した後も本ファイル単体を見張っていると、規範の大半を占める
> rules 側の変更に対してフックもテストも一切反応しない。
> **ただしこのフックは常に `exit 0` の fail-open な nag であり、発火条件が
> 「編集対象の realpath が正本集合のいずれかに一致すること」のため、linked worktree 側で正本を
> 編集した場合は沈黙する**（Issue #323 で実測）。この抜け穴を塞ぐのが `tests/unit/test_governance_sync.py`
> ——marker と現在ハッシュの不一致に加え、common guidance と main-context が正本集合に入ること、`.claude/rules/*.md` と下記 `@` import 行の集合が
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
規約の本体は `.claude/rules/` 配下のファイル群に分割されている。Claude Code は `.claude/rules/*.md` を
`@` 行の有無にかかわらず自動で読み込み、**主文脈にもサブエージェントにも配送する**（公式仕様・Issue #585 で確認）。
下記の `@` 行は、どのファイルが規約に含まれるかを読み手が一覧できる索引として保守する。
rules を追加・削除・改名したら同一 PR でこの一覧も更新する
（`tests/unit/test_governance_sync.py` が双方向一致を fail-close に検査する）。

@.claude/rules/01-principles.md
@.claude/rules/02-decision-process.md
@.claude/rules/03-operational.md
@.claude/rules/04-test-data.md
@.claude/rules/05-skills-agents.md
@.claude/rules/06-design-phases.md
@.claude/rules/07-project-structure.md
@.ai/guidance/common.md

## 主文脈専用の規定
**主文脈（オーナーと直接やり取りする側）にしか当てはまらない規定は `.claude/rules/` に置かない**——
rules に置くとサブエージェントにも配送され、主文脈とサブエージェントで読み込みを分ける手段が無いため
（`paths:` は触るファイルでしか絞れず、サブエージェントの `omitClaudeMd` は CLAUDE.md 一式をまるごと外す）。
**主文脈専用の規範の置き場は `.claude/main-context/*.md` だけ**（自動読み込みされない）。配送は次の2経路で、
どちらも主文脈のイベントでしか発火しないためサブエージェントへは届かない。
- **全文**＝`.claude/hooks/orchestrator-context.sh`（SessionStart の startup/clear/compact）が、
  委譲ルールに続けて名前順に注入する。
- **要約**＝`.claude/hooks/inject-governance.sh`（UserPromptSubmit）が毎ターン注入する
  `governance-directives.md` の項12。全文を毎ターン積むと文脈を圧迫するので要約だけを載せる。
  要約は写しなので main-context は正本集合に入り、追従漏れは冒頭の二段構えで検知される。
  main-context の本文を変えたら項12も合わせる。

**orchestrator-context との併存**：`.claude/hooks/orchestrator-context/orchestrator-task-delegation-rules.md`
も主文脈だけに届くが、これはリポジトリの規範ではなく、委譲プロンプトの書き方（Goal/Context/Constraints/
Deliverable の様式・手順の細部を指示しない）を定める汎用のオーケストレータ役割定義である。
写しも追従検査も持たない。リポジトリ固有の主文脈専用規範（オーナーへの報告・質問の仕方等）は
main-context に置く。置き場は「汎用の役割定義か、リポジトリの規範か」で分け、配送は同じ SessionStart
フックを共有する（委譲ルール→main-context の順）。

**既知の限界（フック単一経路・fail-open）**：main-context は rules と違い Claude Code の自動読込に乗らず、
フックだけが配送経路である。フックが動かない環境（フック無効化・ワークスペース信頼の未受諾・python3 不在・
スクリプト異常）では全文も要約も主文脈に届かない。どの失敗経路も作業を止めない（exit 0）ので、
画面上は何も起きない。検知手段は `claude --debug` で起動し、フックログの stderr に
`[orchestrator-context]`・`[inject-governance]` の警告が無いこと、SessionStart と UserPromptSubmit の
additionalContext に本文が載っていることを確かめること。読めない・UTF-8 として不正なファイルは警告して
飛ばし、残りの注入は続ける。`resume` では全文を再注入しない（会話に残る全文と毎ターンの要約に依る）。

現在の収録：`01-owner-communication.md`（オーナーへの報告はチャットが正本・報告タイミング・`AskUserQuestion` の使用）。
経緯は `.ai/rationale/main-context-injection.md`。
