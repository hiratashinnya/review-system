# 設計 08 — ロギング／バージョニング規約（凍結セット D）

> 「なぜこの結果になったか」を**説明可能・再現可能**にする（[13 S6](../requirements/13-stabilization.md)）。
> チャネル分離は [DD9](decisions.md#dd9--ログ出力先)（stdout=制御・stderr=診断・`run.log`=実行ログ）。版は [DD6](decisions.md#dd6--executionid-の定義)/[DD7](decisions.md#dd7--プロンプト雛形のバージョニング)。
> 関連：[テスト戦略](../../.claude/skills/test-strategy/SKILL.md)（ログ＝stdout ダンプ・成績書に commit id）。

## 1. バージョニング（何を版で固定するか）

| 対象 | 版の形 | 置き場 | 用途 |
|---|---|---|---|
| 実行 | `ExecutionId`＝`executed_at-criteria_hash[:12]`（[DD6](decisions.md#dd6--executionid-の定義)） | レポート・commit・log | revert/ログ/版スタンプの串刺しキー |
| 基準スキーマ | `version: <int>`（フロントマター・[schema](../schema/README.md)） | criteria/*.md | 文法/内容の世代 |
| 合成結果 | `criteria_content_hash`＝hash(合成パック＋メタ) | 版スタンプ・DS2/DS4 キー | どの基準で評価したか |
| プロンプト雛形 | `<id>:<int>`（例 `review:3`・[DD7](decisions.md#dd7--プロンプト雛形のバージョニング)） | prompts/templates | どの雛形で評価したか |
| PF/モデル | `platform_id` / `model_id`（[04 capabilities](04-platform-protocol.md)） | 版スタンプ | どの PF/モデルか |

### 版スタンプ（O-1 に必須・[01 ProvenanceStamp](01-class-design.md) に `execution_id` 追加）

```python
@dataclass(frozen=True, slots=True)
class ProvenanceStamp:                 # S6
    execution_id: ExecutionId          # ← DD6 で追加
    platform_id: str
    model_id: str
    prompt_template_version: str       # 主＝"review:3"
    criteria_content_hash: ContentHash
    executed_at: str                   # ISO8601
```

> **冗長は意図的（非正規化）**：`execution_id = executed_at + criteria_hash[:12]`（[DD6](decisions.md#dd6--executionid-の定義)）なので `executed_at`/`criteria_content_hash` は理論上 execution_id から辿れる。だが版スタンプは**人が直接読む再現性の証跡**なので、導出を強いず**フル値を併記**する（状態ではなく可読性のための非正規化）。`criteria_content_hash` は DS2/DS4 キーと**同じ語彙**で照合に使うため独立フィールドとして保持。
- 各 finding/ルールは **provenance（由来ファイルパス・継承段）**（[01 Provenance](01-class-design.md)・[Q10](../dashboard.md)）。3段継承で衝突/差分の由来段を示す（[schema](../schema/README.md)）。
- **受け入れ基準**（[13 S6](../requirements/13-stabilization.md)）：同一入力×同一版の再実行で、版スタンプから「どの基準・どの PF/モデル・どの雛形」を追える。

## 2. ロギング（3チャネル分離・[DD9](decisions.md#dd9--ログ出力先)）

| チャネル | 内容 | 形式 | 理由 |
|---|---|---|---|
| **stdout** | PF 駆動の制御プロトコル（`>>> …`・[04](04-platform-protocol.md)） | 行指向ディレクティブ | Claude が追従。混線回避で**ここに診断を出さない** |
| **stderr** | 診断ログ（段の開始/終了・警告・例外） | `logging`（stdlib）構造化行 | 人/CI が見る。stdout を汚さない |
| **`run.log`** | 実行単位の永続ログ（`.review-workspace/<exec_id>/run.log`） | stderr と同形式を tee | 後追い調査・テスト成績書からリンク |

```
# stderr / run.log の1行（exec_id で串刺し）
2026-06-07T12:00:01Z  exec=2026...-9af3  stage=compose  level=INFO  msg="composed 7 rules" criteria_hash=9af3…
2026-06-07T12:00:03Z  exec=2026...-9af3  stage=evaluate level=WARN  msg="2 items degraded to unclassified"
2026-06-07T12:00:04Z  exec=2026...-9af3  stage=apply    level=INFO  msg="commit finding=naming-convention@a.py:10"
```

- **段の境界を必ずログ**（intake/compose/evaluate/validate/triage/apply/report）＝[06 オーケストレーション](06-orchestration.md)の `StageOutcome` 遷移を可視化。
- **fail-close（O-14）は WARN/ERROR で stderr＋run.log に**、かつ利用者向けに整形（[03 終了コード](03-external-interfaces.md)）。**黙って空にしない**（[13 S3](../requirements/13-stabilization.md)）。
- **DS3 のコミットメッセージ**＝`<exec_id> <finding_id>`（[05](05-persistence.md)）＝git 履歴がそのまま適用ログ。

## 3. テスト戦略との接続（[/test-strategy](../../.claude/skills/test-strategy/SKILL.md)）

- テストの「ログ＝標準出力ダンプ」は `python -m unittest -v 2>&1 | tee tests/logs/<id>-<commit>.txt`＝**stdout＋stderr 両方**を捕捉（[DD9](decisions.md#dd9--ログ出力先)）。
- テスト成績書ヘッダの版＝本書の版群：`{ ケース版 + 実装commit id + prompt_template_version + criteria_content_hash + executed_at }`。S6 の版スタンプとテスト証跡が**同じ語彙**で揃う。

## 4. 影響範囲（他設計へ）
- [01 クラス設計](01-class-design.md)：`ExecutionId` 追加・`ProvenanceStamp`/`AppliedCommit` に `execution_id`（[DD6](decisions.md#dd6--executionid-の定義)）。
- [04](04-platform-protocol.md)：stdout は制御専用（診断は stderr）。
- [05](05-persistence.md)：`run.log` は実行ワークスペース配下。
- 将来：雛形改定で L2 判定が変わる場合、DS2 キャッシュキーに `judge_version` を足す余地（[07 版管理](07-system-prompts.md) のメモ）。
</content>
