# native-stacked-pr の設計判断（2026-10-11）

## 重複調査と再利用

review-system main `e388b5b0d3043e777143522b7b43e816c24c0714` の `.ai/skills/` と3 PF loader tree を確認した。native stacked PR を扱う既存 Skill はない。`branch-hygiene` はローカル ref の片付け、`issue-pipeline` は逐次 Issue lifecycle、`branch_source` は分岐元の exact OID 検証であり、GitHub stack object の登録証明を担わない。

GitHub 公式 `github/gh-stack` main `29a36d314be664583705f18e41cebdf2b61ad514` には `skills/gh-stack/SKILL.md`（metadata version 0.2.0）と command／design／troubleshooting references がある。汎用 CLI の Skill を独自再実装・vendor せず、公式本文を使用時に読む repo 専用能力 Skill を追加した。CLI の setup／flag／exit code の詳細は公式と実環境 help を正本とする。repo 独自の gate と下段保護だけを共通本文へ置く。

`asset-pipeline` は明示起動専用なので暗黙起動していない。本 Skill は依存 PR 作業時に自動起動できる能力であり、`disable-model-invocation: true` を付けない。3 PF は skill loader wrapper とし、共通正本は `.ai/` に1つだけ置く。dev-tooling の運用補助として、`issue-pipeline`／`branch-hygiene` と同じく doc-system prompt coverage 対象の追加はしない。

## 既存下段を借りる経路

#609 を #604 の上で先行着手する要求を契機とした。通常の base branch 指定だけでは native stack にならない。既存下段を借りる場合、全 active branch を force-with-lease push する `submit` と、cascade rebase/push を含む `sync` を既定にすると下段を意図せず変更し得るため採用しない。

上段だけを repo の gate で作成・push し、draft PR を通常手段で作り、既存 PR URL 群を `gh stack link` へ渡す経路を選んだ。公式 `cmd/link.go` は URL 引数を branch push 対象から除外する一方、既存 PR base の補正と `--open` による ready 化を行い得る。したがって全 base の事前一致確認と `--open` 不使用を規範化した。stack metadata の登録自体は共有 write であり、下段の内容変更禁止とは区別する。

owner 手動 merge 契約を維持し、公式 Skill の `gh stack merge` 操作例を本 repo の AI 実行契約へ取り込まない。merge 後の自動 base／rebase 処理について実確認を省略する保証は置かず、remote state と差分・CI を再確認する。

## 一次資料

- [GitHub Docs: Creating stacked pull requests](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-stacked-pull-requests) — same-repository 制約、CLI、UI Create stack、既存 chain の変換、Add to stack。
- [公式 gh-stack Skill（確認時 commit）](https://github.com/github/gh-stack/blob/29a36d314be664583705f18e41cebdf2b61ad514/skills/gh-stack/SKILL.md) — version、非対話、branch 対象、worktree、local JSON。
- [公式 command 契約（確認時 commit）](https://github.com/github/gh-stack/blob/29a36d314be664583705f18e41cebdf2b61ad514/skills/gh-stack/references/commands.md) — submit/link/sync/rebase の副作用と非 atomic 性。
- [公式 link 実装（確認時 commit）](https://github.com/github/gh-stack/blob/29a36d314be664583705f18e41cebdf2b61ad514/cmd/link.go) — PR URL 解決、branch push 回避、base 補正、ordered prefix。
- [公式 GitHub client（確認時 commit）](https://github.com/github/gh-stack/blob/29a36d314be664583705f18e41cebdf2b61ad514/internal/github/github.go) — stacks GET/POST、`pull_requests` 順序、stack number/URL。

公開資料と repo code の静的照合まで実施。Skill 作成時に実 PR 作成／stack 登録／下段 rebase／merge は行っていない。API 対応・権限・実版 CLI の成功は対象 repo で使用する時に検証する。
