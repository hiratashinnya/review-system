# ローカルブランチ衛生

すべての説明・質問・報告を日本語で行う。**マージ済み・用済みのローカルブランチ ref を、実データを一切失わずに整理する。** 読み取り専用のサーベイを先に完了し、分類表を提示してからでないと1本も削除しない。origin の ref は絶対に触らない。

## 責務境界（このスキルがしないこと）

- **agent worktree（`.claude/worktrees/`）の削除・台帳操作はしない。** worktree 実体の削除経路は `gitgate` に一元化されている（Issue #354・回収検証と handoff 保全が呼び出し順で守られている）。`git worktree remove` / `git worktree prune` を直接実行しない。回収・解放は `python3 -m gitgate collect-worktree | worktree-release | worktree-forget`、詰まったときの復旧手順は `.ai/troubleshooting/issue-pipeline.md` を参照する。
- **Issue のライフサイクル運用（implement→PR→review→merge→close）はしない**＝`issue-pipeline`。
- **origin／リモート ref を削除しない。** 対象はローカル ref だけ。リモートブランチの削除が要るなら別作業として切り出しオーナーに委ねる。
- ブランチの分岐元ポリシー判定はしない＝`branch_source`。

## 1. 前提を整える

1. `git fetch origin --prune` で origin の追跡 ref を最新化する。以降の「マージ済み」判定は必ず fetch 後の既定ブランチ（通常 `origin/main`）を基準にする。stale なローカル `origin/*` で判定しない。
2. `git worktree list` で、現在チェックアウト中・他 worktree がチェックアウト中のブランチを把握する。**チェックアウト中のブランチは削除対象から外す**（`git branch -d` も構造的に拒否される）。
3. リポジトリの既定ブランチ名を `git symbolic-ref refs/remotes/origin/HEAD` 等で確認する（`main` と決め打ちしない）。以下 `origin/main` と書く箇所は実際の既定ブランチに読み替える。

## 2. 読み取り専用サーベイ（削除する前に必ず全部やる）

### 2-1. 祖先マージで二分する

- `git branch --merged origin/main` … HEAD が `origin/main` の祖先＝**内容は 100% main にある**。既定ブランチ自身とチェックアウト中ブランチを除いた全部が第一級の削除候補。
- `git branch --no-merged origin/main` … 祖先ではない。**ここからが判断作業**。squash merge されたブランチは中身が main にあってもここに出る。

### 2-2. not-merged 群を PR 状態で分類する

`git for-each-ref --format='%(refname:short) %(upstream:short) %(upstream:track)' refs/heads` で upstream の有無・`gone` を把握し、各ブランチに対応する PR を GitHub から引く（`gh pr list --state all --head <branch> --json number,state,mergedAt`）。ブランチが多いときは PR 一覧を1回で取得してローカルで突合する。

| 実態 | 判定 |
|---|---|
| 対応 PR が **OPEN** | **残す**（生きた作業） |
| 対応 PR が **MERGED**（squash で祖先にならなかった） | **削除可**。merge commit の PR 番号／OID を確認記録に残す |
| 対応 PR が **CLOSED（未マージ）** | **オーナー判断**（§2-3 へ） |
| 対応 PR が **無い** | **オーナー判断**（§2-3 へ）。ただしコミット subject 等に「オーナー判断待ち」「WIP」等の生存マーカーがあれば残す |
| ローカルのみ（upstream 無し）で PR 名と同名の使い捨て checkout | 中身が該当 PR（MERGED）と一致するなら削除可 |

### 2-3. オーナー判断群は main と内容を突き合わせて実態を出す

CLOSED-unmerged／PR 無しのブランチは、消してよいと AI が独断で結論づけない（独断禁止）。代わりに**実態**を出す：

- `git log --oneline origin/main..<branch>` … main に無い固有コミット
- `git diff --stat origin/main...<branch>` … merge-base からの変更ファイルと規模
- ファイルが別パスへ移設されている可能性があるときは、対応ファイルを main 側で探し、行数・構造を比較して「後続に吸収済み（superseded）」か「未マージの生きた差分」かを述べる
- 後続 PR に置き換えられている場合はその PR 番号を挙げる

## 3. 分類表を提示して停止する（実行前報告）

サーベイ結果を**チャットに全文**で出す。ID・1行要約だけで投げない。少なくとも：

- **削除候補（祖先マージ）**：本数と一覧
- **削除候補（squash-merged PR／使い捨て checkout）**：各ブランチと根拠 PR
- **残す**：各ブランチと理由（OPEN PR 番号／生存マーカー）
- **オーナー判断**：各ブランチの §2-3 実態と、削除可否についての**理由付き推奨**（PR7＝意見なき停止の禁止）

**ここで停止し、削除の実行可否をオーナーに確認する。** clean 判定や過去の一括承認を事前確認の代わりにしない。

## 4. 承認後にだけ削除する

- 祖先マージ群：`git branch -d <...>`（`-d` は未マージなら弾く二重安全）
- squash-merged と検証済みのもの：`git branch -D <...>`。**`-D` を使うのは PR が MERGED であることを確認済みのブランチだけ。**
- **origin の ref には触らない。**
- 削除後に `git branch` で結果を提示する。reflog による復旧可能期間（既定 ~90 日）も添える。

## 5. worktree の整理が絡むとき

このスキルは worktree を消さない。棚卸しで「用済み worktree がある」と分かったら、**手順を書かず** `gitgate` の verb（`collect-worktree` → `worktree-release --force-uncollected --reason <理由>` → `worktree-forget`）と `.ai/troubleshooting/issue-pipeline.md` の復旧手順へ委譲する。`.claude/worktrees/` 配下でない、台帳に無い手動作成 worktree の扱いに迷ったらオーナーに確認する。

## 設計経緯・却下案・既知の制約

`.ai/rationale/branch-hygiene.md` を参照する。
