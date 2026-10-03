# Owner-facing PR blocker report

## Permission boundary

AI roles and the main context do not merge pull requests. The owner reviews the pull request and its blocker report, then performs any merge manually. Repository branch protection and the owner-facing GitHub UI are outside this tool's control.

Claude Code's `.claude/settings.json` denies direct shell merge forms and GitHub MCP merge tools. Codex's `.codex/rules/default.rules` denies direct command prefixes, and `.codex/config.toml` disables the GitHub connector merge tools.

Both `agent-command-gate` hooks inspect shell commands for every role. They compare Git and GitHub CLI executable basenames, skip supported global options, and deny direct merge commands and merge API operations. When the executable cannot be identified but a later Git or GitHub merge command is present, the hook denies the command. Read commands such as `git show merge`, `git log --grep merge`, and GitHub API GET/HEAD requests are allowed.

The hooks inspect REST pull request merge routes and GraphQL merge mutations, including file-backed request bodies. An unreadable or dynamically supplied GraphQL payload is denied because it cannot be inspected. Claude's glob patterns can match benign argument text for some GitHub forms. The hooks inspect command text and are not OS-level enforcement; Git aliases and execution paths outside the shell hook are not covered by this boundary.

Role-specific hooks continue to enforce push, write, and review permissions. Codex native prefix rules cover direct command prefixes; the local hook checks global options, wrappers, and absolute executable paths. Codex project rules apply when the `.codex` project layer is trusted. See [Codex command rules](https://learn.chatgpt.com/docs/agent-configuration/rules).

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
