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
| ~~io-event-ledger~~ | — | ~~`skills/io-event-ledger/SKILL.md`~~ → **`standards/io-event-ledger/SKILL.md`** に非活性化（2026-06-11） | 工程スキルへの著作規約畳み込みをさらに**型別サブエージェント**方式へ刷新（Policy B）。スキル（コンテキスト圧縮による知識流出）→エージェント（知識＋実行を同一コンテキストに同居）に移行。`git mv` で standards/ へ退避。後継：`agents/requirements-author`・`agents/spec-author`・`agents/analysis-author`（下行参照） | review-system |
| requirements-author | なし（新規 agent） | `agents/requirements-author.md` | VAL/SR/FR/NFR 著作エージェント。旧 io-event-ledger の VAL/SR/FR/NFR 規約＋ align の著作ルールを継承。tmp/<sprint>/<parent-id>.md に出力 | review-system |
| spec-author | なし（新規 agent） | `agents/spec-author.md` | SPEC 著作エージェント。**1アサーション1ノード**（≠1condition）・**-N枝番**（英字禁止）・decomposes 辺を強制。旧 io-event-ledger の SPEC 規約を大幅修正して継承。tmp/<sprint>/<parent-id>.md に出力 | review-system |
| analysis-author | なし（新規 agent） | `agents/analysis-author.md` | ACTOR/I/O/P/E 著作エージェント。P consumes I（I→P 方向禁止）・E の5要素必須を強制。tmp/<sprint>/<parent-id>.md に出力 | review-system |
| design-author | なし（新規 agent） | `agents/design-author.md` | ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT/TERM 著作エージェント。各設計スキルの著作規約を集約。SCM→TERM は see-also 強制。tmp/<sprint>/<parent-id>.md に出力 | review-system |
| verification-author | なし（新規 agent） | `agents/verification-author.md` | TD/TC/TR/VERIFY/FND/DD/Q/PEND 著作エージェント。TD condition = verifies 先 SPEC condition（RULE-019）・TR result/log_ref は YAML メタ（RULE-020/021）を強制。tmp/<sprint>/<parent-id>.md に出力 | review-system |
| reconciliation | なし（新規 agent） | `agents/reconciliation.md` | 調停エージェント。各著作エージェントの tmp 出力を検証し、整合が取れたら本ファイルへ確定書き込み。自己修正可（ref_version 不一致等）と差し戻し（ROLLBACK）を分離。レイヤー完了ごとに呼び出す | review-system |

> その他の既存スキル（align・value-trace・mvp-scope・schema-design・domain-model・spec-pipeline・asset-pipeline／
> **実装設計：architecture-design・orchestration-design・prompt-design・impl-design-pipeline**）と
> エージェント（spec-inspector・structured-analysis・asset-auditor）は**未テーラリング＝汎用メソッドのまま active**。
> ※ 実装設計スキルは**汎用メソッド**（本PJ固有の選択＝ヘキサゴナル/内部git/stdout プロトコルは成果物 docs 側）。テーラリングが要る場合のみ本表へ起票する。
> ※ 思考支援スキル（align・architecture-design 等）は著作規約セクションを暫定で保持。型別エージェントへの完全移管は後続タスク。
</content>
