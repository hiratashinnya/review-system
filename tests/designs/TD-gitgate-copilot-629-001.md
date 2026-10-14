---
id: TD-gitgate-copilot-629-001
title: Copilot明示認可による固定PR base取り込み
---

目的: Issue #629 AC1–4を検証する。前提は実bare remote、非default PR headの
通常clone、fake read-only PR APIであり、Copilot自身のhost認証は仮定しない。

| ケース | 手順 | 期待結果 |
|---|---|---|
| 正常 | 登録→非衝突base開始→continue | 非ゼロunittest成功後にexact 2親/treeのcommit |
| 衝突 | 登録→開始→衝突編集→continue | conflict一覧、成功テストとCAS後にcommit |
| abort | 衝突と無関係/untracked編集→API障害中abort | 全編集recovery保存、元HEADへ復帰 |
| fence | pending中通常commit/push fenceと再登録 | 拒否、pending/session保存 |
| drift | request/workspace branch/session/認可変更 | 拒否、確定しない |
| テスト | 実unittest失敗/成功0件/内容書換 | 拒否、元HEADとpending保持 |
| 既存境界 | Claude/Codex gate・既存base回帰 | 登録全role拒否、fixer-only/raw merge/PR merge維持 |
| F-629-01 | 登録中/pending中/committed後/aborted後にClaude単一候補を確認、実Claude runningを追加 | 差分fallback成功、実running存在時拒否、dispatch writer後も認可保持 |
| 品質 | 全unit、asset_parity/maintainability/guidance_sync | 全pass、baseline変更なし |

TC: `tests/unit/test_base_copilot.py` と既存 `test_base_integration.py`。
結果はTRと保存ログに記録する。公開前ローカル検証でありPR CI結果ではない。
