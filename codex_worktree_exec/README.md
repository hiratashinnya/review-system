# `codex_worktree_exec` — Codex を自分の worktree で実行者として起動する

Claude Code の工程ロールと `issue-fixer` が、自分の linked worktree で元ロールの権限を維持して
Codex を起動する `codex exec -C <worktree>` の薄いラッパー（#538、#371）。

```
python3 -m codex_worktree_exec --role <自ロール> -C <自分の worktree ルート> --prompt-file <依頼文> --output-file <最終応答> --model <モデル> --reasoning-effort <low|medium|high|xhigh|max> [--timeout-seconds <1〜3600>]
```

契約（検査の順序と識別子・permission profile・設計の暫定決定・既知の限界）は
[`docs/methods/codex-workspace-binding.md`](../docs/methods/codex-workspace-binding.md) を正とする。

## モジュール

| モジュール | 責務 |
|---|---|
| `roles.py` | 著作・read-only・fixer の起動対象ロール。両PFのcommand hookも読む |
| `arguments.py` | 引数の検査と `ExecRequest` の組立て |
| `request.py` | 検査済みの起動要求（データだけ） |
| `nesting_guard.py` | Codex の内側からの再帰起動の拒否 |
| `worktree_binding.py` | `-C` が呼び出し元自身の linked worktree であることの確認 |
| `profile_pin.py` | `.codex/config.toml` が `origin/main` の版と同一であることの確認 |
| `project_trust.py` | main checkout が Codex で trust 済みであることの確認 |
| `prompt_files.py` | 依頼文の読込みと最終応答の書き先の確認 |
| `invocation.py` | `codex exec` の argv と前置き付き依頼文の組立て |
| `launcher.py` | `codex exec` の起動、終了コードの透過、timeout |
| `cli.py` | 検査を順に通して起動する入口 |
| `artifact_binding.py` / `initial_binding.py` | 信頼callerの期待値、committed artifact、初回Issue snapshotの束縛 |
| `committed_artifact.py` / `source_snapshot.py` | commit済み入力とsource snapshotの確認 |
| `adviser_request.py` / `adviser_capture.py` | 相談入力・予算と完全回答・trusted使用量の確認 |

profile の生成・digest 検査・bwrap・台帳連携は持たない。区分は
`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の汎用開発ハーネスである。

`issue-fixer` 以外は `--binding-file <信頼callerのJSON>` が必須。入力artifactのbytes digestと
envelopeのinput digestを分け、expected値をartifactからコピーして補完しない。
著作ロールはworkspace編集、調査・レビュー・adviserはread-only profileを使う。
全ロールでnetworkと認証情報を拒否し、commit/pushは呼び出し側Claudeの許可ロールだけが行う。
origin/mainとのprofile pinは維持するため、未merge profileの実起動は拒否される。
新工程のnative dispatchはmanifestでunavailableのまま保持し、同一worktree継承のowner判断と
ロール別実測が揃うまで有効にしない。拒否を成功したdispatchとして報告しない。
