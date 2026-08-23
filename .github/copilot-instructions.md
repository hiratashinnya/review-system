# プロジェクト常時コンテキスト（review-system）

このファイルは GitHub Copilot に常時適用される。spec-principles（PR1–PR10）と作業規約の要点を含む。

---

## 仕様設計・点検の原則（PR1–PR10）

- **PR1 もので分ける（発生源基準）** — 入出力は「もの（実体）＋発生源（外部アクター）」だけで分ける。使い道や内部発生プロセスでは分けない。
- **PR2 2軸（判定の種類を混ぜない）** — 機械判定（順序ある属性＝自動ゲートできる）と運用ルール（事実性・妥当性＝人が確認）を分ける。運用ルールは機構＋デフォルトに留める。
- **PR3 系外＝非イベント** — システムを介さない変更はイベント化・入力化しない。必要な検査は処理時に毎回実行して警告する。
- **PR4 観測できないものは持たない** — 顛末をシステムが観測できない事象に対する機能は作らない。
- **PR5 状態の要否** — 毎回作り直せる→無状態。過去を覚えていないと成立しない（取り消し・既出判定・蓄積）→状態。導出物は状態化しない。
- **PR6 価値経路を遮断しない** — すべての入力が、プロセスを通って価値（出力）まで連続して届くこと。途切れ＝設計の穴。
- **PR7 矛盾は停止して打ち上げ（空で止めない）** — 既存決定と両立しない事実は勝手に解決せず止めて確認する。止めるときも原案・比較・理由付き推奨を必ず添える。止める前にノードを起票する：未決論点・質問＝Q ノード / 既存ノードへの指摘・矛盾＝FND ノード。①起票→②ダッシュボード更新→③推奨を添えて停止の順を守る。
- **PR8 フル論理設計＋MVP印** — 論理は完全に作り、MVP で削る所は印で残す（消さない）。
- **PR9 DFD レベリング** — 階層をまたぐ時に上位/下位へ直接繋がない。外部・データストアは L1 境界に繋ぎ、リーフへは親を経由。
- **PR10 認識合わせ先行** — 着手前に手順を整理・提案し、不明点を質問してから動く。重い作業ほど先に握る。

---

## 作業規約（CLAUDE.md ＋ .claude/rules/*.md 要点）

> `CLAUDE.md` 本体は `.claude/rules/01〜07-*.md` に分割済み（Issue #357/#373）。ここは
> `.claude/hooks/governance-directives.md`（Claude Code に毎ターン注入される12項目の恒常規範）と
> 現行 rules の要点ダイジェスト。矛盾したら `CLAUDE.md`＋`.claude/rules/*.md` を正とする。

