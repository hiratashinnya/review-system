# Jev による Claude Code フック判定

Python 3.11 以降、WSL/Linux 向けの独立した stdin/stdout 判定器です。**settings.json の作成・変更、プラグイン登録、自動インストール、実セッションでの有効化は行いません。** 対応 Issue は [#572](https://github.com/hiratashinnya/review-system/issues/572) です。ローカルの Issue 本文ファイルはリポジトリへのコミットに含めません。

## オフラインで試す

リポジトリのルートから実行します。mock は標準ライブラリだけで動き、Claude Code、Skill のインストール、認証情報、API キー、外部通信は不要です。

```bash
python -m unittest discover -s tests/jev_hooks -v
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

stdout は `{"decision":"block","reason":"…AskUserQuestion…"}` になります。PreToolUse 拒否は `hookSpecificOutput.permissionDecision: "deny"` と `permissionDecisionReason`、通過は常に `{}` です。`allow` は出さず既存の権限処理を省略しません。入力・設定・保存障害は `{}`、stderr に固定の障害通知を出します。ただし `evaluator: "jev"` の必須キー欠損は設定不備として分離し、`enforce` の Stop / PreToolUse で block / deny にします。`shadow` はキー欠損でも `{}` を維持し、`missing_api_key` を監査へ残します。mock にキーは不要です。stdout は判定 JSON だけです。

## 責務と設定

| モジュール | 責務 |
|---|---|
| `__main__`, `runner` | Hook Adapter、イベント処理の調停 |
| `transcript`, `evidence` | 公開発言、ユーザー依頼、tool ID による結果の対応付け |
| `state`, `skills`, `fingerprints`, `replay` | SQLite トランザクション、Skill 前提と変更検出、重複処理 |
| `questions`, `evaluator`, `evaluator_transport` | 個別意味質問、公式 TypeSafe SDK、期限と再試行 |
| `policy` | 真偽・確信度の合成、イベント別拒否と反復制限 |
| `verification` | 検証コマンドの機械可読な終了コード receipt |
| `redaction`, `outbound_evidence`, `configuration_failure` | 外送証拠の選択、既知秘密の除去、必須キー不備の分離 |
| `audit_records`, `audit_export`, `audit_cli` | 版付き匿名監査、誤拒否レビュー、分母と拒否数の集計 |
| `skill_semantics` | R4適用・操作・検証・回復の独立した関連性質問 |

`examples/jev_hooks/config.json` が全体設定例です。`mode` は `shadow` / `enforce`、`evaluator` は `mock` / `jev`、`model`、`confidence_threshold`、`timeout_seconds`、`retries`、`max_blocks_per_rule` を変更できます。`research_tools` は運用者が確認した「許可済みかつ利用可能なツール」だけを列挙します。空なら R2 は拒否しません。実際の権限やツール可用性を自動検出するものではありません。`question_tool_available` も同じ運用上の契約です。

R1 は作業上の回答待ちと、同じ質問を AskUserQuestion で既に実行したかを別々に評価します。R2 は調査可能性、関連手段の利用可能性、実施済み調査の関連性を別々に評価します。R3 は質問前の公開説明だけを対象とします。内部思考、tool result、選択肢だけの説明、現在の tool call より後の発言は事前説明の証拠にしません。R4 は独立検査定義と対応する成功証拠をコードで検査します。

履歴が未到着・不完全・圧縮済みの場合、説明不足と断定しません。Stop の `last_assistant_message` は書き込み遅延を補います。履歴欠損時の意味判断、API 障害、不確実な回答は fail-open です。ただし、jevの必須APIキー欠損は設定不備としてenforceで拒否します。確定した R4 前提は API 障害とは分けて拒否します。

## Skill 検査定義

[サンプル](../examples/jev_hooks/skill-check.json) と [未登録の Skill 本文](../examples/jev_hooks/SKILL.md) は独自形式です。Claude Code の標準設定ではありません。`skill_path` が cwd 配下の存在するファイルに解決でき、対応する Read 成功結果を観測した場合のみ適用します。未解決・未観測なら `unknown` です。再開・圧縮後も適用状態を保持します。Skill 自動発見・自動インストールはしません。

`steps` の `kind` は `required` / `optional` / `conditional`、条件は `when.path_exists`。`evidence` は `tool` と `input` の指定キー完全一致を機械selectorとして使えます。`semantic` を宣言した手順では観測された同じtoolの実行が検査目的に関係するかを `r4_step_relevant` で個別評価します。操作の完全一致で捕捉しない同じtoolの呼び出しも `r4_operation_relevant` で検査できます。`applicability` がある場合は `r4_skill_applies`、回復宣言の意味関係は `r4_recovery_relevant` で独立評価します。高確信yesだけを採用し、unknownは意味判断による拒否・完了認証の根拠にしません。`operations` は操作ごとの `requires`、`stop_requires` は納品前条件です。条件付きの path や watch glob は対象プロジェクト内にしてください。`watch` は必須の対象コード全体を覆うよう設定してください。

`recovery` に調査など回復操作の matcher を列挙できます。step の evidence に一致する検証操作も回復扱いで前提拒否を迂回します。汎用 Bash matcher で保護する場合も検証自身を妨げません。意味上の回復と保護対象操作の両方を含む混合コマンドは、回復判定がyesでも操作前提を迂回できません。宣言された完全一致の回復操作は従来どおり許可します。サンプルは完全一致の機械契約です。意味selectorを追加する場合も、適用済みSkill、対応するPre/Post、入力対応、最新試行、成功終了コード、対象/契約fingerprintのコード条件をすべて要求します。自己申告は完了証拠になりません。Jevの意味精度と網羅的な送信操作検出は未検証です。

検証の PreToolUse で対象ファイル群とその手順の検査契約を fingerprint 化し、対応する PostToolUse 成功時にも両方が一致した場合だけ完了します。途中編集、検証後編集、evidence / watch などの契約変更、失敗・中断、自己申告、結果のない呼び出しでは完了にしません。再検証開始時は以前の成功証拠も失効し、重なる検証では最新開始の成功だけを認証します。プロセス再開をまたぐ pending を保持します。

Bash の公式応答例では終了コードが常在しません。そのためサンプルは `python -m jev_hooks.verification -- <検証コマンド>` を使い、stdout 最終行の `JEV_VERIFICATION_RECEIPT={"exit_code":0}` を検査します。ラッパー自身は実コマンドの終了コードを返します。中断なら receipt があっても無効です。単なる `PostToolUse`、空 stderr、"passed" 文字列は成功証拠にしません。正規化された fixture の数値 `exit_code` にも対応します。実行入口の tool_input は検査定義と一致させ、検証には Pre / Post / Failure イベントを順に stdin へ渡してください。

## 状態、監査と shadow 運用

既定の保存先は `~/.local/state/jev-hooks/state.sqlite3`、サンプルは `/tmp/jev-hooks-demo` です。セッション ID と正規化 cwd をハッシュして分離し、SQLite の排他トランザクションで並行イベントを直列化します。再開・重複イベントに対応し、Stop の重複でも検証進捗、現在の対象 fingerprint、条件パスの存在値を反映します。状態には本文・tool 入力・結果を保存せず、ハッシュ、手順 ID、適用状態、拒否回数などを保持します。API キーや例外本文も記録しません。設定には API キーを記載しないでください。

SQLite の `audit` は `schema_version: 1` の内容を持ち、record / request / session / turn の相関ID、イベント、R1〜R4の三値結果、候補・拒否、固定障害コード、model、質問/ルール版、遅延と履歴充足性を保存します。会話や任意の識別文字列を監査に持ち込まず、同じrequestの再送を二重計数しません。unknown、低確信、API障害、キー欠損はオーナー通知用metadataを残します。**実通知の配送先と配送処理は未結線です。** `notice_delivery: "not_connected"` は通知済みという証拠ではありません。

shadow でも同じ検査と候補計数を行い stdout は `{}` です。まず fixture を使って判定をレビューしてください。意味ルールの反復予算はユーザー turn ごとに制限し、`stop_hook_active` で同じ是正停止の再帰を通過させます。質問キャンセル後はその turn の R1/R3 を抑止します。調査可能な R2 は質問ツールが使えなくても検査します。R4 の確定した前提は予算・stop_hook_activeで迂回せず、回復操作を通します。

```bash
python -m jev_hooks.audit_cli --state-dir /tmp/jev-hooks-demo export
python -m jev_hooks.audit_cli --state-dir /tmp/jev-hooks-demo counters
python -m jev_hooks.audit_cli --state-dir /tmp/jev-hooks-demo review RECORD_ID R1 false_positive
```

`review` は既存の候補record/ruleに `positive` または `false_positive` を追加し、自由文は保存しません。`counters` はrule別のevaluations（評価分母）、candidates、denials、unknown、faults、reviewed、positive、false_positiveとunique_requestsを返します。無記名の母数を保持し、意味精度や誤拒否率をmock成功件数から推測しません。

`export` は監査とレビューの匿名metadataだけをJSON出力します。[リポジトリ内の合成export fixture](../examples/jev_hooks/audit-export.json) を計測側から参照でき、`jev_hooks.audit_export.counters(json.loads(Path("examples/jev_hooks/audit-export.json").read_text()))` でrule別分母を再計算できます。元SQLite、会話本文、tool入力、APIキーをGitへ保存しないでください。質問版とルール版は本PRで初めて `1.1` へ上げ、R4意味質問とキー欠損の拒否契約を記録します。`audit_retention` は既定10000行（1〜100000）；上限を超えた古い監査と対応reviewは削除するため、集計は保持期間内の値です。`coverage` は総監査数・保持数・削除数・旧schema除外数を、`dimensions` はmode/model/質問版/ルール版の混在を示します。期間フィルタはありません。観測窓・projectごとに専用設定とstate_dirを分け、削除済み件数を含む全期間の精度と解釈しないでください。state_dirは利用者管理下の専用ディレクトリを使い、状態の容量管理は運用側で行います。

## Jev を使う場合と意味精度の評価

明示的に利用する場合のみ仮想環境へ [依存関係](requirements.txt) をインストールし、設定を `evaluator: "jev"` にします。キーは `TYPESAFE_API_KEY` 環境変数（`api_key_env` で変更可）から読みます。**Jevモードは送信直前に選択・秘密除去した公開会話と現在turnの関連tool結果をTypeSafe外部APIへ送ります。** mockは送信しません。課金とshadow試験導入は [PR #577](https://github.com/hiratashinnya/review-system/pull/577) のオーナー決定です。本PRは実装取込みであり、settings結線、試験導入開始、通知配送、enforce移行は行いません。

SDK境界では実認証キー、`TYPESAFE_API_KEY` と `secret_env_vars` に明示した環境変数の値、credential名の構造化値、Bearer/Basic、PEM秘密鍵、既知token形式を再帰的に除去します。内部思考、秘密ファイル（`.env` / `.ssh` / `.aws` / credentials / private-key / pem等）の本文とshell出力は外送対象から外します。通常tool入力もquestions/query/pattern/url/file_path/path/globに限定し、サイズを制限します。独自の秘密値は `secret_env_vars` に環境変数名を指定してください。**未知の秘密を完全に検出する保証はありません。** この制限で必要な証拠が除外された場合はunknownが増えます。

```bash
python -m venv /tmp/jev-env
/tmp/jev-env/bin/pip install -r jev_hooks/requirements.txt
# evaluator=jev の独自設定を用意し、環境変数にキーを設定した場合のみ実行
/tmp/jev-env/bin/python -m jev_hooks.semantic_eval --config /path/to/jev-config.json
```

[注釈付き意味 corpus](../examples/jev_hooks/semantic-corpus.jsonl) には修辞、引用、任意追加提案、回答待ち、関連・無関係調査、選択肢だけの説明、履歴不明を含めています。これは小さな smoke corpus で、精度保証ではありません。live 評価は明示実行のみです。mock の制御テストと意味精度を分け、実モデルの精度・誤拒否率は未検証です。

## 判断記録と検証範囲

`jev-claude-code-architecture.html` は取得できず、設計書との照合は未実施です。ユーザー要件と公式仕様を基に、公式 SDK 0.7.2、モデル ID `jev-1.13.0`、SQLite 永続化、成功 receipt、明示した Skill 解決契約を採用しました。閾値は仮設定で校正していません。モデル API と標準ライブラリ部分を分離し、通常テストには外部通信を要求しません。

コード制御テストは各ルールの違反・非違反・unknown、拒否後回復、キャンセル、API障害、重複、保存、検証失敗・検証後/中の編集を確認します。CIは `tests/unit/`、`tests/jev_hooks/`、新設 `tests/time_fixture_lint/` をそれぞれ直接discoverし、SDK/evaluatorを含めたhook TCは `tests/jev_hooks/` に集約しています。`time_fixture_lint` はfixtureの全参照先とPython literalの両検査をこの3rootに適用します。新rootの違反canaryは修正前3失敗、修正後3成功を確認しました。

通常のmock制御テストはAPIキー、実API、Claude Code、Skillインストール不要です。`test_sdk_transport.py` とSDK外送境界の `test_safety_transport.py` は任意依存の公式SDK 0.7.2実体をHTTP mockで検査し、SDK未導入時のみskipします。CIでは固定requirementsを事前導入し、このSDK実体検査もskipせず実行します。依存取得の通信はsetup時だけです。実API、WSL実機、実Claude Codeセッション、実モデルの意味精度・誤拒否率は未検証です。既存の2026-10-05の38件成功は旧制御証跡として [レビュー履歴](verify/reports/jev-hook-review-history.md) に保全しています。

[テスト設計 TD-jev-hooks-572](verify/designs/TD-jev-hooks-572.md) と [結果・ログ](verify/reports/TR-jev-hooks-572-b7ff3e5-worktree.md) に今回の追加レビューXR-571-1〜7と失敗→修正の対応を記録します。旧F-572-001〜004と混同しません。ローカル作業treeの検証と公開headのCIを区別し、ローカル全unitは2105件を完走し11fail/1errorでした。今回のgovernance marker不一致1件を修正して12件を再検証し、残る10fail/1errorは旧HEADでも同環境で再現しました。全unit成功とは扱わず、CIは公開後に確認します。他ツールのTC移設・他workflowの固定pathsは #578 の範囲です。

## 公式資料

- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/skills
- https://docs.typesafe.ai/introduction/quickstart
- https://docs.typesafe.ai/api
- https://docs.typesafe.ai/models
- https://docs.typesafe.ai/confidence
- https://docs.typesafe.ai/model-jaggedness/jev-1.13
