# Jev による Claude Code フック判定

Python 3.11 以降、WSL/Linux 向けの独立した stdin/stdout 判定器です。**settings.json の作成・変更、プラグイン登録、自動インストール、実セッションでの有効化は行いません。** Issue 本文はチャットで提示し、リポジトリへのコミットには含めません。GitHub API が 403 を返したため、Issue は作成できていません。

## オフラインで試す

リポジトリのルートから実行します。mock は標準ライブラリだけで動き、Claude Code、Skill のインストール、認証情報、API キー、外部通信は不要です。

```bash
python -m unittest discover -s tests/jev_hooks -v
python -m unittest tests.unit.test_jev_evaluator -v
python -m jev_hooks --config examples/jev_hooks/config.json < examples/jev_hooks/stop.json
python -m jev_hooks --config examples/jev_hooks/config.json < examples/jev_hooks/ask.json
```

既定は `shadow` と unknown の mock なので stdout は `{}` です。拒否を再現する設定は次のように作れます。この設定は Claude Code 標準設定ではありません。

```bash
python - <<'PY'
import json
from pathlib import Path
config = json.loads(Path('examples/jev_hooks/config.json').read_text())
config.update(mode='enforce', state_dir='/tmp/jev-hooks-enforce-demo',
              mock_answers={'r1_waiting_for_answer': True, 'r1_question_already_asked': False})
Path('/tmp/jev-hook-demo.json').write_text(json.dumps(config))
PY
python -m jev_hooks --config /tmp/jev-hook-demo.json < examples/jev_hooks/stop.json
```

stdout は `{"decision":"block","reason":"…AskUserQuestion…"}` になります。PreToolUse 拒否は `hookSpecificOutput.permissionDecision: "deny"` と `permissionDecisionReason`、通過は常に `{}` です。`allow` は出さず既存の権限処理を省略しません。入力・設定・保存障害も `{}`、stderr に固定の障害通知を出します。stdout は判定 JSON だけです。

## 責務と設定

| モジュール | 責務 |
|---|---|
| `__main__`, `runner` | Hook Adapter、イベント処理の調停 |
| `transcript`, `evidence` | 公開発言、ユーザー依頼、tool ID による結果の対応付け |
| `state`, `skills`, `fingerprints`, `replay` | SQLite トランザクション、Skill 前提と変更検出、重複処理 |
| `questions`, `evaluator`, `evaluator_transport` | 個別意味質問、公式 TypeSafe SDK、期限と再試行 |
| `policy` | 真偽・確信度の合成、イベント別拒否と反復制限 |
| `verification` | 検証コマンドの機械可読な終了コード receipt |

`examples/jev_hooks/config.json` が全体設定例です。`mode` は `shadow` / `enforce`、`evaluator` は `mock` / `jev`、`model`、`confidence_threshold`、`timeout_seconds`、`retries`、`max_blocks_per_rule` を変更できます。`research_tools` は運用者が確認した「許可済みかつ利用可能なツール」だけを列挙します。空なら R2 は拒否しません。実際の権限やツール可用性を自動検出するものではありません。`question_tool_available` も同じ運用上の契約です。

R1 は作業上の回答待ちと、同じ質問を AskUserQuestion で既に実行したかを別々に評価します。R2 は調査可能性、関連手段の利用可能性、実施済み調査の関連性を別々に評価します。R3 は質問前の公開説明だけを対象とします。内部思考、tool result、選択肢だけの説明、現在の tool call より後の発言は事前説明の証拠にしません。R4 は独立検査定義と対応する成功証拠をコードで検査します。

履歴が未到着・不完全・圧縮済みの場合、説明不足と断定しません。Stop の `last_assistant_message` は書き込み遅延を補います。履歴欠損時の意味判断、API 障害、不確実な回答は fail-open です。確定した R4 前提は API 障害とは分けて拒否します。

## Skill 検査定義

[サンプル](../examples/jev_hooks/skill-check.json) と [未登録の Skill 本文](../examples/jev_hooks/SKILL.md) は独自形式です。Claude Code の標準設定ではありません。`skill_path` が cwd 配下の存在するファイルに解決でき、対応する Read 成功結果を観測した場合のみ適用します。未解決・未観測なら `unknown` です。再開・圧縮後も適用状態を保持します。Skill 自動発見・自動インストールはしません。

`steps` の `kind` は `required` / `optional` / `conditional`、条件は `when.path_exists`。`evidence` は `tool` と `input` の指定キー完全一致です。`operations` は操作ごとの `requires`、`stop_requires` は納品前条件です。条件付きの path や watch glob は対象プロジェクト内にしてください。`watch` は必須の対象コード全体を覆うよう設定してください。

`recovery` に調査など回復操作の matcher を列挙できます。step の evidence に一致する検証操作も回復扱いで前提拒否を迂回します。汎用 Bash matcher で保護する場合も検証自身を妨げません。サンプルの `git push` matcher はその文字列だけを対象とし、シェルの意味解析・あらゆる送信操作の遮断機能ではありません。

