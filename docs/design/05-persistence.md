# 設計 05 — 永続層（DS1–DS5）と内部 git ワークスペース（凍結セット C）

> 状態（[03 状態インベントリ](../process/03-state-inventory.md)）を**リポジトリ port の裏**に隔離する（[02](02-module-architecture.md)）。`core` は port だけを見る。
> 形式は stdlib のみ（[Q5](../dashboard.md)）：[DD4](decisions.md#dd4--ds2ds4ds5-の保存形式) JSONL/JSON・[DD5](decisions.md#dd5--ds3-内部-git-ワークスペースの実体) git subprocess。
> [13 S4](../requirements/13-stabilization.md)（トランザクション）・[S5](../requirements/13-stabilization.md)（lint）・[S6](../requirements/13-stabilization.md)（版）の実体。

## state ディレクトリ配置

```
criteria/                       # DS1（人が編集・git 管理・系外）
  org/code.md  policy/org.yaml  …          ([schema](../schema/README.md) のツリー)
.review-state/                  # システムが書く永続（リポジトリにコミット）
  contradiction-cache.json      # DS2
  warning-ledger.jsonl          # DS4（append-only）
  feedback.jsonl                # DS5（append-only）
.review-workspace/              # DS3（実行ごと・git）
  <exec_id>/  .git/  <対象の作業コピー>  run.log
```

## リポジトリ port（[01 §9](01-class-design.md) のポート契約）

```python
# ports/repositories.py
class CriteriaRepository(Protocol):       # DS1
    def discover(self, doc_type: DocumentType, scope: Scope) -> tuple["CriteriaFile", ...]: ...
    def load_policy(self, scope: Scope) -> "PolicyMatrix": ...
class ContradictionCache(Protocol):       # DS2
    def get(self, key: ContentHash) -> "ContradictionVerdict | None": ...
    def put(self, key: ContentHash, verdict: "ContradictionVerdict") -> None: ...
class WorkspaceRepository(Protocol):      # DS3
    def open(self, exec_id: ExecutionId, targets: tuple[SourceFile, ...]) -> None: ...
    def commit_fix(self, fix: ResolvedFix) -> AppliedCommit: ...
    def rollback_execution(self, exec_id: ExecutionId) -> None: ...   # S4 書込ゼロ
    def revert(self, target: RevertTarget) -> tuple[AppliedCommit, ...]: ...   # O-6
class WarningLedger(Protocol):            # DS4
    def seen(self, rule_id: RuleId, h: ContentHash) -> bool: ...
    def record(self, entry: WarningLedgerEntry) -> None: ...
class FeedbackStore(Protocol):            # DS5
    def append(self, fb: Feedback) -> None: ...
    def trend(self, rule_id: RuleId) -> "FeedbackTrend": ...
```

## DS1 基準/ポリシーファイル（filesystem・read-only 系外編集）

- `discover` は `criteria/org → teams/<t> → projects/<p>` の同 `doc_type` を集め、**自前パーサ**（`parsing/frontmatter.py`＝[S5 検証器](../requirements/13-stabilization.md)）で `CriteriaFile{frontmatter, rules[], body}` に読む。
- 合成（継承マージ・方向ゲート・本文矛盾）は `core/compose`。**毎回合成**（[Q15](../dashboard.md)・安価）。本文矛盾(LLM)だけ DS2 でキャッシュ。
- 編集は**系外＝非イベント**（[PR3](../methods/method-inventory.md)）。システムは書かない。lint は `criteria lint`／合成時に毎回（[04](04-platform-protocol.md)）。
- `version` は `"MAJOR.MINOR"` 文字列で読み、**MAJOR が `parsing.SUPPORTED_CRITERIA_MAJOR`（定数・[08 §4](08-logging-and-versioning.md)）に無ければ S5 fail-close**。MINOR は情報のみ。

## DS2 矛盾チェックキャッシュ（JSON・[DD4](decisions.md#dd4--ds2ds4ds5-の保存形式)）

- キー＝`content_hash = hash(対象ルールのメタ＋本文)`（[schema](../schema/README.md)）。値＝`{verdict: contradictory|consistent, decided_at}`。
- ヒット→流用、ミス→PF(L2)判定→追記（[02 P2.2](../process/02-decomposition.md)）。`hashlib.sha256`（stdlib）。
- メタ/本文が変われば hash が変わり**自動的に再判定**（古い項は残置＝無害・PR8）。

## DS3 finding-commit ワークスペース（内部 git・[DD5](decisions.md#dd5--ds3-内部-git-ワークスペースの実体)）

**[13 S4](../requirements/13-stabilization.md) を git の枯れた機構で満たす**（自前差分スタックを書かない）。

```python
class GitWorkspaceRepository:
    def open(self, exec_id, targets):
        # .review-workspace/<exec_id>/ に対象を複製 → git init → git add -A → 初期コミット（基準点）
    def commit_fix(self, fix) -> AppliedCommit:
        # diff 適用 → git add <file> → git commit -m "<exec_id> <finding_id>"（finding 単位・Q3）
        # commit_ref と finding_id を AppliedCommit で返す
    def rollback_execution(self, exec_id):
        # 実行内のどこかで失敗 → git reset --hard <基準点>（適用済みも含め書込ゼロ＝all-or-nothing）
    def revert(self, target):
        # finding: 当該 commit を git revert / exec: その実行の全 commit を revert / all: 基準点へ
```

| S4 受け入れ基準 | 実装 |
|---|---|
| 途中1件失敗→書込が残らない | `try: 各 commit_fix / except: rollback_execution`（`git reset --hard`） |
| 任意 finding を revert→当該だけ戻る | `git revert <finding の commit>` |
| 実行 ID 一括 revert | その実行の全 finding コミットを revert |

- **衝突**（同一 location）は適用前に `core/apply` が解決（[Q20](../dashboard.md) 2段：LLM マージ→不可は人）してから `commit_fix`（[02 P5.2](../process/02-decomposition.md)）。
- 前提：**git バイナリ存在**（[DD5](decisions.md#dd5--ds3-内部-git-ワークスペースの実体) で明示）。`subprocess` 駆動・外部 Python 依存なし。

## DS4 警告レジャー（JSONL append-only・[schema](../schema/README.md#警告の既出判定warning-ledger)）

- 1行＝`{rule_id, content_hash, first_seen}`。`seen` は同 `rule_id×content_hash` の有無で**既出判定**。
- 既出→**警告しない**（レポートに「既知」として混ぜるだけ）。未出→発行＋追記（[02 P6.5](../process/02-decomposition.md)）。
- **状態を持つ理由**＝「一度示せば足りる人間の判断待ち」はノイズ抑制が要る（[schema](../schema/README.md)）。レビュー指摘（無状態）と逆（[PR5](../methods/method-inventory.md)）。

## DS5 フィードバック蓄積（JSONL append-only・MVP 最小）

- 1行＝`{finding_id, decision(approve|reject|out_of_scope), recorded_at}`（[01](01-class-design.md) `Feedback`）。
- `trend(rule_id)` ＝ rule_id 別の却下/対象外率を集計（P6.2 観点FB起草の素材）。MVP は蓄積＋集計のみ、自動起票はしない。

## ExecutionId（[DD6](decisions.md#dd6--executionid-の定義)・[01 クラス設計](01-class-design.md)へ追加）

```python
@dataclass(frozen=True, slots=True)
class ExecutionId:
    """1レビュー実行の識別子。版スタンプ(S6)と同素材で再現性に直結。"""
    value: str
    @classmethod
    def of(cls, executed_at: str, criteria_hash: ContentHash) -> "ExecutionId":
        return cls(f"{executed_at}-{criteria_hash.value[:12]}")
```

> **[01 クラス設計](01-class-design.md) への影響**：`ExecutionId` 型を新規追加し、`ProvenanceStamp` と `AppliedCommit` に `execution_id` を持たせる（[08](08-logging-and-versioning.md)）。`RevertTarget = FindingId | ExecutionId | All` の穴埋め。

## 永続の不変条件
- **読み出し1件は frozen**（[01 §4](01-class-design.md)）。`list`/`dict` は repo 層に隔離。
- **追記専用（DS4/DS5）は上書き禁止**（PR8）。DS2 は再計算可能な導出キャッシュ（消えても再生成）。
- **DS3 以外はリポジトリにコミット**して再現可能に。`.review-workspace/` は実行産物（gitignore 可・revert 期間中のみ保持）。
