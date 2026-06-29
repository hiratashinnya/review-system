# 資産テーラリング台帳（tailoring-registry）

> 資産の**汎用標準**と**プロジェクト・テーラリング済み版**の対応を管理する単一ソース。
> プロセスはスキル等で実現するため、**テーラリングの実体は `.claude/` 配下**に置く（docs ではない）。
> 関連：[asset-plan](../docs/methods/asset-plan.md)・[method-inventory A16](../docs/methods/method-inventory.md)・原則 [PR2](skills/spec-principles/SKILL.md)（機構/デフォルト）・[PR8](skills/spec-principles/SKILL.md)（消さず残す）。

## 配置ルール
| 区分 | 置き場 | auto-load | 役割 |
|---|---|---|---|
| 汎用標準（非活性） | `.claude/standards/<name>/SKILL.md` | されない | プロジェクト非依存の不変条件＋ノブ一覧。参照ベースライン |
| テーラリング済み（active） | `.claude/skills/<name>/SKILL.md` | される | ノブを埋めた本番運用版 |
| 台帳 | `.claude/tailoring-registry.md` | — | 標準⇄テーラリングの対応・実体パス・差分 |

## テーラリング手順（標準 → active）
1. 標準を棚卸し（不変条件は継承・ノブを洗い出す）。
2. **既存の active 汎用版があれば** `git mv .claude/skills/<n> .claude/standards/<n>`（非活性化・消さない＝PR8）。
   ※ 本PJのように標準を**新規 author** する場合は、標準を `standards/` に、テーラリング版を `skills/` に直接置く（extract-then-generalize）。
3. ノブを埋めた `SKILL.md` を `.claude/skills/<n>/` に置く（active）。
4. **本台帳に追記**（下表）。

## 台帳

