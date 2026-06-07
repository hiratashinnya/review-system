# 設計 08 — ロギング／バージョニング規約（凍結セット D）

> 「なぜこの結果になったか」を**説明可能・再現可能**にする（[13 S6](../requirements/13-stabilization.md)）。
> チャネル分離は [DD9](decisions.md#dd9--ログ出力先)（stdout=制御・stderr=診断・`run.log`=実行ログ）。版は [DD6](decisions.md#dd6--executionid-の定義)/[DD7](decisions.md#dd7--プロンプト雛形のバージョニング)。
> 関連：[テスト戦略](../../.claude/skills/test-strategy/SKILL.md)（ログ＝stdout ダンプ・成績書に commit id）。

## 1. バージョニング（何を版で固定するか・`MAJOR.MINOR`）

**版の規約（[DD7](decisions.md)・オーナー指示）**：**MAJOR＝構造/型が変わる⇒対応ロジック（パーサ/ビルダー）の改修必須**、**MINOR＝内容/文言のみ⇒ロジック不変（見せたい差分）**。最低 `MAJOR.MINOR` を付ける。**MAJOR が処理ロジックの世代キー**＝版を見れば対応ロジックが一目で分かる。

| 対象 | 版の形 | 置き場 | MAJOR を上げる契機（＝ロジック改修） |
|---|---|---|---|
| 実行 | `ExecutionId`＝`executed_at-criteria_hash[:12]`（[DD6](decisions.md)） | レポート・commit・log | （識別子・版概念なし） |
| 基準フロントマター | `version: <MAJOR.MINOR>`（[schema](../schema/README.md)） | criteria/*.md | 対応サブセット文法/必須キーが変わる⇒自前パーサ改修 |
| 自動化ポリシー | `version: <MAJOR.MINOR>` | policy/*.yaml | matrix 構造が変わる⇒写像ロジック改修 |
| 合成結果 | `criteria_content_hash`＝hash(合成パック＋メタ) | 版スタンプ・DS2/DS4 キー | （ハッシュ・版概念なし） |
| プロンプト雛形 | `<id>:<MAJOR.MINOR>`（例 `review:3.1`・[DD7](decisions.md)） | prompts/templates | 出力スキーマの型/構造が変わる⇒[07 対応表](07-system-prompts.md)で世代切替 |
| PF/モデル | `platform_id` / `model_id`（[04 capabilities](04-platform-protocol.md)） | 版スタンプ | （外部識別子） |

> **版↔対応ロジックの一覧**は[07 §版管理](07-system-prompts.md)（プロンプト）と各パーサ（基準/ポリシー）が持つ。**未対応 MAJOR は実行前 fail-close**（[13 S5](../requirements/13-stabilization.md)）、MINOR 差は許容（情報のみ）。

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

## 4. 版定数はプログラム側に持つ（コメントでなく定数・[DD7](decisions.md)）

対応する版は**ソースの定数**として持つ（コメント不可）。理由＝`reviewer version`／`--help` がそれを読んで表示でき、lint も同じ定数で判定できる（単一ソース）。

```python
# parsing/frontmatter.py — 基準/ポリシーが読める MAJOR の集合（S5 lint がこれで判定）
SUPPORTED_CRITERIA_MAJOR: frozenset[int] = frozenset({1})   # 未対応 MAJOR は fail-close
SUPPORTED_POLICY_MAJOR:   frozenset[int] = frozenset({1})
# MINOR は情報のみ（処理は MAJOR で分岐）。version は "MAJOR.MINOR" 文字列で読む（整数化しない）

# prompts/registry.py — 各雛形の現行版（版スタンプ・version コマンドが読む）
TEMPLATE_VERSIONS: dict[str, str] = {
    "role": "1.0", "review": "3.1", "contradiction": "1.0",
    "type-estimate": "1.0", "merge": "1.0", "feedback-draft": "1.0", "scaffold": "1.0",
}
```

- `reviewer version`（[03](03-external-interfaces.md)）＝この2定数を表示。lint（S5）と版スタンプ（S6）も**同じ定数**を参照（DRY）。
- **MAJOR を上げる＝対応ハンドラ世代を上げる**ので、定数の更新と[07 対応表](07-system-prompts.md)・パーサ/ビルダーの改修は**同時**に行う（版↔ロジックを一目で追える）。

## 5. 影響範囲（他設計へ）
- [01 クラス設計](01-class-design.md)：`ExecutionId` 追加・`ProvenanceStamp`/`AppliedCommit` に `execution_id`（[DD6](decisions.md#dd6--executionid-の定義)）。
- [04](04-platform-protocol.md)：stdout は制御専用（診断は stderr）。
- [05](05-persistence.md)：`run.log` は実行ワークスペース配下。版定数は `parsing/`。
- [03](03-external-interfaces.md)：`reviewer version` が版定数を表示。
- 将来：雛形 MAJOR 改定で L2 判定が変わる場合、DS2 キャッシュキーに `judge_major` を足す（[07 版管理](07-system-prompts.md)）。
</content>
