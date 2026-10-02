# Owner-facing PR blocker report

## Policy boundary

AI roles and the main context do not merge pull requests. The owner performs a manual merge after reviewing the PR and its blocker report. The repository does not change GitHub branch protection or the owner-facing GitHub UI.

Claude Code uses native `permissions.deny` rules in `.claude/settings.json` for shell commands and GitHub MCP merge tools. These rules apply to the main context and every agent. Its PreToolUse and PostToolUse hooks no longer invoke a PR merge classifier.

These command rules deny the supported command spellings covered by their patterns; they are not OS-level enforcement. Claude Code matches Bash command text, and Codex matches argument prefixes, so a different executable path or an unlisted command spelling may fall outside the rule. Do not treat these project rules as protection from a deliberately constructed alternate invocation.

Codex uses project execpolicy rules in `.codex/rules/default.rules`. Forbidden rules cover direct and RTK-wrapped GitHub CLI merge calls, local Git merge commands, and all `gh api` calls. The rule engine matches command prefixes and cannot inspect a GraphQL query loaded from a file, so denying the whole API command is required to cover REST and file-backed GraphQL requests. This also removes Codex CLI access to non-merge `gh api` operations. Project rules load only when the `.codex` project layer is trusted; restart Codex after changing them. The GitHub connector merge tools remain disabled in `.codex/config.toml`. See [Codex command rules](https://learn.chatgpt.com/docs/agent-configuration/rules) for the native rule behavior.

The role-specific command hooks retain their existing push, write, and review command boundaries. They no longer give `pr-reviewer` a special merge allowance. Native platform rules provide the all-role merge denial.

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

The former command classifier, pre-use and post-use hook, hook shell wrappers, and request-argument parser have been removed. `pr_merge_gate.gate` keeps the fresh blocker re-evaluation; `pr_merge_gate.audit` packages its evidence as a non-executable owner report. Neither module invokes a merge API.
