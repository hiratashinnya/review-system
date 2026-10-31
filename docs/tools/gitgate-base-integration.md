# PR base 取り込み契約（gitgate-base-integration/2.0）

`gitgate integrate-base` / `integrate-base-continue` / `integrate-base-abort` は、**OPEN PR の base を、その PR の head ブランチの checkout へ取り込み、必要な衝突を解消して確定する**ための操作である。設計目標は善意の利用者・AI による誤操作の防止であり、悪意ある実行者の迂回を阻止すること（sandbox・耐タンパ性）ではない。

本書が現行契約である。policy 2.0 は Issue #706 のオーナー決定による MAJOR 改訂で、#594（PR #600）・#629（PR #640）の設計判断（`.ai/rationale/gitgate-base-integration-594.md`・`.ai/rationale/gitgate-copilot-base-integration-629.md`）に優先する。両文書は履歴として保持する。#706 の判断経緯は `.ai/rationale/gitgate-base-integration-706.md`。

## 使い方

PR head ブランチを checkout した clean な作業ツリー（linked worktree・通常 clone・primary worktree のいずれでもよい）で実行する。

```sh
python3 -m gitgate integrate-base --repository OWNER/REPO --pr N --expected-head HEAD_OID --expected-base BASE_OID
# exit 0 + {"status": "ready"}     : 衝突なし。continue で確定する
# exit 3 + {"status": "conflicts"} : 衝突ファイル一覧。編集して解消する
# exit 0 + {"status": "no_change"} : base は既に head に取り込み済み。何もしない
# 衝突以外に直した tracked ファイル・新規ファイル・再生成した生成物は、意図して stage する
python3 -m gitgate add path/to/extra-file
python3 -m gitgate integrate-base-continue
# 中止する場合
python3 -m gitgate integrate-base-abort
```

- 取り込みは固定の `git merge --no-ff --no-commit <base OID>`。任意の ref・Git option・merge 戦略は受け付けない。
- continue は、開始時に衝突したファイルのうち未解消のものだけを自動 stage してから、index を2親の merge commit `[元 HEAD, base OID]` として確定する。衝突ファイル以外の変更は自動 stage しない（意図しない全ファイル stage はしない）。
- 設定・エージェント定義・ガイダンス・生成物を含め、パス名を理由に停止しない。
- テストの実行・成功は確定の前提にしない。必要なテスト・品質保証は呼び出し元のワークフローと CI が担う。
- push は通常の `gitgate push` で行う。PR 自体の merge・auto-merge（head→base の公開マージ）は本 verb の権限外で、raw `git merge` の禁止も従来どおり。

## 保持する検査と防ぐ失敗モード

| 検査 | 防ぐ失敗モード（善意の誤操作） |
|---|---|
| live PR が OPEN・同一 repository（fork でない）・PR 番号一致 | 閉じた PR や fork PR、番号違いの PR の base を取り込む |
| live PR の head ref ＝ 現在の branch、head ref ≠ base ref | 別ブランチ（別 PR の head）を誤って変更する |
| head ref ≠ repository の default branch | default branch を取り込み先にして、default branch に merge commit を作る |
| 引数の `--expected-head` ＝ 現在の HEAD ＝ live head、`--expected-base` ＝ live base | 古い情報や別 PR の OID を見て取り込む |
| fresh fetch 後の `origin/<head>`・`origin/<base>` ＝ 引数の OID、fetch 前後で PR 情報が不変 | 取り込み直前に PR が更新・retarget されたのに古い base を取り込む |
| 開始時に作業ツリー clean（ignore 外の新規ファイル含む）・merge/rebase/cherry-pick/revert 進行中でない | 未コミットの作業が merge と混ざって区別できなくなる／別の Git 操作を壊す |
| 進行中記録（後述）が無いこと | 同じ checkout での二重開始 |
| continue/abort 時、記録と現在の branch・HEAD・`MERGE_HEAD` が一致し、他の Git 操作が進行中でない | gitgate が開始していない merge（手動 merge 等）や、HEAD が動いた後の状態を取り違えて確定・中止する |
| continue 時に live PR を再照合 | 解消中に base が進んだ・PR が retarget されたのに古い base で確定する |
| 記録済み衝突ファイルに衝突マーカー行（`<<<<<<< ` 等）が残っていない | 未解消の衝突を自動 stage して確定する |
| 記録外の未解消 index が無い | 想定外の衝突を見落として確定する |
| stage されていない tracked 変更・ignore 外の新規ファイルが残っていない | 解消に必要な編集を stage し忘れ、作業ツリーでは正しく見えるのに確定 commit から欠落する |
| 確定 commit の親列が `[元 HEAD, base OID]` | 1親 commit や別 base との merge を「取り込み済み」として扱う |
| 進行中は通常の `gitgate commit` を拒否 | 通常 commit が取り込み途中の merge を上記検査なしに確定し、記録だけが残る |
| abort 前に編集を退避 | `merge --abort` で衝突解消の編集が黙って失われる |

