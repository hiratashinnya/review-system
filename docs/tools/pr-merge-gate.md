# Owner-facing PR blocker report

## Permission boundary

AI roles and the main context do not merge pull requests. The owner reviews the pull request and its blocker report, then performs any merge manually. Repository branch protection and the owner-facing GitHub UI are outside this tool's control.

| Layer | Current coverage | Limits |
|---|---|---|
| Native controls | Claude settings and Codex rules deny direct merge command prefixes; Claude settings and Codex configuration also disable their GitHub merge tools. | Native command rules cover direct prefixes. Both shared hooks inspect global options, wrappers, API requests, and other inspectable indirect forms. |
| Shared shell hooks | Both `agent-command-gate` hooks apply the shared merge check to every role. They inspect supported global options, environment and absolute-path wrappers, RTK wrappers, REST routes, GraphQL mutations, and readable command substitutions. Read commands such as `git show merge`, `git log --grep merge`, and GitHub API GET/HEAD requests are allowed. | This is static command-text inspection, not OS-level enforcement. Git aliases, shell functions, other executables, execution inside scripts, escaped nested legacy backtick substitutions, Bash ANSI-C quoting (`$'...'`) and other quote forms where shell and static-tokenizer interpretations differ, GraphQL inline fragments containing merge mutation fields, and other intentional bypass forms are outside its guarantee. |
| Product-session evidence | Local hook tests, settings tests, and the Codex native checker provide the available evidence. | Claude's live permission engine and role dispatch in product sessions have not been measured. |
| Final enforcement | GitHub branch protection is the final enforcement layer for repository merges. | Local hooks do not control owner-selected execution paths. |
| Gated-role GraphQL files | The hooks inspect readable GraphQL mutation text. | Query text passed with `-F query=@...` is not inspected for gated roles, so rejection of non-merge mutations in this form is not guaranteed. |
| Gated-role repository option placement | `-R` and `--repo` select the repository for GitHub CLI commands. | Read commands are denied when `-R` or `--repo` follows `gh pr` immediately; place the option at the end or immediately after `gh`. |
| Main-context GraphQL writes | The gate checks GraphQL mutations that merge pull requests. | The gate covers merge denial; non-merge GraphQL mutations in the main context are out of scope. |

The hooks inspect REST pull request merge routes and readable GraphQL merge mutations. Unreadable or dynamically supplied GraphQL payloads are denied when the hooks cannot inspect them. Claude's glob patterns can match benign argument text for some GitHub forms. Codex project rules apply when the `.codex` project layer is trusted. See [Codex command rules](https://learn.chatgpt.com/docs/agent-configuration/rules).

Role-specific hook checks continue to enforce push, write, and review permissions.

## Creating a report

Run this from a checkout with GitHub read credentials:

```text
rtk python3 -m pr_merge_gate report 123 --repository OWNER/REPO --merge-method merge
```

`number` is the pull request number. `--repository` is required. `--merge-method` accepts `merge`, `rebase`, or `squash` and defaults to `merge`; choose the method the owner is considering because blocker closure evidence depends on the resulting commit message.

The command reads current GitHub state, evaluates the existing blocker policy, and re-reads an `ALLOW` candidate to confirm the same evidence remains stable. It retries unstable state up to three times and returns `ERROR/REEVALUATION_LIMIT` if it does not stabilize. API failures, malformed results, and identity mismatches fail closed.

The JSON report includes the verdict, reason, fetch time, repository and pull request identity, closing sets, findings, and the complete blocker evidence. `owner_action_required` is always true. `automatic_merge_authorized` and `merge_api_called` are always false. An `ALLOW` verdict means the report found no blocker at fetch time; it is not an execution permit.

Exit codes follow the blocker result: `0` for `ALLOW`, `10` for `BLOCK`, and `20` for `ERROR`. The command writes the machine-readable report to stdout and a one-line summary to stderr. Preserve the output if an audit record is needed.

The report is point-in-time evidence. It cannot prevent state changes between the report and the owner's manual action. The owner reviews the report and uses the GitHub UI or another owner-controlled path to merge.

## Retired components

The former command classifier, pre-use and post-use hooks, hook shell wrappers, and request-argument parser are retired. `pr_merge_gate.gate` keeps the fresh blocker re-evaluation; `pr_merge_gate.audit` packages its evidence as a non-executable owner report. Neither module invokes a merge API.

[Decision rationale](../../.ai/rationale/pr-merge-permission-settings.md)