検証の PreToolUse で対象ファイル群を fingerprint 化し、対応する PostToolUse 成功時にも一致した場合だけ完了します。途中編集、検証後編集、失敗・中断、自己申告、結果のない呼び出しでは完了にしません。再検証開始時は以前の成功証拠も失効し、重なる検証では最新開始の成功だけを認証します。プロセス再開をまたぐ pending を保持します。

Bash の公式応答例では終了コードが常在しません。そのためサンプルは `python -m jev_hooks.verification -- <検証コマンド>` を使い、stdout 最終行の `JEV_VERIFICATION_RECEIPT={"exit_code":0}` を検査します。ラッパー自身は実コマンドの終了コードを返します。中断なら receipt があっても無効です。単なる `PostToolUse`、空 stderr、"passed" 文字列は成功証拠にしません。正規化された fixture の数値 `exit_code` にも対応します。実行入口の tool_input は検査定義と一致させ、検証には Pre / Post / Failure イベントを順に stdin へ渡してください。

## 状態、監査と shadow 運用

既定の保存先は `~/.local/state/jev-hooks/state.sqlite3`、サンプルは `/tmp/jev-hooks-demo` です。セッション ID と正規化 cwd をハッシュして分離し、SQLite の排他トランザクションで並行イベントを直列化します。再開・重複イベントに対応し、Stop の重複でも検証進捗、現在の対象 fingerprint、条件パスの存在値を反映します。状態には本文・tool 入力・結果を保存せず、ハッシュ、手順 ID、適用状態、拒否回数などを保持します。API キーや例外本文も記録しません。設定には API キーを記載しないでください。

SQLite の `audit` にルール ID、三値結果、confidence、固定障害コード、実応答 model、質問版、ルール版、遅延、履歴充足性を保存します。shadow でも同じ検査を行い stdout は `{}`。まず fixture を使って shadow の判定をレビューしてください。意味ルールの反復予算はユーザー turn ごとに制限し、`stop_hook_active` で同じ是正停止の再帰を通過させます。質問キャンセル後はその turn の R1/R3 を抑止します。調査可能な R2 は質問ツールが使えなくても検査します。R4 は予算・stop_hook_active による迂回を許さず、回復操作を通す方針です。

state_dir は利用者管理下の専用ディレクトリを使用してください。状態と監査は自動削除しません。長期利用時の容量管理は運用側の責務です。秘密を含む設定 ID や手順 ID は使わないでください。

## Jev を使う場合と意味精度の評価

明示的に利用する場合のみ仮想環境へ [依存関係](requirements.txt) をインストールし、設定を `evaluator: "jev"` にします。キーは `TYPESAFE_API_KEY` 環境変数（`api_key_env` で変更可）から読みます。**Jev モードでは正規化した会話とツール結果が TypeSafe 外部 API へ送られます。** mock は送信しません。

```bash
python -m venv /tmp/jev-env
/tmp/jev-env/bin/pip install -r jev_hooks/requirements.txt
# evaluator=jev の独自設定を用意し、環境変数にキーを設定した場合のみ実行
/tmp/jev-env/bin/python -m jev_hooks.semantic_eval --config /path/to/jev-config.json
```

[注釈付き意味 corpus](../examples/jev_hooks/semantic-corpus.jsonl) には修辞、引用、任意追加提案、回答待ち、関連・無関係調査、選択肢だけの説明、履歴不明を含めています。これは小さな smoke corpus で、精度保証ではありません。live 評価は明示実行のみです。mock の制御テストと意味精度を分け、実モデルの精度・誤拒否率は未検証です。

## 判断記録と検証範囲

`jev-claude-code-architecture.html` は取得できず、設計書との照合は未実施です。ユーザー要件と公式仕様を基に、公式 SDK 0.7.2、モデル ID `jev-1.13.0`、SQLite 永続化、成功 receipt、明示した Skill 解決契約を採用しました。閾値は仮設定で校正していません。モデル API と標準ライブラリ部分を分離し、通常テストには外部通信を要求しません。

コード制御テストは各ルールの違反・非違反・unknown、拒否後回復、キャンセル、API 障害、重複、保存、検証失敗・検証後/中の編集を確認します。公式 SDK 実体を用いた `tests.unit.test_jev_sdk_transport` も HTTP mock で検証します。実 API、WSL 実機、実 Claude Code セッション、実 Skill の自動解決は未検証です。ローカル全 unit suite は未実行ですが、是正前 head の CI 全3 checks は成功しています。是正後 head の CI は別途確認します。[レビュー是正記録](../docs/jev-hook-review.md) に境界条件と回帰テストを残します。

## 公式資料

- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/skills
- https://docs.typesafe.ai/introduction/quickstart
- https://docs.typesafe.ai/api
- https://docs.typesafe.ai/models
- https://docs.typesafe.ai/confidence
- https://docs.typesafe.ai/model-jaggedness/jev-1.13

最終オフライン検証（2026-10-05）: `python -m unittest tests.unit.test_jev_core tests.unit.test_jev_evaluator tests.unit.test_jev_sdk_transport -v` は SDK 0.7.2 導入済み一時 venv で **35 件すべて成功、skip なし**。maintainability lint は violations=0（既存 accepted_debt=136）。前回の手動 stdin では shadow `{}`、Stop block、PreToolUse deny の JSON と終了コード 0 を確認しました。
