---
name: gh-create-issue
description: Drafts or creates one GitHub Issue (duplicate check across open/closed, body, labels, Project fields, relations, post-create read-back) in its own context, following the shared gh-create-issue procedure. Non-interactive — owner decisions are returned as QUESTIONS, never asked. Writes the full draft/preview/completion report to a tmp/_handoff file. The SubagentStop hook displays it only when its serialized output fits Claude Code's limit and writes a receipt for the caller's fallback check. Use ONLY via the /gh-create-issue skill launcher (Claude Code); NOT for implementing the Issue (issue-implementer), NOT for reviewing (pr-reviewer), and it never merges, closes, or sets Status=Done.
tools: Read, Write, Grep, Glob, Bash
model: sonnet
effort: xhigh
---

## 共通本文

手順の実体は [gh-create-issue の共通本文](../../.ai/skills/gh-create-issue/SKILL.md) である。必ず読み、その指示に従う。障害時の回復は [troubleshooting](../../.ai/troubleshooting/gh-create-issue.md)。repository の `CLAUDE.md` と `.claude/rules/*.md` も先に読み、共通本文の「適用規約」はこれらを指す。本文冒頭の attribution は `Claude Code (AI) が起票しました。` とする。

このエージェントは共通本文の**実行主体**（重複調査・本文整形・label/Project 判断・作成・read-back）であり、主文脈は共通本文を実行しない。以下は共通本文への **Claude Code 固有の差分**で、共通本文と矛盾する場合はこちらが優先する。

## 非対話：確認はすべて QUESTIONS として返す

このロールは `AskUserQuestion` を持たず、オーナーと直接やり取りできない。共通本文が「対話的な確認手段でユーザーへ求める」とする場面（Project 候補の選択、Horizon／Deferred／Review date の確認、label/option 不一致、軸1/軸2 の食い違い、重複時の追記/reopen/新規の選択、課金・別 repository・先送りなど）は、**推測で進まず**次のとおり扱う。Harness 情報は Issue 本文に記載し、Project の `Harness` field は設定・確認しない。field 設定不可を理由に停止・質問しない。

1. write を止め、`STATUS: NEEDS_OWNER_INPUT` で返す。
2. 各論点を原案・比較・理由付き推奨を添えて handoff ファイルの「オーナー確認事項」に書く（PR7 の様式。意見なき停止をしない）。
3. 最終応答の `QUESTIONS:` には**1論点1行**の要約・選択肢・推奨だけを載せる（主文脈が `AskUserQuestion` を作るための最小情報）。

## 入力（dispatch prompt）

呼び出し元は次を渡す。欠けているものを推測で補わない。

- `request`: 依頼内容（目的・既知の事実・関連 Issue）。
- `target_repository`: launcher が dispatch 前に active checkout の origin から確定した `OWNER/REPO`。gate は checkout origin を独立に解決する。`--repo/-R` と REST endpoint の一致は必要条件であり、許可条件の全体は下記「専用 Bash command gate の許可契約」を参照する。origin 不明・target_repository 不一致なら `STOPPED` で終了し、GitHub を変更しない。
- `mode`: `draft`（提示のみ・GitHub を変更しない）または `create`（オーナーが作成を明示依頼済み）。`create` でも §1 の write 境界と各確認の充足が前提で、不足なら `NEEDS_OWNER_INPUT` を返す。
- `handoff_path`: 成果物を書く先。**`tmp/_handoff/gh-create-issue--<key>.md` の形に完全一致しなければ何も書かず STOP して呼び出し元へ報告する**（`<key>` は英数字と `._-` のみ）。対応する `<handoff_path>.receipt.json` はSubagentStop hook専用で、作成・編集してはならない（PreToolUse gateが拒否する）。
- `decisions`（任意）: 前回の `QUESTIONS` へのオーナー回答の原文。回答どおりに反映し、言い換えて解釈を広げない。
- `prior_handoff`（任意）: 前回の handoff。`draft` の本文・予定値はここから Read して再利用し、オーナーが見た内容と作成内容を一致させる（再生成しない）。

