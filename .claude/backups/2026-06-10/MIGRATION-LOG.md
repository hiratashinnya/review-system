# 移行ログ（2026-06-10）

## 目的
doc-system の USDM 分割・テスト3層（TD/TC/TR）・`condition` 属性・`suppress` 属性・`result`/`log_ref` メタ属性の確定に伴い、
既存スキルの整合性を保つための退避と更新を記録する。

## 退避一覧

| ファイル | 退避元（active） | 退避先（backup） | 理由 |
|---|---|---|---|
| `test-strategy SKILL.md` | `.claude/skills/test-strategy/SKILL.md` | `.claude/backups/2026-06-10/test-strategy-SKILL.md` | `TC-` → `TD-` prefix リネーム・TR frontmatter（result/log_ref）追加に伴い更新前退避 |

## 更新内容サマリ

### test-strategy（active）
**変更理由**: doc-system でテスト3層（TD/TC/TR）が確定（DD-009）し、  
test-strategy のケース Markdown が `TC-` prefix を使っていたため `TD-` に統一。  
合わせて TR（成績書）の frontmatter に `result: PASS|FAIL` と `log_ref` を追加（DD-011）。

**対応マッピング**:
| 旧名称 | 新名称 | doc-system 対応型 |
|---|---|---|
| ケース（`tests/cases/*.md`） | テスト設計（`tests/designs/*.md`） | TD（テスト設計） |
| unittest コード（`tests/unit/`） | テストコード（`tests/unit/`） | TC（テストコード） |
| 成績書（`tests/reports/*.md`） | テスト結果（`tests/reports/*.md`） | TR（テスト結果） |
| ケース ID `TC-<area>-<nnn>` | テスト設計 ID `TD-<area>-<nnn>` | TD- prefix |

### io-event-ledger
**変更なし**：FR/SPEC の参照を持たないため更新不要。

### spec-inspector（サブエージェント）
**変更なし**：`TC→FR verifies` の旧参照は見当たらず、プロンプト内容のチェック不要と判断。

## 復元方法

```bash
# test-strategy を退避前に戻す場合
cp .claude/backups/2026-06-10/test-strategy-SKILL.md .claude/skills/test-strategy/SKILL.md
```

---

## doc-authoring スキル廃止（2026-06-10）

**変更理由**: 工程横断の doc-authoring スキルは粒度が粗すぎ auto-load の無駄。  
authoring 規約は各フェーズスキル（spec-pipeline・test-strategy 等）に持たせる設計に変更（方針変更：工程ごとにスキル化・doc-authoring はプレーン Markdown）。

**対応**:
| 対象 | 変更内容 |
|---|---|
| `.claude/skills/doc-authoring/` | 削除（auto-load から除外）|
| `docs/doc-system/07-authoring-guide.md` | SKILL.md 参照を削除、プレーン Markdown 参照文書として継続 |
| `.claude/tailoring-registry.md` | doc-authoring エントリを廃止済みとしてマーク |

**退避先**: `.claude/backups/2026-06-10/doc-authoring-SKILL.md`

```bash
# doc-authoring を退避前に戻す場合
mkdir -p .claude/skills/doc-authoring
cp .claude/backups/2026-06-10/doc-authoring-SKILL.md .claude/skills/doc-authoring/SKILL.md
```
