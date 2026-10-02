# Owner-facing PR blocker report

## Policy boundary

AI roles and the main context do not merge pull requests. The owner performs a manual merge after reviewing the PR and its blocker report. The repository does not change GitHub branch protection or the owner-facing GitHub UI.

Claude Code keeps native `permissions.deny` rules in `.claude/settings.json` for direct shell merge forms, global-option forms, and GitHub MCP merge tools. Codex keeps native execpolicy prefix rules in `.codex/rules/default.rules` for direct Git and GitHub CLI merge forms. The Codex GitHub connector merge tools remain disabled in `.codex/config.toml`.

Both existing `agent-command-gate` hooks also inspect shell commands for every role, including the main context. The small token scanner removes leading environment assignments and `env`, `rtk` / `rtk proxy`, `command`, `builtin`, and `exec` wrappers; it compares executable basenames, then skips known Git and GitHub CLI global options before checking the subcommand. It denies `git merge`, `gh pr merge`, and explicit command-line Git aliases whose value invokes `merge`.

The hooks inspect GitHub REST requests for pull request merge routes and deny non-read methods. For `gh api graphql`, they inspect inline query fields, file-backed query fields, and JSON input files for the `mergePullRequest` and `enablePullRequestAutoMerge` mutation fields. GET/HEAD REST requests and GraphQL reads without these mutation fields pass. An unreadable or dynamically supplied GraphQL payload is denied with an inspection reason.

The native rules are not OS-level enforcement. Codex prefix rules match only direct command prefixes, so the shell hooks cover global options, wrappers, and absolute executable paths. The hook fails closed with a reason when shell tokenization, an option, or an API payload is ambiguous. The Claude glob patterns for options before subcommands can also match a benign command when its argument text has the same word sequence as a merge invocation; this narrow risk is accepted to retain native coverage. A configured Git alias not named on the command line, an alternate command transport, or an intentionally constructed dynamic invocation remains outside this text-based boundary.

The role-specific hook rules retain their existing push, write, and review boundaries. Native settings still provide the all-role direct merge denial, while the common shell hook covers forms that the native matchers cannot express. Project rules load only when the `.codex` project layer is trusted; restart Codex after changing them. See [Codex command rules](https://learn.chatgpt.com/docs/agent-configuration/rules) for native prefix behavior.

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