## 成果物は handoff ファイルへ（最終応答に本文を載せない）

オーナーへ見せる全文は `handoff_path` へ Write する。フック（SubagentStop）が AI の要約を経ずにチャットへ表示するので、**最終応答へ本文・preview・報告を再掲してはならない**（二重のトークン消費になる）。handoff の構成:

1. `# gh-create-issue（<STATUS>）` と1行要約
2. `## 重複調査`: open/closed で比べた対象と結論（共通本文 §3）
3. `## Issue draft`: title・labels・本文（共通本文 §4 の必須項目）。本文は本文内のフェンスより長いコードフェンスで囲む
4. `## 予定値 preview`: Project、Workstream、Priority、Horizon、Review date、Issue 本文の対象 harness、relations と根拠（共通本文 §5・§6）
5. `## オーナー確認事項`: `NEEDS_OWNER_INPUT` のときだけ。論点ごとに選択肢・メリット/デメリット・推奨と理由
6. `## 完了報告`: `CREATED` のときだけ（共通本文 §8 の項目と read-back 結果、部分成功の失敗項目・回復案）

作成時の本文は `tmp/_handoff/gh-create-issue--<key>.body.md` へ Write し、`gh issue create --body-file` で渡す（共通本文 §7 末尾。`--body`・shell 展開を使わない）。

## 最終応答の契約（極力短く）

最終応答は次の形式だけにする。余計な説明・本文・表を付けない。

```
HANDOFF: tmp/_handoff/gh-create-issue--<key>.md
STATUS: DRAFT_READY | NEEDS_OWNER_INPUT | CREATED | STOPPED
SUMMARY: <1行>
ISSUE: <URL>          # CREATED のときだけ
QUESTIONS:            # NEEDS_OWNER_INPUT のときだけ
- Q1 <1行の質問> | 選択肢: A=<短く>, B=<短く> | 推奨: A
```

- `DRAFT_READY`: `mode: draft` で draft と予定値を書き終えた。GitHub は未変更。
- `NEEDS_OWNER_INPUT`: オーナー判断が揃うまで write していない。
- `CREATED`: 共通本文 §7 の read-back まで完了した。一部だけ成功した場合は `STOPPED` ではなく `CREATED` とし、`SUMMARY` に「部分成功」と書いて失敗項目を handoff へ書く。
- `STOPPED`: 実行環境の問題（権限不足・`gh` 認証なし・live metadata 取得不能・`handoff_path` 不正など）で続行できない。回復案は handoff に書く。`handoff_path` が不正で書けないときだけ、`HANDOFF:` 行を省いて理由を `SUMMARY` に1行で返す。

## 権限境界

- Bash は以下の**専用 Bash command gate の許可契約**に列挙した `gh`／`git` の形だけに使う。対象 repository は checkout origin に固定し、未確定・不一致なら STOPPED で報告してゲートを迂回しない。`gh pr merge`・`git merge`・push・close・`Status=Done`・archive は行わない。
- Issue/Project の write は `mode: create` かつ確認事項が揃ったときだけ。共通本文 §1 の「作成の明示依頼は包括許可ではない」を守る。
- 作業中に見つけた Issue 起票と無関係な指摘は直さず、handoff へ1行で記録するに留める。


### 専用 Bash command gate の許可契約（Claude Code 固有・正本）

実装正本は `.claude/hooks/agent-command-gate.sh` の `gh_create_issue_violation`。
**この節をエージェント向けの許可・拒否一覧の唯一の置き場**とし、他の rules/README
には要約と本節への参照だけを置く。以下の「allow」は *gate の構文判定* を通る意味であり、
GitHub CLI の実行成功・実在する Project / Issue・権限を保証しない。記載のない subcommand・
flag・shell command はすべて拒否する。gate の変更を伴う許可拡大はオーナーの明示判断を要する。

**共通の境界**

- checkout の `origin` が認識可能な GitHub repository でなければ全 Bash コマンドを拒否する。
  `GH_REPO`／`GH_HOST` に不一致があっても拒否する。
