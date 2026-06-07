# 設計 03 — 外部アクタ・インターフェース（凍結セット ②）

> 人間アクタ（**利用者 / レビュアー / 基準メンテナ**）とシステムの境界を**CLI のシグネチャ**として固める。PF（LLM）との境界は [04](04-platform-protocol.md)。
> 形式は [DD1](decisions.md#dd1--人間向けインターフェースの形)＝**単一 CLI `reviewer` ＋サブコマンド**。MVP はアクターを区別しない（[dashboard 決定](../dashboard.md)・単一ユーザー）が、**操作（口）は論理的に分けて**おく（将来 RBAC の土台）。
> 出典：[DFD L1](../process/01-dfd-level1.md)・[02 分解](../process/02-decomposition.md)・[05 I/O](../requirements/05-io-overview.md)・[01 クラス](01-class-design.md)。

## アクタ × 操作（レーン）

```mermaid
flowchart LR
  subgraph 利用者
    u1[提出してレビュー]
    u2[revert 要求]
  end
  subgraph レビュアー
    r1[✋ 承認→適用]
    r2[💬 決定→適用/却下]
    r3[判断・対象外フラグ]
  end
  subgraph 基準メンテナ
    m1[基準ひな形 生成]
    m2[警告/観点FB提案 受領]
    m3[基準編集（系外・非イベント）]
  end
  u1 --> CLI[(reviewer CLI)]
  u2 --> CLI
  r1 --> CLI
  r2 --> CLI
  r3 --> CLI
  m1 --> CLI
  CLI --> m2
  m3 -.->|エディタ/git で直接| DS1[(criteria/)]
```

> `m3 基準編集`は**系外＝非イベント**（[PR3](../methods/method-inventory.md)・[Q15](../dashboard.md)）。CLI の口にしない。検査は合成時に毎回（[04 lint](04-platform-protocol.md)/P2）。

## CLI サーフェス（サブコマンド一覧）

| アクタ | コマンド | 役割（DFD） | 入力 | 出力 / exit |
|---|---|---|---|---|
| 利用者 | `reviewer review <paths…>` | P1→P5 本線 | 対象パス・`--ref`・`--type`・`--scope` | **評価レポート(O-1・インタラクティブ HTML)** / 0 成功・3 fail-close(O-14)・4 lint 不正 |
| 利用者 | `reviewer revert <report> [--all]` | P5.4 | **レポートのパス**（revert チェック）or `--all` | revert 結果(O-6) / 0・2 対象なし |
| レビュアー | `reviewer approve <report>` | P5.2(✋・I-6) | **レポートのパスだけ**（✋ チェック状態） | 適用結果 / 0・3 衝突→人 |
| レビュアー | `reviewer decide <report>` | P5.2(💬・I-6) | **レポートのパスだけ**（💬 決定＋任意の修正欄） | 適用 or 記録 / 0 |
| レビュアー | `reviewer feedback <report>` | P6.1 | **レポートのパスだけ**（判断/対象外チェック） | DS5 追記 / 0 |
| メンテナ | `reviewer criteria feedback-draft [--rule <id>]` | P6.2（オンデマンド・[DD11](decisions.md#dd11--観点fb起草p62-のオンデマンド起動口)） | DS5 傾向（任意で rule 絞り） | O-12 観点FB提案 / 0 ・**MVP保留印** |
| メンテナ | `reviewer criteria lint [paths]` | S5 | 基準/ポリシーのパス（既定＝全件） | lint 結果（O-14 同形式）/ 0 健全・4 不正 |
| メンテナ | `reviewer criteria scaffold --type <t> --scope <s>` | P6.4 | doc_type・scope | 基準ひな形(O-11) / 0 |
| メンテナ | `reviewer warnings [--scope <s>]` | P6.5 表示 | scope フィルタ | 新規＋既知警告(O-9) / 0 |
| 共通 | `reviewer run <paths…>` | PF 駆動入口 | review と同じ | **stdout 制御プロトコル**（[04](04-platform-protocol.md)） |
| 共通 | `reviewer version` | 版表示 | — | 対応する基準/ポリシー MAJOR・プロンプト雛形版（**パーサ側の版定数を読む**・[DD7](decisions.md)/[08](08-logging-and-versioning.md)） |

> `review` は **System 駆動相当の一括実行**（人間/CI が直接叩く）。`run` は **PF 駆動**（Claude が stdout 指示に従う）。中身のツールは共通（[04 DD3](decisions.md#dd3--決定的ツールの公開トランスポート)）。

## シグネチャ（型は [01 クラス設計](01-class-design.md) のドメイン型）

口は CLI（文字列引数）だが、**境界の内側で即ドメイン型へ写像**し、以降生 `str` を流さない（[02 決め事](02-module-architecture.md)）。

```python
# io/cli.py（合成ルート。引数→ドメイン型→core→レンダリング）
from pathlib import Path

def cmd_review(paths: list[str], ref: list[str], type_: str | None, scope: str | None) -> int:
    request = ReviewRequest(                      # ← 文字列をここでドメイン型へ
        targets=tuple(normalize(Path(p)) for p in paths),     # DD13：pathlib.Path＋正規化
        references=tuple(normalize(Path(p)) for p in ref),    # 正規化は境界の1箇所だけ
        type_override=DocumentType(type_) if type_ else None,
        scope=parse_scope(scope),                 # 既定 Scope.org()
    )
    outcome: StageOutcome[ReviewReport] = pipeline.run_review(request, deps)  # core
    match outcome:
        case Success(report): write_html_report(report); return 0   # O-1（HTML・review_id 埋込）
        case Failure(notice): render_failure(notice); return EXIT_FAILCLOSE  # O-14
```

レビュアー系は **レポートのパスだけ**を取り、`review_id` と各 finding の入力を**レポート＋同梱 feedback.json から復元**（[DD10](decisions.md#dd10--承認決定fb-の入口オーナー指摘で全面改訂100件問題)/[DD14](decisions.md#dd14--html-レポートcli-の往復サーバ無し)）：

```python
def cmd_approve(report: Path) -> int: ...     # ✋ I-6：HTML から review_id→同梱 feedback.json の ✋ 選択を適用
def cmd_decide(report: Path) -> int: ...      # 💬 I-6：決定（approve/modify/reject/out_of_scope）＋任意修正欄を適用
def cmd_feedback(report: Path) -> int: ...    # DS5：判断/対象外チェックを記録
def cmd_revert(report: Path, all_: bool = False) -> int: ...   # P5.4 / O-6（revert チェック or --all）
def cmd_criteria_lint(paths: tuple[Path, ...]) -> int: ...     # S5（CriteriaLintResult → O-14 形式）
def cmd_criteria_scaffold(doc_type: DocumentType, scope: Scope) -> int: ...  # O-11
def cmd_warnings(scope: Scope | None) -> int: ...          # O-9（DS4）
def cmd_version() -> int: ...                  # 対応版定数を表示（parsing.SUPPORTED_*・prompts.TEMPLATE_VERSIONS）
```

> **`ReviewRequest` は新規のポート入力型**（[01 §9](01-class-design.md)）。`parse_scope` は `org|team:x|project:x` を `Scope` へ（[01 §3](01-class-design.md)）。
> `normalize(Path)`＝リポジトリ相対 POSIX へ正規化（[DD13](decisions.md#dd13--自前-filepath-クラスの要否オーナー指摘)）。突合（参照除外・`location.file`）はこの正規化済み Path で行う。

## 終了コードと O-14（[13 S3](../requirements/13-stabilization.md) fail-close）

| code | 意味 | 例 |
|---|---|---|
| 0 | 成功（空文書 no-op 含む＝良性 fail-open） | レポート出力・0件レポート |
| 2 | 要求不正（対象なし・revert 対象なし） | 引数ミス |
| 3 | fail-close（O-14） | 基準パース失敗・LLM 障害・スコープ未解決 |
| 4 | lint 不正（S5） | `override` 不正値・extends 切れ |

- どの異常も**黙って空を返さない**：`FailureNotice{stage+reason+subject+next_action}`（O-14）を**stderr へ可読出力**し、上の code を返す（[DD9](decisions.md#dd9--ログ出力先)）。

## レポート駆動のフィードバック（HTML・[DD10](decisions.md#dd10--承認決定fb-の入口オーナー指摘で全面改訂100件問題)/[DD14](decisions.md#dd14--html-レポートcli-の往復サーバ無し)）

**100件問題への解**：id を CLI に打たせない。レビューとレポートは **1:1** なので、レポート自体を入力面にする。

```
reviewer review …  ─▶  report.html（O-1）          ┐ review_id=<ExecutionId> を埋込
                        ├ finding 毎にチェックボックス（承認/却下/対象外/決定）＋💬修正欄
                        └ 「書き出す」ボタン(JS) ─▶ <review_id>.feedback.json をDL
                                                       │
レビュアーがブラウザで選ぶ ──────────────────────────┘
                                                       ▼
reviewer feedback|decide|approve  report.html   ─▶  HTML から review_id を読み
                                                     同梱 <review_id>.feedback.json を解決し一括適用
```

- **review_id（=`ExecutionId`）はレポートに埋込**（表示は任意）。**DS3 適用フォルダ `.review-workspace/<review_id>/` にも同 id**（[05](05-persistence.md)・既に exec_id キー）＝レポートと適用先が同 id で対応。
- コマンドの**引数はレポートのパスだけ**。対象 finding 群はレポート＋feedback.json から復元（id 入力ゼロ）。
- UI はブラウザに委譲（チェックボックス/フォーム）。系は **HTML＋クライアント JS を生成するだけ**（サーバレス・stdlib）。
- ✋衝突（同一 location）は従来どおり適用時に解決（[05 DS3](05-persistence.md)）。一括適用でも finding 単位コミットは不変（[S4](../requirements/13-stabilization.md)）。

## 入力台帳との対応（[05 I/O](../requirements/05-io-overview.md) の正準番号に整合）

> ⚠️ 番号は[05 台帳](../requirements/05-io-overview.md)が正準。**参照＝I-13**（I-3 は scope）・**scope＝I-3**（I-5 はポリシー）・**判断/対象外＝I-6/I-7**・**revert＝I-14**（[04-gaps](../process/04-gaps-found.md) で台帳化）。`I-10/I-11` は使わない（I-10＝通知条件・post-MVP、I-11＝削除済み）。

| 操作 | I-#（[05](../requirements/05-io-overview.md)） | O-# |
|---|---|---|
| `review` | I-1 対象・I-13 参照・I-2 型上書き＋I-15 推定・I-3 scope（MVP=org）・I-4/I-5 基準/ポリシー | O-1 レポート・O-2 指摘・O-14 |
| `approve`/`decide` | I-6 指摘への判断（承認/修正/却下） | O-3 適用・O-4 diff・O-5 原案 |
| `revert` | I-14 revert 要求 | O-6 |
| `feedback` | I-6 判断 ＋ I-7 対象外フラグ | — (DS5) |
| `criteria feedback-draft` | （DS5 起点・オンデマンド・[DD11](decisions.md#dd11--観点fb起草p62-のオンデマンド起動口) MVP保留印） | O-12 観点FB提案 |
| `criteria scaffold` | （入力番号なし＝**イベント E8** 起点・doc_type/scope は引数） | O-11 |
| `warnings` | — | O-9 |

> **post-MVP・未結線**（[PR8](../methods/method-inventory.md) フル論理＋MVP印）：I-10 通知条件設定・I-12 時間トリガは MVP では CLI に口を持たない（[05 ③](../requirements/05-io-overview.md)）。
</content>