- **意見なき停止は禁止（PR7）**：矛盾・情報不足・オーナー判断必須で止めるときも、原案・比較・理由付き推奨/非推奨を必ず添える。
- **起票してから止める**：論点・矛盾・情報不足→①ノード起票（未決の質問＝Q ノード／既存ノードへの指摘・矛盾＝FND ノード、`verification-author` に委譲）→②ダッシュボード更新（doc_system は `doc-system-v2/00-dashboard.md`、review_system は `docs/dashboard.md`）→③選択肢＋推奨を添えて停止。チャットで指摘するだけで起票しないのは禁止。
- **起票先はプロジェクト区分で決める**：判定軸は「そのハーネスが doc_system／review_system に含有されるか」。含有される（著作・検証エージェント、仕様策定スキル、`dsv2`、review_system 本体）→従来どおりノード起票＋ダッシュボード更新。含有されない汎用開発ハーネス（Issue 運用パイプライン・実行環境フック・`agy-delegate`／`codex-review`等の外部委譲・`asset_parity`・CI 定義等）→ノード起票せず GitHub Issue で処置（`area:harness`）。
- **「対応不要」を AI が独断で書かない**：指摘の処置要否・スプリント繰り越しはオーナー判断。AI が単独で「対応不要」「将来検討でよい」と結論づけてコメント・クローズしない。
- **スケジュール独断禁止**：FND/Q/DD/PEND の `scheduled` を次スプリント以降へ繰り越すことは、オーナーの明示指示なしに行わない（現行スプリントを設定すること自体は既定で確認不要）。「実害ゼロ・軽微・後でよい」は独断の根拠にならない。
- **DD# は設計フェーズの判断ログ**：仕様で一意に決まらない点は迷いを推奨案で暫定決定し、DD#（論点→選択肢→推奨→暫定決定→影響範囲）に記録して前進。
- **ノード著作は専門エージェントに委譲し、2段で確定する**：VAL/SR/FR/NFR→requirements-author／SPEC→spec-author／分析層→analysis-author／設計層→design-author／検証層→verification-author が `tmp/<sprint>/` に出力→**reconciliation-validator**（read-only 構造検証・VALIDATION_OK/ROLLBACK）→合格なら**reconciliation**（self_fix 適用・本ファイル確定書き込み）。主文脈で本ファイルへ直接書かない。
- **課金の独断禁止**：CI・外部サービス連携は無課金で実現できる方法を優先する。課金が発生する構成が必要な場合は、実装前に必ずオーナーの明示認可を取る。
- **PR レビュー・GitHub コメント運用（明示・独断禁止）**：レビュー指摘への返信・コメントは AI（Copilot）による対応であることと実施した処置を具体的に明記する。指摘は原則、起票→反映まで追い、据え置きはオーナーが明示的に「不要/繰り越し」と判断した場合のみ、その旨と判断者を明記する。
- **PR8「消さない」の適用範囲は区分で決める**：決定履歴・却下案・経緯・例外理由（区分1）は削除せず `.claude/rationale/` へ移設または `git mv` で archive 化する。今の正しい手順を記す手順書・契約文（区分2）は古くなったら本文を書き換える（訂正の追記積み上げは禁止）。判定に迷ったら「読み手の行動を決めるか（区分2）／なぜそう決めたかを説明するか（区分1）」で分ける。
- **レートリミット由来の品質降格は禁止**：エージェントがレートリミット／セッション上限で停止しても、モデル降格・effort 低下・委譲取りやめによる代行はしない。正しい対処は同じ構成でそのまま再投入すること。
- **オーナーへの報告はチャットが正本**：オーナーの判断を要する事項（打ち上げ・据え置き可否・スコープ判断・矛盾）はチャットに全文を出す。PR コメント・ノード等の記録は永続化目的の副次記録であり、書いたことをもって報告済みとはみなさない。
- **新資産前に asset-auditor で重複/競合点検**（A14）。
- **資産のテーラリング運用（A16）**：テーラリング実体は `.claude/`（docs ではない）。汎用標準は `.claude/standards/<name>/`（非活性）、テーラリング済 active は `.claude/skills/<name>/`、対応は `.claude/tailoring-registry.md`。
- **実装設計フェーズ（凍結セット・A17–A20）**：仕様確定後・実装着手前に凍結セット（モジュール／IF／プロトコル／永続／オーケストレーション／プロンプト／ログ・版／テスト戦略）を固める（索引 `docs/design/README.md`）。設計一式は spec-inspector で総点検してから実装へ。
- **review_system 本体の実装は Python・原則標準ライブラリのみ**。

---

## このリポジトリの正本（2プロジェクト同居・混同注意）

本リポジトリには **doc_system**（仕様策定支援ツール・メタ側）と **review_system**（AI レビューツール本体）が同居する。「正本」はどちらの話かで指す実体が変わる（詳細＝`.claude/rules/07-project-structure.md`）。

- **① doc_system**（本リポジトリの開発方法論そのもの）：正本＝`doc-system-v2/`（ノードグラフ・`nodes/**`＋`00-dashboard.md`＋`config.yml`）＋ `.claude/`（資産・規約）＋ `CLAUDE.md` と `.claude/rules/*.md`。機械定義ドキュメント `docs/doc-system/` は例外的に正本の一部。v1 `doc-system/` は `doc-system-v1-archive/` へ retire 済み（非正本）。運用ハブ＝`doc-system-v2/00-dashboard.md`。
- **② review_system**（開発対象の製品本体）：正本＝**`docs/` 配下**（`docs/doc-system/` を除く＝要件・設計・スキーマ・プロセス・メソッド・ダッシュボード）。①の「`docs/` は非正本」は doc_system 自身の記述についての規定であり、doc-system-v2 コーパスに review_system 固有の要件/設計ノードが無い以上 **review_system には適用しない**。運用ハブ＝`docs/dashboard.md`・`docs/design/decisions.md`（DD#）。
- 実装：review_system 本体＝`review_system/`（Python・原則標準ライブラリのみ）。テスト＝`tests/unit/` は doc_system／review_system 両方のテストが同一ディレクトリに同居するため、判別は import 先で行う（`review_system.*` import＝review_system 対象、`dsv2`／`archive.docidx_v1`／`asset_parity` 等の import・exec＝doc_system 対象）。

---

## スキル一覧（自動発見・Copilot が用途に応じ自動選択する Skill）