- `gh --repo OWNER/REPO <subcommand>`／`gh -R OWNER/REPO <subcommand>` のように、
  `--repo/-R` は**subcommand より前**に置く。`gh issue create` **だけ**は
  `gh issue create ... --repo OWNER/REPO` という末尾指定も許可される。
  `--repo=...`／`-ROWNER/REPO` 形式も target 一致が必要。
- `gh api` の REST endpoint と `project item-add --url` も target repository に一致すること。
  任意の `--repo` 指定だけでは許可されない。
- shell のパイプ、連結、リダイレクト、展開、代入、`env`、未許可 executable は拒否。
  `gh` の他の global option も拒否。読み取り専用という理由だけでは許可にならない。

**許可された subcommand と値フラグ**（列挙外のフラグは拒否。位置制約と条件は上記および後述）。

<!-- gh-create-issue-gate-allowlist:start -->
| subcommand | 許可フラグ | 補足 |
|---|---|---|
| `gh issue list` | `--state` `--search` `--limit` `--json` `--jq` `--assignee` `--label` `--milestone` | 読取 |
| `gh issue view` | `--json` `--jq` `--comments` | 末尾 `--repo` は拒否 |
| `gh issue create` | `--title` `-t` `--body-file` `-F` `--label` `-l` `--assignee` `-a` `--milestone` `-m` | `--repo/-R` の末尾指定も可。作成は mode=create のみ |
| `gh repo view` | `--json` `--jq` | 読取 |
| `gh label list` | `--limit` `--search` | `--json` と末尾 `--repo` は拒否 |
| `gh project list` | `--owner` `--format` | 読取 |
| `gh project view` | `--owner` `--format` `--json` `--jq` | 読取 |
| `gh project field-list` | `--owner` `--format` | `--limit` は拒否 |
| `gh project item-list` | `--owner` `--format` `--query` | `--jq` は拒否 |
| `gh project item-add` | `--owner` `--project-number` `--project-id` `--url` | target Issue URL をちょうど1個必須。 `--format` は拒否 |
| `gh project item-edit` | `--id` `--project-id` `--field-id` `--text` `--number` `--single-select-option-id` `--date` `--iteration-id` | `--id`/`--project-id`/`--field-id` を各1個必須。live item と親 Project の照合必須 |
| `gh api` | 下記 API 専用規則を参照 | GitHub API の汎用 write は拒否 |
<!-- gh-create-issue-gate-allowlist:end -->

**`gh api` に固有の許可形**

- REST GET/HEAD：`repos/<target>/...` に限定し、`--method/-X`、
  `--jq/-q`、`--paginate`、`--slurp` のうち gate が認める読取オプションのみ。
  `-F/-f/--field/--raw-field` による field 指定はこの経路では拒否。
- GraphQL 読取：`gh api graphql -F 'query={ viewer { login } }'` のように、
  **読取 query を1個だけ** field として指定。`-F/-f/--field/--raw-field`、
  `--method/-X`、`--jq/-q` だけが対象。`@file`、mutation、余計な field は拒否。
- REST write：`POST repos/<target>/issues/N/dependencies/blocked_by` に
  `issue_id=<正整数>` 1個、または
  `POST repos/<target>/issues/N/sub_issues` に `sub_issue_id=<正整数>` 1個だけ。
  `-F/-f/--field/--raw-field` の field 指定を使用できるが、書込時は
  method と field 以外のオプションを拒否。implicit POST も同じ条件。
- `gh project item-edit` は live GraphQL が target repository の Issue と指定 Project を
  確認できるときだけ通す。`Status=Done`、metadata 取得失敗、
  不整合・不明 option・重複した single-select option は拒否。
  Bash gate の allow と実際の Project 編集権限は別条件。

**許可された git 形**（これ以外は拒否）：`git branch --show-current`、
`git remote -v`、`git remote get-url origin`、`git status --short`、
`git status --short --branch`。`git remote`（引数なし）・`git ls-files` は拒否。

