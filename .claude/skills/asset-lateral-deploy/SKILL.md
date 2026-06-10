---
name: asset-lateral-deploy
description: 資産の横展方法確立。.claude 配下の資産を棚卸しし、ターゲットプラットフォーム（GitHub Copilot 等）向けにフォーマット変換してPRを作成する。スラッシュコマンド一発で一気通貫実行。
disable-model-invocation: true
---

# 資産の横展方法確立（asset-lateral-deploy）

## 概要

`.claude/` 配下の**スキル・エージェント**を、GitHub Copilot など別プラットフォームで利用可能にする。3フェーズを順に回す。

**MVP スコープ**: `.claude/skills/*/SKILL.md` と `.claude/agents/*.md` のみ変換・出力。標準ベースライン（`.claude/standards/`）は棚卸し対象だが変換は将来対応（スタブで出力スキップ）。

---

## フェーズ 1: 棚卸し（Inventory）

1. **前提確認**
   - リポジトリルート直下に `.claude/skills/`, `.claude/agents/` が存在すること
   - `.claude/standards/` は存在すれば棚卸し対象（optional）
   - 変換対象の frontmatter 属性（`name`, `description`, `user-invocable`, `disable-model-invocation`）が正しく記述されていること

2. **`asset-auditor` 呼び出し**（オプション）
   - `.claude/` を走査して全資産を台帳化（`name | 種別 | 責務 | 変換可否判定`）
   - 矛盾・重複を検出し、変換リスクを事前通知

**チェックポイント**: `asset-auditor` の出力で警告がないこと

---

## フェーズ 2: フォーマット変換（Format Conversion）

1. **Dry-run でプレビュー**
   ```bash
   python scripts/lateral_deploy.py --target copilot --dry-run
   ```
   - 出力ファイルパス・内容を全てコンソール表示
   - `.github/` ディレクトリへの書き込みは行わない

2. **変換ルール確認**

   | 変換元 | 変換先 | 条件 |
   |---|---|---|
   | `skills/*/SKILL.md` | `.github/prompts/<name>.prompt.md` | `user-invocable: true` または未指定 |
   | `agents/*.md` | `.github/instructions/<name>.instructions.md` | エージェント定義全般 |
   | `skills/spec-principles/SKILL.md` | `.github/copilot-instructions.md` に展開 | `user-invocable: false`、PR1–PR10 をインライン化 |
   | オーケストレータ（`disable-model-invocation: true`） | `.github/instructions/<name>.instructions.md` | orchestrator 型スキル |

3. **出力形式**
   - **Prompt** (`.github/prompts/<name>.prompt.md`): YAML frontmatter + Markdown body（SKILL.md をそのまま）
   - **Instructions** (`.github/instructions/<name>.instructions.md`): HTML comment で tools/model 記載 + body
   - **Copilot Instructions** (`.github/copilot-instructions.md`): PR1–PR10 + スキル一覧表

**チェックポイント**: dry-run の出力で、スキップ対象（`user-invocable: false`）の判定が正確であること

---

## フェーズ 3: PR 作成（PR Creation）

1. **ファイル書き込み + ブランチ作成**
   ```bash
   python scripts/lateral_deploy.py --target copilot --create-pr [--branch-name <name>]
   ```
   - `.github/` 配下にファイルを生成
   - git branch を作成・push（省略時: `asset-lateral-deploy/YYYYMMDD`）
   - PR を自動作成（base: `main`, body: 変換完了通知）

2. **フォールバック**
   - `gh` CLI が未インストール → 手順をコンソール出力
   - git push 失敗 → エラーメッセージ表示

**チェックポイント**: GitHub 上に PR が作成され、`.github/` 配下のファイルが全て含まれていること

---

## セカンダリターゲット（将来実装）

```
# MVP: --target claude-to-claude 変換スタブ
python scripts/lateral_deploy.py --target claude --dry-run
→ "Target 'claude' not yet implemented"
```

別の Claude Code プロジェクトへのコピーは、`scripts/lateral_deploy.py` の `--target claude` で対応予定（PR8: 削除せず MVP 印を記録）。

---

## 変換スキップルール

- **スキップされるスキル**:
  - `user-invocable: false` → Copilot の単体ファイルには出力しない（ただし `spec-principles` は `copilot-instructions.md` に PR1–PR10 を展開）
  - `name` が未記載でも →ディレクトリ名またはファイル stem でフォールバック（変換は実行）

- **スキップされないスキル**:
  - `disable-model-invocation: true` でも → `.github/instructions/<name>.instructions.md` に変換（文脈ルール・ガイドラインとして機能）

---

## Done 条件

✓ `python scripts/lateral_deploy.py --target copilot --dry-run` でエラーなく実行完了  
✓ `.github/prompts/*.prompt.md` が全スキル分生成される  
✓ `.github/instructions/*.instructions.md` が全エージェント分生成される  
✓ `.github/copilot-instructions.md` に PR1–PR10 とスキル一覧が含まれている  
✓ `--create-pr` 実行後、GitHub 上に PR がオープンされている  
✓ `/asset-lateral-deploy` が Claude Code のスラッシュコマンドとして起動可能

---

## 手順サマリ

```
1. `/asset-lateral-deploy` コマンドで本スキルを起動
2. asset-auditor で棚卸し（オプション）
3. dry-run でプレビュー確認
4. create-pr で PR 作成
5. GitHub でレビュー・マージ
```

---

## 参考

- **スクリプト実装**: `scripts/lateral_deploy.py`
- **メタドキュメント同期更新対象**:
  - `CLAUDE.md` — スキル一覧に `/asset-lateral-deploy` を追記
  - `docs/methods/asset-plan.md` — 活動カード追加
  - `.claude/tailoring-registry.md` — 注記行追加
