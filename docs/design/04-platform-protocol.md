# 設計 04 — PF 駆動プロトコル＋公開ツールのシグネチャ（凍結セット B）

> PF（LLM）は**外部アクタ**。境界は2つ：**System→PF**（`PlatformPort`＝LLM を問い合わせる穴）と **PF→System**（決定的ツールを公開し PF が呼ぶ）。
> [11 アダプタ方針](../requirements/11-platform-adapter.md) を実装シグネチャに固める。MVP は **PF 駆動（CLI＋stdout）**（[DD2](decisions.md#dd2--pf-駆動の-stdout-制御プロトコル形式)/[DD3](decisions.md#dd3--決定的ツールの公開トランスポート)）。
> 不変条件：**PF が返す出力も必ずシステムが検証**（[10 境界](../requirements/10-llm-system-boundary.md)・[13 S1](../requirements/13-stabilization.md)）。

## 1. System → PF：`PlatformPort`（LLM 呼び出し L1–L6）

`core` はこの抽象だけに依存する（[02](02-module-architecture.md)）。具体アダプタ（`ClaudeCodeAdapter` 等）が実装し、結線は合成ルート。

```python
# ports/platform.py
class PlatformPort(Protocol):
    def capabilities(self) -> "PlatformCapabilities": ...
    # L1 レビュー評価（中核）。戻りは生＝未検証（検証は core/triage）
    def review(self, req: "ReviewRequest", pack: CriteriaPack,
               targets: tuple[SourceFile, ...], references: tuple[SourceFile, ...],
               schema: "OutputSchema") -> "RawReviewResponse": ...
    # L2 本文矛盾（yes/no のみ・方向は判定しない）
    def judge_contradiction(self, a: RuleGuidance, b: RuleGuidance) -> "ContradictionVerdict": ...
    # L3 文書タイプ推定
    def estimate_type(self, features: "DocumentFeatures") -> TypeEstimation: ...
    # L4 衝突マージ草案（Q20 2段の1段目）
    def draft_merge(self, conflict: "FixConflict") -> "MergeDraft": ...
    # L5 観点FB草案 / L6 基準ひな形草案
    def draft_feedback(self, trend: "FeedbackTrend") -> "FeedbackDraft": ...
    def draft_scaffold(self, doc_type: DocumentType, neighbors: tuple[ComposedRule, ...]) -> "CriteriaDraft": ...
```

```python
@dataclass(frozen=True, slots=True)
class PlatformCapabilities:
    structured_output: bool      # MVP 必須（Q22）。false なら make_adapter が拒否
    file_apply: bool             # 無ければシステムが diff 適用（DS3）
    tool_execution: bool         # 無ければ決定的修正はシステムが formatter/linter 実行
    model_id: str
    platform_id: str
```

- **能力差はシステムが吸収**（[11](../requirements/11-platform-adapter.md) の表）：`file_apply`/`tool_execution` 無しは自前代替。**`structured_output` だけは必須**（[DD8](decisions.md#dd8--構造化出力の強制q22-グレーゾーン)・Q22）。
- アダプタ選択は registry ファクトリ `make_adapter(platform_id) -> PlatformPort`（[01 §6](01-class-design.md)）。階層は〔agentic PF → raw API → self-host〕で必要に応じ降りる（[11](../requirements/11-platform-adapter.md)）。

### L1 出力スキーマ（strict・[13 S1](../requirements/13-stabilization.md)）

```jsonc
// RawReviewResponse（アダプタが PF からこの形を得る。未適合は ❓未分類へ＝DD8）
{ "findings": [ { "rule_id": "naming-convention",
                  "location": { "file": "a.py", "line_range": [10, 12] },   // file 必須
                  "rationale": "…", "quote": "uc = 0",
                  "suggested_fix": { "description": "…", "diff": "…" } } ],
  "unmatched": [ { "description": "…", "location": { "file": "a.py" },
                   "suggested_fix": null } ] }
```

> `findings.length + unmatched.length` が PF の出した item 総数（**取りこぼしゼロの保存則**・S1）。`rule_id` 実在・`location.file` 必須はシステムが検証（[02 分解 P3.3/P4.1](../process/02-decomposition.md)）。

## 2. PF → System：公開ツール（決定的オペレーション）

[11](../requirements/11-platform-adapter.md) の公開ツール群を **CLI サブコマンド**として露出（[DD3](decisions.md#dd3--決定的ツールの公開トランスポート)）。各ツールは `core` の純関数を呼ぶ薄い殻で、**stdin=JSON / stdout=JSON**。

| ツール（CLI） | core 関数 | 入力→出力 | 段 |
|---|---|---|---|
| `tool compose-criteria` | `compose.compose(doc_type, scope)` | → `{pack, meta_index, warnings[]}` | P2 |
| `tool validate-findings` | `triage.validate(findings, pack)` | → `{valid[], unclassified[]}` | P4.1（⑤） |
| `tool exclude-reference` | `triage.exclude(findings, refs)` | → `{kept[]}` | P4.2 |
| `tool triage` | `triage.triage(findings, meta, policy)` | → `{auto[],approve[],judge[]}` | P4.3 |
| `tool apply-fix` | `apply.apply(exec_id, fixes)` | → `{commits[]}`（DS3） | P5.2 |
| `tool revert` | `apply.revert(target)` | → `{reverted[]}` | P5.4 |
| `tool run-deterministic-fix` | `apply.run_tool_fix(file)` | → `{diff}` | P5.1（Q21） |
| `tool warning-check` | `governance.check(hash)` | → `{seen: bool}` | P6.5 |
| `tool build-prompt` | `prompts.build(...)` | → `{prompt}` | P3.1 |
| `tool build-report` | `apply.build_report(...)` | → `{report}` | P5.3 |

> **順序ガード（[Q23](../dashboard.md)）**：`apply-fix` は**検証済みであること**を前提にする。MVP は stdout が順序を握る（下記）ので軽量、本番（System 駆動）は `apply-fix` が検証トークンを要求して機械強制（[11 注](../requirements/11-platform-adapter.md)）。

## 3. PF 駆動の stdout 制御プロトコル（[DD2](decisions.md#dd2--pf-駆動の-stdout-制御プロトコル形式)）

`reviewer run <paths>` 起動後、**システムが「次に何をするか」を stdout に行指向ディレクティブで流し**、Claude が従う。順序はシステムが握る（[11](../requirements/11-platform-adapter.md)）。診断は stderr（[DD9](decisions.md#dd9--ログ出力先)）。

| ディレクティブ | 意味 | Claude の行動 |
|---|---|---|
| `>>> STEP <name>` | これから行う段の宣言 | 文脈把握 |
| `>>> CALL <tool> <args>` | 決定的ツールを呼べ | 当該 CLI を実行し結果を待つ |
| `>>> THINK <prompt-ref>` | LLM 役の推論（評価/矛盾/草案） | プロンプトに従い JSON を返す |
| `>>> EXPECT <schema>` | 期待する戻り形式 | スキーマ準拠で応答 |
| `>>> WRITE <path>` | 応答をこのパスへ | 書き出す |
| `>>> DONE <exit>` | 完了 | 終了 |

**起動プロンプト（最小・[11](../requirements/11-platform-adapter.md)）**：「`reviewer run <paths>` を実行し、**以後 stdout の `>>>` 指示に従え**。`THINK` では観点に基づき違反を見つけ `rule_id` を付け原案を出す。仕分け・適用・revert は**ツール（CALL）に任せ自分でやらない**。」

```text
>>> STEP intake            # 例：1レビューの stdout（抜粋）
>>> CALL tool compose-criteria {"doc_type":"code","scope":"org"}
>>> STEP evaluate
>>> THINK review:3         # プロンプト雛形 review v3（07）
>>> EXPECT findings_schema  # L1 スキーマ（上記）
>>> CALL tool validate-findings {...}
>>> CALL tool triage {...}
>>> CALL tool apply-fix {"exec":"…","fixes":[…]}
>>> CALL tool build-report {...}
>>> DONE 0
```

## 4. 2つの運転モードと保証（[11](../requirements/11-platform-adapter.md)）

| モード | 駆動 | 「全 LLM 出力を検証」の担保 | 位置づけ |
|---|---|---|---|
| **PF 駆動** | `run`＝CLI＋stdout でシステムが手順指示・Claude が実行 | **順序を stdout で握る**（最終実行は agent・人も見る） | MVP・反復 |
| **System 駆動** | `review`＝システムが制御フロー保持 | **制御フローで強制**（必ず検証が走る） | 後・本番/ヘッドレス |

ツール（§2）と `PlatformPort`（§1）は**両モード共通**。作り直しは無い（[11](../requirements/11-platform-adapter.md)）。

## 5. 検証の不変条件（[10](../requirements/10-llm-system-boundary.md)）
- PF が返す `findings/unmatched` は**必ず** `validate-findings`（⑤）→ `exclude-reference` → `triage` を通る。PF に直接 `apply-fix` させない。
- `judge_contradiction` は **yes/no のみ**（方向＝厳しく/緩めは判定させない・[schema 2軸](../schema/README.md)）。
- 構造化出力が崩れたら **degrade して ❓未分類**（crash も silent-drop もしない・[DD8](decisions.md#dd8--構造化出力の強制q22-グレーゾーン)/S1）。
</content>