| 資産 | 標準源 | 実体（active） | テーラリング内容（要点） | 由来PJ |
|---|---|---|---|---|
| test-strategy | `standards/test-strategy/SKILL.md` | `skills/test-strategy/SKILL.md` | 全 public 関数を unittest／非決定（LLM）は `FakePlatformAdapter`(record-replay) で決定化＝アダプタ境界＝テスト境界／e2e＝Claude Code エージェント×`io/cli` stdout 駆動／log＝stdout ダンプ(`tee`)／dirs＝`tests/{unit,designs,reports,logs}`／版＝TD版＋commit id＋雛形版＋基準content_hash(S6)／runner＝`python -m unittest`。**TD/TC/TR 対応**：ケース→TD(`tests/designs/` `TD-xxx`)・unittest→TC・成績書→TR(frontmatter: result/log_ref)（DD-009/DD-011 対応） | review-system |
| ~~doc-authoring~~ | なし（新規 author） | ~~`skills/doc-authoring/SKILL.md`~~ → **廃止＝工程別に畳み込み**（2026-06-10） | 横断 1 スキルを廃し、**ノードはそれを著作する工程スキルが規約を持つ**方式に統一（test-strategy が TD/TC/TR で先行）。新規スキルは作らず既存を拡張（A14 新規ゲート対象外）。割当：VAL/SR→align・ACTOR/I/O/P/E＋FR/SPEC/NFR→io-event-ledger・DM/TERM→domain-model・MOD/PORT/PRS/DS→architecture-design・ORC→orchestration-design・SCM/CFG→schema-design・PROMPT→prompt-design・TD/TC/TR→test-strategy。各スキルは**型・必須辺・要 RULE のみ**を持ち本文/RULE 全文は 07 へ集約（複製ドリフト防止）。横断スパイン（DD/Q/PEND/VERIFY/FND）は単一工程に属さず `docs/doc-system/07-authoring-guide.md`（プレーン MD）が第一参照。退避：`.claude/backups/2026-06-10/doc-authoring-SKILL.md` | review-system |
| ~~io-event-ledger~~ | `standards/io-event-ledger/SKILL.md`（非活性） | **廃止＝著作ルールを型別エージェントに移管**（2026-06-11） | 工程スキル方式（A14 拡張）も pull-once ロード＋コンテキスト圧縮による知識/実践分離問題を根本解決できないと判明。**型別著作エージェント（Policy B）に全面移行**。io-event-ledger の著作ルール（ACTOR/I/O/P/E/FR/SPEC/NFR）は `agents/` 配下の各エージェントに移譲済み。`git mv .claude/skills/io-event-ledger .claude/standards/io-event-ledger`（2026-06-11）で非活性化。 | review-system |
| requirements-author | なし（新規 author） | `agents/requirements-author.md` | VAL/SR/FR/NFR 著作エージェント。著作ルールと実行を同一コンテキストに同居させ、圧縮による知識欠落を構造的に防止。`tmp/<sprint>/<parent-id>.md` に出力。 | review-system |
| spec-author | なし（新規 author） | `agents/spec-author.md` | SPEC 著作エージェント。**1 SPEC = 1 検証アサーション**（1 condition ≠ 1 SPEC）を強制。-N 枝番（数字のみ）・decomposes 辺・`scheduled: ""`・`suppress: [RULE-015]` 禁止を組み込み済み。 | review-system |
| analysis-author | なし（新規 author） | `agents/analysis-author.md` | ACTOR/I/O/P/E 著作エージェント。P consumes I（I→P 禁止）・E の5要素必須を組み込み済み。 | review-system |
| design-author | なし（新規 author） | `agents/design-author.md` | ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT/TERM 著作エージェント。SCM→TERM は kind: see-also（refines 禁止）等を組み込み済み。 | review-system |
| verification-author | なし（新規 author） | `agents/verification-author.md` | TD/TC/TR/VERIFY/FND/DD/Q/PEND 著作エージェント。TD condition 一致（RULE-019）・TR result/log_ref を YAML メタに記述（RULE-020/021）・TC は kind: realizes（verifies 禁止）を組み込み済み。 | review-system |
| reconciliation-validator | なし（新規 author） | `agents/reconciliation-validator.md` | 検証エージェント（read-only）。`tmp/<sprint>/` の一時ファイルを surgical read（docidx）で検証し `VALIDATION_OK`（self_fix 指示付き）or `ROLLBACK` を返す。**Write/Edit を持たない＝構造的に本ファイルへ書けない fail-close**（DD-22）。自己修正は自分で適用せず指示として writer へ渡す。 | review-system |
| reconciliation | なし（新規 author） | `agents/reconciliation.md` | 調停（書込）エージェント。reconciliation-validator が `VALIDATION_OK` を返した後、`self_fix` 指示を適用し本ファイルへ確定書き込み＋tmp 掃除。**検証ロジックは持たない＝validator 専権**（二重実装ドリフト防止・DD-22）。責務分離：tmp 著作=*-author／検証=validator／本ファイル書込=reconciliation。 | review-system |

> その他の既存スキル（align・value-trace・mvp-scope・schema-design・domain-model・spec-pipeline・asset-pipeline・**asset-lateral-deploy**・**agy-delegate**・**bloom-model-tier**／
> **実装設計：architecture-design・orchestration-design・prompt-design・impl-design-pipeline**）と
> エージェント（spec-inspector・structured-analysis・asset-auditor・**agy-delegate**）は**未テーラリング＝汎用メソッドのまま active**。
> ※ 実装設計スキルは**汎用メソッド**（本PJ固有の選択＝ヘキサゴナル/内部git/stdout プロトコルは成果物 docs 側）。テーラリングが要る場合のみ本表へ起票する。
> ※ 思考支援スキル（align・architecture-design 等）は著作規約セクションを暫定で保持。型別エージェントへの完全移管は後続タスク。
> ※ `asset-lateral-deploy` は Issue #3 で新規追加（汎用メソッド・テーラリング対象外）。
> ※ `agy-delegate`（スキル＋エージェント）は外部 CLI 委譲ツール（汎用・テーラリング対象外）。agy MCP はローカル CLI／Windows Credential Manager 依存のため**クラウド/別プラットフォームへは非移植**。横展時は「環境依存・非移植」注記が要る。
> ※ `docidx`（スキル）＋ `docidx-lookup`（エージェント）はノード検索/読み込みツール（実体 `docidx/`・Python 標準ライブラリのみ・汎用・テーラリング対象外）。doc-system フォーマット仕様（SPEC/notation）に依存＝依存マップは `docidx/README.md`・各関数 `依存仕様:` docstring（フォーマット改版時に見直す）。
