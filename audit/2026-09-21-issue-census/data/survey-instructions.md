# Issue 全数調査の共通指示（batch 共通）

このリポジトリ（hiratashinnya/review-system）の GitHub Issue を**割り当てられた番号帯だけ**調査し、
リポジトリの長所・短所を分析するための**一次材料**を作る。分析・結論は呼び出し元（主文脈）が行う
ので、**あなたは事実の抽出と分類に徹する**。評価語（良い／悪い／改善すべき）は使わない。

## 調査対象

- `gh issue list --state all` で自分の番号帯に含まれる Issue を列挙する（open/closed 両方）。
- 各 Issue の本文を読む（`gh issue view <N>`）。コメントは、本文だけで分類できないときに限り読む。
- PR は対象外（Issue のみ）。ただし本文・コメントが PR 番号に言及していれば記録してよい。

## 各 Issue について抽出する項目

| 項目 | 取り方 |
|---|---|
| `number` / `state` / `title` | `gh issue list` の JSON |
| `labels` | `area:*` / `type:*` / `concern:*` |
| `author_kind` | 本文冒頭の attribution で判定。`Claude Code (AI) が起票しました` → `ai-claude`／`Codex AI agent` → `ai-codex`／それ以外・attribution 無し → `owner` |
| `origin` | 何をきっかけに起票されたか。`design`（設計・棚卸しで発見）／`review`（PR レビューの指摘から）／`post-merge`（merge 後に判明した欠陥）／`incident`（運用中の事故・実行時エラー）／`external`（外部ツール・API 変更）／`plan`（計画・トラッキング）／`unknown` |
| `root_cause_slug` | 原因を短い kebab-case で1つ（例 `gate-false-positive`・`contract-vs-mechanism-mismatch`・`spec-drift-between-copies`・`tooling-limitation`・`authority-conflation`）。同じ原因には同じ slug を使い、**バッチ内で語彙を一貫させる**。 |
| `resolution` | `implemented`（実装して close）／`duplicate`／`merged-into`（他 Issue へ統合）／`rejected`／`stale`（処置せず close）／`open` |
| `days_open` | 作成日〜クローズ日（open は作成日〜2026-09-21）の日数 |
| `spawned` | 本文・追記でこの Issue から派生したと明記される Issue 番号（あれば） |
| `recurrence_of` | 「同型の再発」「#N と同じ root cause」等と本文が述べている先行 Issue 番号（あれば） |
| `mechanized` | 処置が**機械検査・ゲート・テスト**の追加を伴ったか（`yes`/`no`/`partial`）。契約・散文のみなら `no` |

判定に迷ったら `unknown` を使い、推測で埋めない。**本文に書かれていないことを補完しない。**

## 成果物

1. **全件表**を `tmp/_analysis/batch-<範囲>.md` に Markdown テーブルで書く（1 Issue 1 行・上記の全項目）。
2. **チャットへ返す digest**（120 行以内・これが呼び出し元の分析材料になるので、ファイルパスだけ返すのは不可）:
   - 件数（open/closed 別）
   - `root_cause_slug` の頻度上位（件数つき・**全 slug の一覧も**付ける）
   - `origin` の分布（件数）
   - `author_kind` の分布（件数）
   - `resolution` の分布（件数）
   - `mechanized` の分布（件数）
   - **再発チェーン**：`recurrence_of` で繋がる連鎖を `#A → #B → #C` の形で全て列挙
   - **`post-merge` 起因の Issue 一覧**（番号とタイトル・1行要約）＝ レビューをすり抜けた欠陥
   - **長期 open**（`days_open` 60 日以上の open）の番号・日数・タイトル
   - **この番号帯で観測した特徴**（事実のみ・3〜6 行）

## 制約

- リポジトリのファイルを**変更しない**。書いてよいのは `tmp/_analysis/batch-*.md` だけ。
- `git` の状態を変えない（checkout・branch 操作をしない）。
- `gh` は読み取りのみ（`issue list` / `issue view`）。Issue の作成・編集・クローズをしない。
- 件数が多いので、本文全文をそのまま digest に貼らない。分類と1行要約に落とす。
