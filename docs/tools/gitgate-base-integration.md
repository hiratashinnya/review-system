# PR base 取り込み契約（gitgate-base-integration/2.1）

`gitgate integrate-base` / `integrate-base-continue` / `integrate-base-abort` は、**OPEN PR の base を、その PR の head ブランチの checkout へ取り込み、必要な衝突を解消して確定する**ための操作である。設計目標は善意の利用者・AI による誤操作の防止であり、悪意ある実行者の迂回を阻止すること（sandbox・耐タンパ性）ではない。

本書が現行契約である。policy 2.0 は Issue #706 のオーナー決定による MAJOR 改訂で、#594（PR #600）・#629（PR #640）の設計判断（`.ai/rationale/gitgate-base-integration-594.md`・`.ai/rationale/gitgate-copilot-base-integration-629.md`）に優先する。両文書は履歴として保持する。#706 の判断経緯は `.ai/rationale/gitgate-base-integration-706.md`。

policy 2.1 は Issue #716 により、PR の `base.sha` と現在の base branch 先端が異なる場合を許容し、先端を branch API と fresh fetch で照合する MINOR 改訂である。

## 使い方

PR head ブランチを checkout した clean な作業ツリー（linked worktree・通常 clone・primary worktree のいずれでもよい）で実行する。
`BASE_OID` は PR 情報の `base.sha` ではなく、PR の base branch の現在の先端 OID を指定する。

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
| 引数の `--expected-head` ＝ 現在の HEAD ＝ live head、`--expected-base` ＝ PR base branch の live 先端 | 古い情報や別 PR の OID を見て取り込む |
| fresh fetch 後の `origin/<head>`・`origin/<base>` ＝ 引数の OID、fetch 前後で PR 情報と branch 先端が不変 | 取り込み直前に PR が更新・retarget されたのに古い base を取り込む |
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

開始から確定・中止までの間、当該作業ツリーの Git 管理領域（`git rev-parse --git-path gitgate-base-integration.json`）に、PR 番号・repository・branch・元 HEAD・base ref と OID・開始時の衝突ファイル一覧を1件だけ置く。作業ツリー内には何も書かない。これは他の操作との取り違えを防ぐための記録であり、認可や耐タンパの仕組みではない。canonical worktree 台帳（`tmp/_worktree/`）は使わない（policy 1.x の `base_integrations` / `base_authorizations` は読まない）。policy 2.0 の進行中記録には base ref がないため、2.1 では continue できない。abort で退避・中止し、再開始する。

## 中止と回復

- `integrate-base-abort` は PR API に依存しない。HEAD から変わった tracked ファイル・ignore 外の新規ファイルと `MERGE_HEAD` / `MERGE_MSG` を、共通 Git ディレクトリの `gitgate-base-recovery/<時刻>-<pid>.tar` に保存してから `git merge --abort` を実行し、保存先を返す。ignore 外の新規ファイルは中止後も作業ツリーに残り、残っている間は `integrate-base` が開始を拒否する（開始条件は未追跡ファイルを含めて作業ツリーが clean であること）。同じファイルは退避 tar にも入っている。この制約が効くのは、同じ作業ツリーで取り込みをやり直す場合である。Issue-pipeline の外で gate の無い呼び出し元（オーナー・主文脈・`general-purpose` 等の `GATED_ROLES` に入らないロール）が同じ作業ツリーでやり直すときは、再開始の前に残った新規ファイルを片付ける。Issue-pipeline 内の `issue-fixer` は同じ作業ツリーでやり直さない（次項「復元の実行者」）。
- 退避 tar の構成：`worktree/<パス>`（作業ツリー上の当該ファイル。記号リンクはリンクのまま）と、存在した場合だけ `git/MERGE_HEAD`・`git/MERGE_MSG`。`worktree/` 配下は「HEAD から変わったファイル」の丸ごとの写しなので、利用者の衝突解消の編集だけでなく、**取り込み中だった base 側の変更もそのまま含む**。HEAD に存在し作業ツリーから消えていたファイルは tar に入らない。
- 退避からの復元：tar 全体を作業ツリーへ展開しない（base 側の変更が取り込みの記録なしに作業ツリーへ混ざる）。`integrate-base` で取り込みをやり直し、`tar -tf <tar>` で中身を確認したうえで、衝突解消に必要なファイルだけを `tar -xOf <tar> worktree/<パス>` で標準出力へ取り出す。現在のファイルと比較して必要な編集だけを適用し、`integrate-base-continue` で確定する。`worktree/` には HEAD から変わった tracked ファイルに加え、ignore 外の新規ファイル（`git ls-files --others --exclude-standard`）も入る。記号リンクのエントリは `tar -xOf` では何も出力されないので、リンク先は `tar -tvf <tar>` で確認する。
  - 復元の実行者：`tar` は `issue-fixer` には使えない（両 PF の `agent-command-gate.sh` は gated ロールのコマンドを `git`・`gh`・`pyright`・許可された `python3 -m` モジュールに限り、`ctx_execute` 経由でも同じ判定を掛ける。Read ツールでは tar を開けない）。`issue-fixer` は中止後に作業を止め、`integrate-base-abort` が返した退避 tar のパスを含めてオーナーへ報告する。tar の一覧・取り出しは、オーナーまたは gate の無い呼び出し元（主文脈・`general-purpose` 等の `GATED_ROLES` に入らないロール）が行う。その先の衝突解消の適用・確定を誰が行うかは、gate の有無ではなく Issue-pipeline を運用中かどうかで決まる。
    - Issue-pipeline の運用中：主文脈が行うのは退避 tar の一覧・取り出しと、`issue-fixer` を再 dispatch するときに取り出した内容を渡すことまでで、衝突解消の適用・確定は行わない（実装・是正は別文脈へ分離する＝`.ai/guidance/common.md`「作業分離・判断境界」）。退避元の作業ツリーに残った新規ファイルの片付けも行わない。停止した `issue-fixer` の作業ツリーの回収・解放は無条件ではない。`issue-fixer` の1回目の停止は `SubagentStop` のカルテ停止ゲートに拒否されることがあり（中止を含む取り込み起因の STOP が Step 1 の診断登録より前なら、カルテへ記録せずにもう一度停止する＝`.ai/agents/issue-fixer.md`「取り込みとカルテ手順の順序」）、`SubagentStop` フックが回収・解放するのは、停止が通り、かつその `issue-fixer` 自身のハンドオフが作業ツリーにあるときだけである。回収されずに残った場合は `.ai/troubleshooting/issue-pipeline.md` の手順に従う。再 dispatch された `issue-fixer` は新しい作業ツリー（`isolation: "worktree"`）で `gitgate adopt-branch` により PR ブランチを取得して始める。退避 tar は共通 Git ディレクトリにあるので、作業ツリーの解放後も残る。作業ツリーやブランチの残留で再 dispatch が拒否された場合（`ISSUE_START_WORKTREE_RESIDUE`・`ISSUE_START_WORKTREE_UNCLAIMED`・`BRANCH_ADOPT_LOCAL_EXISTS`）は、`.ai/troubleshooting/issue-pipeline.md` の手順に従う（作業ツリーを手で削除しない）。`issue-fixer` が `integrate-base` による再開始・必要な編集の適用・`integrate-base-continue` を行う。
    - Issue-pipeline を運用していないとき（オーナーの直接指示で動く主文脈・`general-purpose` 等）：取り出しから確定までを自分で行ってよい。