ロール・ハーネス・dispatch 台帳・登録・承認・テスト実行・保護パスはいずれも検査しない。

## 進行中記録

開始から確定・中止までの間、当該作業ツリーの Git 管理領域（`git rev-parse --git-path gitgate-base-integration.json`）に、PR 番号・repository・branch・元 HEAD・base OID・開始時の衝突ファイル一覧を1件だけ置く。作業ツリー内には何も書かない。これは他の操作との取り違えを防ぐための記録であり、認可や耐タンパの仕組みではない。canonical worktree 台帳（`tmp/_worktree/`）は使わない（policy 1.x の `base_integrations` / `base_authorizations` は読まない）。

## 中止と回復

- `integrate-base-abort` は PR API に依存しない。HEAD から変わった tracked ファイル・ignore 外の新規ファイルと `MERGE_HEAD` / `MERGE_MSG` を、共通 Git ディレクトリの `gitgate-base-recovery/<時刻>-<pid>.tar` に保存してから `git merge --abort` を実行し、保存先を返す。ignore 外の新規ファイルは中止後も作業ツリーに残る。再開始する前に片付ける。
- 保存できない場合は `merge --abort` を実行しない。`merge --abort` が失敗した場合は保存先を含むエラーで停止し、記録は残す。
- merge が gitgate の外で終わった（手動の `git merge --abort`・手動 commit 等）後に記録だけが残った場合、`integrate-base-abort` は記録を消して `{"status": "cleared"}` を返す。何も中止しない。
- 記録と異なる merge が進行中の場合、continue・abort はいずれも拒否する。その merge は自分で `git merge --abort` 等で片付けてから `integrate-base-abort` で記録を消す。
- continue が検査で止まった場合、Git 状態と記録はそのまま残る。指摘を直して continue を再実行するか、abort する。
- 記録ファイルが読めない・壊れている場合は `BASE_STATE_INVALID: <パス>` で停止する。Git の merge 状態を確認して片付けてから、そのファイルを削除する。
- policy 1.x で開始して未完了のまま残った取り込みは 2.0 では認識しない。必要なら `git merge --abort` で片付ける。

## ロール境界（呼び出し元の責務）

GitGate 本体はロールやハーネスを同定しない。ロール別の許可・禁止は呼び出し元の command gate とワークフローポリシーで扱う。

- Issue-pipeline の工程ロール（`issue_start/gated_roles.py` の `GATED_ROLES`）のうち、取り込みを使えるのは `issue-fixer` だけ。`issue-implementer`・`pr-reviewer` 等は `.claude/hooks/agent-command-gate.sh`・`.codex/hooks/agent-command-gate.sh` が拒否する。
- Issue-pipeline 外（主文脈・`general-purpose` 等）には pipeline 専用のロール制約を波及させない。
- Copilot など project hook の無い実行環境も、同じ CLI をそのまま使う。専用の登録・認可手順は無い。