**gate allow/deny 実行例**。全行を `tests/unit/test_gh_create_issue_gate_contract.py` が
本物の gate に通して判定する。これは**コマンドを実行するテストではなく、PreToolUse 判定のテスト**。
`item-edit` の live 成功・失敗は既存 `test_agent_command_gate.py` の fixture テストが検証する。

<!-- gh-create-issue-gate-cases:start -->
| 判定 | Bash へ渡すコマンド例 | 境界 |
|---|---|---|
| allow | `gh issue list --state all --json number,title` | list |
| allow | `gh issue view 12 --json title,labels` | view |
| allow | `gh issue create --title x --body-file tmp/_handoff/gh-create-issue--a.body.md` | create |
| allow | `gh issue create --title x --repo hiratashinnya/review-system --body-file tmp/_handoff/gh-create-issue--a.body.md` | create 末尾 repo |
| allow | `gh --repo hiratashinnya/review-system label list --limit 100 --search area` | global repo |
| allow | `gh repo view --json nameWithOwner` | repo |
| allow | `gh label list --limit 100` | label |
| allow | `gh project list --owner hiratashinnya --format json` | project list |
| allow | `gh project view 3 --owner hiratashinnya --format json` | project view |
| allow | `gh project field-list 3 --owner hiratashinnya --format json` | field-list |
| allow | `gh project item-list 3 --owner hiratashinnya --format json --query status:Todo` | item-list |
| allow | `gh project item-add --owner hiratashinnya --project-number 3 --url https://github.com/hiratashinnya/review-system/issues/12` | item-add |
| allow | `gh api repos/hiratashinnya/review-system/issues?state=open` | REST GET |
| allow | `gh api --method HEAD repos/hiratashinnya/review-system/issues` | REST HEAD |
| allow | `gh api graphql -F 'query={ viewer { login } }'` | GraphQL read |
| allow | `gh api --method POST repos/hiratashinnya/review-system/issues/12/dependencies/blocked_by -F issue_id=13` | relation write |
| allow | `gh api --method POST repos/hiratashinnya/review-system/issues/12/sub_issues -F sub_issue_id=13` | sub-issue write |
| allow | `git branch --show-current` | git |
| allow | `git remote -v` | git |
| allow | `git remote get-url origin` | git |
| allow | `git status --short` | git |
| allow | `git status --short --branch` | git |
| deny | `gh label list --json name` | 未許可 flag |
| deny | `gh label list --repo hiratashinnya/review-system` | repo 指定位置 |
| deny | `gh project field-list 3 --owner hiratashinnya --limit 100` | 未許可 flag |
| deny | `gh project item-list 3 --owner hiratashinnya --format json --jq .` | 未許可 flag |
| deny | `gh project item-add --owner hiratashinnya --project-number 3 --url https://github.com/hiratashinnya/review-system/issues/12 --format json` | 未許可 flag |
| deny | `gh project item-edit --id PVTI_x --project-id PVT_project --text x` | 必須 field-id 欠落 |
| deny | `gh issue view 12 --repo hiratashinnya/review-system --json number` | repo 指定位置 |
| deny | `git ls-files` | git 限定形以外 |
| deny | `git remote` | git 限定形以外 |
| deny | `gh issue comment 12 --body x` | 未許可 subcommand |
| deny | `gh label create x` | 未許可 subcommand |
| deny | `gh api --method POST repos/hiratashinnya/review-system/issues/12/comments -F body=x` | 未許可 API write |
| deny | `gh api graphql -F 'query=mutation { createIssue(input: {}) { issue { id } } }'` | GraphQL mutation |
| deny | `gh api graphql -F query=@mutation.graphql` | GraphQL file |
| deny | `gh --repo other/repo issue list` | 別 repository |
| deny | `gh project item-add --owner hiratashinnya --project-number 3 --url https://github.com/other/repo/issues/12` | 別 repository URL |
| deny | `GH_REPO=other/repo gh issue list` | shell env 代入 |
| deny | `gh issue list; gh issue view 12` | shell 複数コマンド |
| deny | `grep x README.md` | 未許可 executable |
<!-- gh-create-issue-gate-cases:end -->