- 保存できない場合は `merge --abort` を実行しない。`merge --abort` が失敗した場合は保存先を含むエラーで停止し、記録は残す。
- merge が gitgate の外で終わった（手動の `git merge --abort`・手動 commit 等）後に記録だけが残った場合、`integrate-base-abort` は記録を消して `{"status": "cleared"}` を返す。何も中止しない。
- 記録と異なる merge が進行中の場合、continue・abort はいずれも拒否する。生の `git merge`（`--abort` を含む）は `.claude/settings.json` の deny・`.codex/rules/default.rules`・両 PF の `agent-command-gate.sh` が全 AI ロールに対して拒否するので、AI はこの merge を自分では片付けられない。AI は作業を止め、branch・`git status` の要約・拒否メッセージをオーナーへ報告する。オーナーが手動でその merge を中止した後、`integrate-base-abort` で記録を消す。
- continue が検査で止まった場合、Git 状態と記録はそのまま残る。指摘を直して continue を再実行するか、abort する。
- 記録ファイルが読めない・壊れている場合は `BASE_STATE_INVALID: <パス>` で停止する。Git の merge 状態を確認して片付けてから、そのファイルを削除する。merge が進行中なら、上と同じく AI は停止してオーナーへ報告し、オーナーが中止する。
- policy 1.x で開始して未完了のまま残った取り込みは 2.0 では認識せず、`integrate-base-abort` も中止しない。上と同じく AI は停止してオーナーへ報告し、オーナーが手動で merge を中止して片付ける。

## ロール境界（呼び出し元の責務）

GitGate 本体はロールやハーネスを同定しない。ロール別の許可・禁止は呼び出し元の command gate とワークフローポリシーで扱う。

- Issue-pipeline の工程ロール（`issue_start/gated_roles.py` の `GATED_ROLES`）のうち、取り込みを使えるのは `issue-fixer` だけ。`issue-implementer`・`pr-reviewer` 等は `.claude/hooks/agent-command-gate.sh`・`.codex/hooks/agent-command-gate.sh` が拒否する。
- `GATED_ROLES` に入らない呼び出し元（主文脈・`general-purpose` 等）には pipeline 専用のロール制約（command gate）を波及させない。ただし Issue-pipeline の運用中は、主文脈もワークフローポリシー（作業分離）に従い、取り込みの解消・確定を `issue-fixer` に委ねる（「中止と回復」の「復元の実行者」）。
- Copilot など project hook の無い実行環境も、同じ CLI をそのまま使う。専用の登録・認可手順は無い。
