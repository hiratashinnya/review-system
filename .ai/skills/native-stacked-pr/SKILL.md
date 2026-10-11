# GitHub ネイティブ stacked PR

依存 PR の上で作業し、GitHub の **stack object** に登録して各層だけをレビューできるようにする repo 運用の能力 Skill。すべての説明・報告は日本語で行う。base branch の指定や `Depends on` 本文だけを native stack と呼ばない。

## 責務と前提

- 汎用 CLI の正本は GitHub 公式 [gh-stack Skill](https://github.com/github/gh-stack/blob/main/skills/gh-stack/SKILL.md)。使用時に本文と、対象操作の `references/commands.md` を読み、実環境の `gh stack <command> --help` と照合する。公式 Skill の一般手順を本 Skill へ複製しない。
- 本 Skill は repo の分岐元検証・下段保護・native 登録証明を追加する。Issue 処置順、実装、レビュー、worktree の寿命は既存担当の責務。`issue-pipeline` を暗黙起動しない。
- 利用可能な別コンテキストへ実装とレビューを分離する。supervisor を使う前提にしない。ユーザーが禁止していれば通常の subagent を用いる。
- 共有状態への write は repo guidance とセッションの認可に従う。実行対象・差分・下段への影響を事前報告する。既に対象操作が明示認可されていれば同じ認可を再要求しない。**AI は merge／auto-merge／merge queue 投入を実行せず、fresh blocker evidence を示して owner の手動操作へ委ねる。**
- GitHub CLI 認証、Git 2.36+、公式 `github/gh-stack` 拡張、same-repository の全 branch が必要。未導入なら公式拡張を導入する。fork 間 stack は扱わない。

## 1. 読み取りと実行範囲の固定

1. repo の guidance、担当ロール契約、作業 tree の clean 状態、worktree 所有者、remote を確認する。repo の default branch を取得し、`main` と決め打ちしない。
2. 下段 PR の OPEN 状態、head/base repo、head ref、exact head OID、base ref、draft 状態を fresh API から記録する。既存 stack の有無・全層の順序・stack number も remote metadata で確認する。
3. 今回変更してよい層と、読み取り専用で保護する層を明記する。下段を取り込むだけなら、そのコード・commit・head ref・base・本文・draft 状態を変更しない。保護する下段が別 stack の途中にある場合、勝手に並べ替えたり fork したりしない。
4. 従来の「前の Issue が merge-close してから次へ」と stacked 先行着手が競合する場合、既存のユーザー指示を確認する。先行着手が認可済みならその例外・依存関係を報告へ残す。認可がなく処置順の変更が必要なら比較・推奨を示して owner 判断へ返す。

## 2. 分岐元ゲートを通して上段を作る

repo の `branch_source` は same-repository OPEN PR の fresh exact head OID を許す。新規 branch 作成は **`gitgate new-branch`** を通す。`gh stack init/add` や直接 `git switch -c` でこのゲートを迂回しない。

```bash
python3 -m gitgate new-branch <UPPER-BRANCH> --repository <OWNER/REPO> --base-ref <DEFAULT-BRANCH> --base-oid <LOWER-HEAD-OID> --base-pr <LOWER-PR>
```

`--base-ref` は repo の **default branch**、`--base-oid` は下段 PR の head OID。下段の head branch 名を `--base-ref` に渡さない。検証中に下段が更新されたら fresh metadata からやり直し、旧 OID で先へ進まない。agent worktree は既存の `gitgate` 契約に従って確保する。

上段だけに変更し、担当ロールの検証・commit 契約を通す。上段と下段の差分に今回の変更だけが含まれることを確認する。

## 3. 既存の下段を保護して native 登録する

既存 PR を下段に借りる場合の既定は **上段だけを push・PR 作成し、PR URL で link**。stack 全体を push する `submit` は使わない。

1. fresh な下段 metadata と OID を再確認し、事前記録と一致しなければ後述の追随へ進む。
2. 上段を current branch にした状態で、認可済みの `python3 -m gitgate push` を実行する。上段の draft PR を、下段 head branch を base に作成する。本文は利用 AI 名、対象 Issue、依存 PR、変更、検証を記載する。shell 投稿なら body file を用いる。
3. 下段から上段の順で URL を渡す。**`--open` を付けない**。PR URL は branch 引数と異なり push を伴わず、数字の stack/PR 解釈も避けられる。

```bash
gh stack link <LOWER-PR-URL> <UPPER-PR-URL> --base <DEFAULT-BRANCH> --remote origin
```

4. 既存 stack を延長する場合は、既存全層を下から上へ列挙した PR URL に上段 URL を足す。既存層は ordered prefix を保ち、省略・入替・別 stack からの移動をしない。
5. `link` は誤った base を補正し得る。実行前に **全既存 PR の base が期待した連鎖と一致**することを確認する。下段 base が default 以外なら、その trunk を `--base` に指定する。補正が必要なら保護対象を勝手に変更せず、具体的な影響を owner へ報告する。

CLI が使えない場合、GitHub UI の Create stack／既存 chain の変換／Add to stack を使える。通常の PR 作成 connector の成功だけでは native 登録完了としない。利用できる write 手段がなければ local 成果物と draft 本文まで整え、未登録であることを報告する。手動 base 管理へ無言でフォールバックしない。

## 4. 登録を remote metadata で証明する

公式 gh-stack が使用する read API を再取得する（connector で未対応なら `gh api`）。全ページを確認する。

```bash
gh api 'repos/<OWNER>/<REPO>/stacks?pull_request=<UPPER-PR>&per_page=100'
gh api 'repos/<OWNER>/<REPO>/stacks/<STACK-NUMBER>'
```

- remote stack の `number`／`url`、`pull_requests[].number` の下から上への順序、各 head ref、stack base を記録する。予定外の層が混入していないことを確認する。
- 各 PR の base/head OID と検証済み差分を別途確認する。保護した下段の head OID・base・draft・本文が変わっていないことを比較する。
- local tracking を採用した場合は `gh stack view --json` も確認する。ただし local catalog だけでは remote native 登録の証拠にならない。
- 404／exit 9、認証・権限・repo 機能設定不足、API partial response は登録成功と扱わない。確認済みの範囲と不足 evidence を明記する。status 0 でも warning や `Sync aborted` があれば remote 状態を実証してから判定する。

## 5. 下段更新・merge 後の追随

- `rebase` は複数 branch を書き換え、`push`／`submit` は全 active branch を push し、`sync` は fetch→rebase→push を行う。既存下段を保護する場面で無条件に実行しない。`--upstack` も current layer から対象になるため、下段上で実行すれば下段を巻き込む。
- 下段が更新されたら fresh metadata を取り直し、変更対象を上段に限定して追随する。local tracking を使うときはゲートで作成済み branch だけを `init` で採用し、書換対象と worktree 所有者を確認する。上段からの `rebase --upstack --no-trunk` 等も実版の help／公式 reference を読み、下段を対象に含めないことを確認して使う。push は上段だけに限定し、履歴変更の force 操作が必要なら認可・lease 条件を具体化する。
- owner が下段を merge した後、GitHub の stack・PR base・上段差分・CI を再取得する。自動処理を想定して確認を省略しない。squash 後に旧下段 commit が上段差分へ残っていないことを確かめ、必要な上段追随を行う。
- merge 判断前には各層を独立レビューし、repo の `pr_merge_gate report` が対象 base／依存関係をどう判定したかを示す。stack 特有の blocker を隠さず、gate を改変・迂回して通さない。owner 手動 merge 後に Issue close と残る stack を確認する。

## 完了報告

各 PR URL、依存順、remote stack number／URL、下段保護の比較、差分・検証結果、未実行操作と未確認点を示す。native 登録が未確認なら「stack 作成済み」と報告しない。

設計判断・重複調査・公式資料の確認記録は [rationale](../../rationale/native-stacked-pr.md) を参照する。
