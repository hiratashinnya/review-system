# Issue #706: PR base 取り込みを責務に絞る

対象: https://github.com/hiratashinnya/review-system/issues/706

現行契約は `docs/tools/gitgate-base-integration.md`（policy 2.0）。本書は #594 / #629 の設計判断
（`gitgate-base-integration-594.md`・`gitgate-copilot-base-integration-629.md`）を置き換えた理由を残す。

## オーナー決定（要約）

- GitGate は OPEN PR の base→その PR の head checkout の取り込みだけを担う。方向は live PR 情報と
  実 Git 状態で確認し、default branch を取り込み先にしない。Git の整合性に直結する最小限の検査は残す。
- 設計目標は善意の誤操作防止。悪意ある実行者への耐タンパ・sandbox は非目標。
- ロール境界は呼び出し元（command gate / ワークフロー）へ移す。Issue-pipeline 内は `issue-fixer` だけ、
  pipeline 外（主文脈・`general-purpose` 等）には波及させない。
- 新たな安全対策は、具体的な誤操作シナリオ・最小検査で防げない理由・正常操作へのコストを示し、
  オーナー承認を得るまで要件化しない。

## 撤去したもの

| 撤去 | 理由 |
|---|---|
| `base_authority.py`（running `issue-fixer` dispatch 必須・primary worktree 一律拒否） | 主文脈・`general-purpose` の正常な取り込みを阻害。ロール判定は呼び出し元 gate の責務 |
| `base_copilot.py`・`integrate-base-copilot-register`・台帳の `base_authorizations` | ハーネス別の登録は Git 操作の成立条件ではない。別名の登録制度にも置き換えない |
| `base_protection.py`（protected path の incoming change で開始前 STOP） | 取り込みが必要な変更を取り込めなくする自己矛盾。パス名だけで止めない |
| `base_tests.py`・continue の `--test-module`・固定 unittest 成功と非ゼロ件の強制 | Git 操作と品質検証の責務混同。テストは呼び出し元ワークフロー・CI が担う |
| `base_resolution.py` の衝突外 tracked 変更・新規ファイル・非衝突 index 変化の拒否 | 周辺ファイル修正・生成物再生成を妨げる。明示 stage した変更は確定対象にする |
| canonical worktree 台帳への operation 記録（`base_integrations`）・PID/start token 予約・内容ハッシュ CAS・ledger CAS | 台帳とロール束縛は撤去した認可モデルの一部。同一 checkout の並行実行は Git の index lock と記録ファイルの排他作成で足り、内容 CAS は耐タンパ寄りで善意の誤操作に対応する失敗モードが無い |

## 置き換えた最小機構

進行中記録は当該作業ツリーの Git 管理領域の1ファイル（`gitgate-base-integration.json`）に移した。
防ぐ失敗モードは「gitgate が開始していない merge を continue/abort が取り違える」「二重開始」の2つで、
ロールや台帳には依存しない。abort 前の退避先は、worktree を削除しても残るよう共通 Git ディレクトリの
`gitgate-base-recovery/` にした。各検査が防ぐ失敗モードは現行契約の表に記載する。