| Skill | 用途 |
|---|---|
| `align` | 着手前の認識合わせ（手順分解・提案・不明点質問・固定パラメータ宣言） |
| `value-trace` | イベント→プロセス→出力の価値経路トレース・DFD レベリング検証 |
| `mvp-scope` | 価値ベースの MVP スコープ決定（依存 DAG→ビルド順の提案） |
| `schema-design` | 外部設定/基準ファイルのスキーマ設計（frontmatter＝機械／body＝人手の二層split） |
| `domain-model` | 確定済みデータ辞書からの型安全・イミュータブルなドメインモデル導出 |
| `architecture-design` | 確定済み論理 DFD＋ドメインモデルからの物理モジュール/依存アーキ設計（ヘキサゴナル） |
| `orchestration-design` | ランタイム制御フロー設計（swimlane・Result 型・fail-close・ログチャネル分離） |
| `prompt-design` | LLM システムプロンプトテンプレ設計（役割制約・組立・injection 対策・版管理） |
| `test-strategy` | 本プロジェクト（review-system）のテスト戦略（TD/TC/TR・unittest・commit-before-test） |
| `bloom-model-tier` | Bloom 認知分類でカスタムエージェントのモデル階層（model:/effort:）を選定 |
| `docidx` | **v1-archive 専用**のノード検索/読み込み（現行 v2 コーパスは対象外） |
| `coverage-html` | `unittest discover` によるカバレッジ HTML レポート生成（`htmlcov/index.html`） |
| `issue-pipeline` | 複数 Issue の実装→PR→レビュー→マージ→クローズをオーケストレーション。**Copilot には `issue-implementer`／`issue-fixer`／`pr-reviewer` 専用 Agent が未移植**（下記エージェント一覧の注記参照）。利用可能な実行手段へ読み替えるが役割分担・順序・オーナー判断・STOP 契約は維持する |

## プロンプト一覧（`/` で明示起動するオーケストレータ）

| コマンド | 用途 |
|---|---|
| `/asset-lateral-deploy` | `.claude` 資産を GitHub Copilot 向けに手書き変換 |
| `/asset-pipeline` | メソッド→スキル/エージェント 資産化パイプライン |
| `/impl-design-pipeline` | 実装設計フェーズ凍結セット化（spec→実装の橋渡し。architecture-design→orchestration-design→prompt-design→test-strategy） |
| `/spec-pipeline` | 要件から MVP スコープまでの仕様設計パイプライン |

> Claude Code 側に存在する `/agy-delegate`（Antigravity CLI 委譲）・`/codex-review`（Codex CLI への第二意見レビュー委譲）・`/gh-create-issue`（Issue 起票）は、ローカル CLI／認証／ChatGPT ログイン等の環境依存、または Claude Code と Codex の2環境に限定した明示スコープのため、意図的に Copilot 非移植（`asset_parity/exceptions.py`・`.claude/tailoring-registry.md` に記録済み）。

## エージェント一覧（`.github/agents/`）

- **ノード著作（`tmp/<sprint>/` 出力）**：`requirements-author`（VAL/SR/FR/NFR）／`spec-author`（SPEC）／`analysis-author`（ACTOR/I/O/D/P/E/TERM）／`design-author`（ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT）／`verification-author`（TD/TC/TR/VERIFY/FND/DD/Q/PEND）
- **バッチ委譲**：`authoring-fanout`（複数の独立した著作対象を同一 `*-author` へ一括ファンアウトし、まとめて `reconciliation-validator`→`reconciliation` へ渡す非対話オーケストレータ。ROLLBACK・矛盾・曖昧は STOP して呼び出し元へ報告）
- **確定（検証→書込の2段）**：`reconciliation-validator`（read-only 構造検証・VALIDATION_OK/ROLLBACK。Write/Edit を持たず構造的に本ファイルへ書けない fail-close）→`reconciliation`（self_fix 適用・本ファイル確定書き込み・tmp 掃除）
- **点検・分析**：`spec-inspector`（仕様/設計点検・G# 出力）／`structured-analysis`（DFD 分解）／`asset-auditor`（資産の重複/矛盾/競合監査・read-only）
- **ノード検索**：`dsv2-lookup`（doc-system-v2 ノードを `dsv2 index` の meta.json で絞り込み、該当本文だけをダイジェスト返却）
- **設定操作**：`doc-system-config-operator`（`doc-system-v2/config.yml` と関連 CFG/SCM/SPEC/PROMPT 資産の説明・点検・変更。review_system 側の config は対象外）
- **共有参照**：`doc-system-v2-authoring`（各 `*-author` が参照する共通ポインタ。単独では起動しない）

> Claude Code 側に存在する `agy-delegate`（エージェント）・`issue-implementer`／`issue-fixer`／`pr-reviewer` は Copilot の `.github/agents/` へ非移植。理由＝ gh CLI／Claude Code フック（`agent-command-gate.sh`）／Task 委譲／`bloom-model-tier`／`karte` CLI 等、Copilot に等価物がない依存を持つため（詳細＝`.claude/tailoring-registry.md`・`asset_parity/exceptions.py`）。`issue-pipeline` の運用そのものは上記スキル一覧のとおり Skill として移植済みで、専用 Agent 不在の分は利用可能な実行手段へ読み替える。
