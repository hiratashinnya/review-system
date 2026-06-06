# 資産化プラン — メソッドをスキル/エージェントにする計画・提案

> [method-inventory.md](method-inventory.md) で棚卸した A1–A13 ＋原則 PR1–10 を、**Claude Code のスキル/サブエージェント**として再利用可能にする提案。
> これらは review-system 専用ではなく、**今後どんな仕様策定でも使える横断資産**を想定。

## 1. スキルか？エージェントか？（振り分けの判断基準）

| 形式 | 使う場面 | 特徴 |
|---|---|---|
| **スキル**（`/name`・SKILL.md） | メインスレッドが**その場で従う手順・チェックリスト**。ユーザーとの対話・判断が要る、比較的短い手続き | 手順書を注入して実行。状態は会話に残る |
| **サブエージェント**（agent 定義） | **大きい・ファンアウト・ほぼ自走**して結論だけ返す仕事。読み込み量が多くコンテキストを隔離したい | 別コンテキストで走り、結論を返す。点検/分解の重い処理向き |
| **共有リファレンス**（`_shared/principles.md`） | 全スキル/エージェントが参照する**決めた基準**（PR1–10） | 単独実行しない。各定義が冒頭で読み込む |

判断則：**対話と判断が中心 → スキル**／**読み込み・分解・点検が中心で自走 → エージェント**。

## 2. 振り分け案（A# → 資産）

| A# 活動 | 資産 | 形式 | 名前（案） | 優先 |
|---|---|---|---|---|
| 原則 PR1–10 | 共有リファレンス | `_shared/principles.md` | — | **1** |
| A6 カバレッジ点検 ＋ A10 入出力点検 ＋ A11 漏れ/矛盾ハント | 点検ループ | **エージェント** | `spec-inspector` | **1** |
| A7 構造化分析 ＋ A8 状態インベントリ | DFD 分解 | **エージェント** | `structured-analysis` | **2** |
| A9 価値経路トレース | レベリング点検 | スキル | `/value-trace` | 2 |
| A12 価値ベース MVP スコープ | 価値分析 | スキル | `/mvp-scope` | 2 |
| A4 I/O 台帳 ＋ A5 イベントリスト | 台帳起こし | スキル | `/io-event-ledger` | 3 |
| A1 認識合わせ | 段取り | スキル | `/align` | 3 |
| A13 スキーマ設計 | スキーマ起こし | スキル | `/schema-design` | 3 |
| A2 ダッシュボード運用 / A3 案出し | 作業流儀 | （CLAUDE.md の作業規約に記述） | — | 3 |
| A1→A12 全体 | パイプライン | スキル（オーケストレータ） | `/spec-pipeline` | 4 |

> `spec-inspector` と `structured-analysis` を**エージェント**にする理由：複数ファイルを横断的に読み・分解し、結論（gap 一覧 / DFD 一式）を返す自走型で、メインの会話文脈を汚さない方が効く（[method-inventory](method-inventory.md) の依存図でも A10/A11 が反復ループの核）。

## 3. ディレクトリ構成（案）

```
.claude/
  skills/
    _shared/principles.md      # PR1–10。各 SKILL.md が冒頭で参照
    align/SKILL.md             # A1
    io-event-ledger/SKILL.md   # A4+A5
    value-trace/SKILL.md       # A9
    mvp-scope/SKILL.md         # A12
    schema-design/SKILL.md     # A13
    spec-pipeline/SKILL.md     # A1→A12 オーケストレータ（他を順に呼ぶ）
  agents/
    spec-inspector.md          # A6+A10+A11（点検→gap 一覧を返す）
    structured-analysis.md     # A7+A8（コンテキスト→DFD→単一責務→状態）
CLAUDE.md                      # A2/A3 の作業流儀＋「迷ったら principles を見る」
```

- **最初は project 直下（`.claude/`）に置き repo にコミット**。安定したら user 級（`~/.claude/`）へ昇格して全プロジェクトで共有。
- 各 SKILL.md / agent は **対応する A# カードへ逆リンク**（[method-inventory](method-inventory.md)）し、原則は `_shared/principles.md` を単一ソースにする（DRY）。

## 4. 各資産の中身テンプレ

**SKILL.md**（例：`/io-inspect` 相当を io-event-ledger に内包）
```
---
name: <名前>
description: いつ使うか（トリガを具体的に）
---
## 参照
- 原則：_shared/principles.md（PR1, PR6 …）
## 手順
1. … 2. …（method-inventory の A# の手順をそのまま）
## 判断基準
- …（A# の判断基準）
## 点検観点（done の条件）
- …（A# の点検観点）
## 成果物テンプレ
- 表/図のひな形
```

**agent 定義**（例：`spec-inspector`）
```
---
name: spec-inspector
description: 台帳/イベント/設計を横断点検し gap 一覧(G#)を返す。矛盾は停止して報告。
tools: Read, Grep, Glob   # 読み取り中心。書き込みはしない
---
（system prompt に PR1–10 と A6/A10/A11 の手順・点検観点を埋め込む。
 出力＝gap 表 ＋ 矛盾があれば「停止・要確認」マーカー）
```

## 5. 着手順の提案（資産化フェーズ）

1. **`_shared/principles.md`**（PR1–10 を移植）＋ **`spec-inspector` エージェント** … いま最も繰り返し使う点検ループを先に固める。
2. **`structured-analysis` エージェント** … 最も重く独自性の高い手法を再現可能に。
3. **`/value-trace`・`/mvp-scope`** スキル … 設計後半の価値点検を軽量化。
4. **`/io-event-ledger`・`/align`・`/schema-design`** スキル … 前半の起こし作業。
5. **`/spec-pipeline`**（オーケストレータ）＋ **CLAUDE.md の作業規約** … 全体を1コマンドで回せるように。

## 6. ユーザーに確認したい点

- 置き場所：**まず project `.claude/`（推奨）**でよいか、最初から user 級にするか。
- スコープ：この review-system に閉じた例で作るか、**汎用（プロジェクト非依存）**として抽象化するか（推奨：汎用）。
- 最初に作る範囲：**フェーズ1（principles ＋ spec-inspector）**から始めてよいか。

> 合意が取れたら、この計画の「フェーズ1」から実体（SKILL.md / agent 定義）を作成する。
