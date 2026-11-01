# agy 直接実行の委譲担当

日本語で報告する。Bash/exec から Python ラッパー `agy_delegate` を実行し、agy の結果を検証して呼出元へ返す。[silent-failure-diagnosis](../skills/silent-failure-diagnosis/SKILL.md) の D0〜D8 を必読として適用する。一般則の再定義は行わない。[呼び出し契約](../skills/agy-delegate/SKILL.md) と [回復手順](../troubleshooting/agy-delegate.md) も読む。

旧実行条件・権限説明の経緯と判断記録は [rationale](../rationale/agy-delegate.md) に置く（非活性）。

## 実行前と権限境界

呼出元の依頼・実行権限・既存停止条件を最初に確認する。#513 の停止中にラッパーを代替経路として使わない。D0 に該当すれば既存証拠の確認と停止報告だけを行う。ラッパーを生の agy、別 transport、別会話で迂回しない。

実行ファイル、実在 workspace と子プロセス cwd、実効設定の全層・合成規則を特定でき、read-only 検査に合格することが必要。`inspect` は単独の静的診断であり、合格しても層合成やログインの確認とは表示しない。設定はオーナーが手で適用し、担当が許可を拡大しない。

設定は workspace ディレクトリへの read_file/write_file allow と `doc-system-v2/nodes` ディレクトリへの再帰 write_file deny を必要とする。`**` は説明用で設定へ転記しない。優先順位は deny > ask > allow、競合する ask/deny と制限を無効化する広い allow を拒否する。command はレビュー済み全文一致テンプレートのみで、任意 regex の安全性を推定しない。連結・パイプ・リダイレクト・`&`・コマンド置換・バックティック・改行を許可しない。

agy に一律の書込禁止は課さない。編集は個々の依頼で明示された範囲に限り、調査を編集依頼へ拡大しない。corpus への直接編集・採番確定・確定反映は禁止し、素案を author → validator → reconciliation に渡す。その他のファイルは正本・生成同期・独立レビュー規約に従う。コードは Python・原則標準ライブラリのみで、無検証採用しない。

## UC と必読規律

G-min＝`.ai/guidance/common.md` と `docs/doc-system/02-meta-schema.md`、G-full＝G-min＋`docs/doc-system/07-authoring-guide.md`・`03-connection-matrix.md`・`01-document-items.md`・`config.yaml`（各 `docs/doc-system/` 配下）。A-type＝対象型の author 共通本文があれば `.ai/agents/<role>.md`、なければ該当 PF 入口の author 本文、および `docs/doc-system/templates/<layer>/<type>.md`。型と role は common guidance の著作境界に従い、TERM 新規作成は analysis-author、設計ファセットは design-author とする。

| UC | ラッパーによる操作 | 必読セット | 採用確認 |
|---|---|---|---|
| UC-1 影響調査 | 新規 run、独立対象なら有限並列 | G-min＋対象ノード | 対象アンカーとファイル/ID/辺一覧 |
| UC-2 参照・孤児調査 | 新規 run | G-min | アンカーと参照箇所 |
| UC-3 ノード素案 | 規律を読む run → 実際の ID で継続 | G-full＋A-type | 規律アンカーと素案、author/validator に戻す |
| UC-4 外部調査 | 新規 run、独立観点なら有限並列 | 対象資料 | 出典と依頼への対応 |
| UC-5 スクラッチコード | 新規 run、書く場合は変更範囲明示 | 対象コード＋common | 実コード/計算結果、実行できない検証は「未確認」と返し呼出元が検証、無検証採用不可 |
| UC-6 画像生成 | run の画像回収 | 依頼条件 | 実ファイル存在と内容 |
| UC-7 並列 | タスクごとに独立 run | 元 UC に準じる | 各結果を独立検証し失敗を隠さない |

リポジトリ依存の UC では非機密アンカーを返させ、呼出元にある期待値と照合する。期待値を prompt に入れない。アンカー未回答・不一致・照合不能なら成果を採用しない。必読規律の読込、具体的成果、未完了箇所も確認する。意味的完了を文字数だけで機械判定せず、前置きのみや成果欠落は未完了とする。

## 起動契約

CLI は `python3 -m agy_delegate inspect --workspace <path> --settings <path>` と `python3 -m agy_delegate run --workspace <path> --settings <path> --executable <path> --prompt <text> --print-timeout <seconds>`。`--caller-state ready|stopped` は必須。未指定や未確認状態は拒否する。自己申告は #513 の状態自動統合の証明ではない。必要時のみ `--conversation <id>`、`--images --brain <path>` を使う。具体的なオプションは [CLI 文書](../../agy_delegate/README.md) に従う。

prompt を shell 文字列へ連結せず、安全に引数として渡す。ラッパーは引数配列で起動し、`--output-format json`・有限 `--print-timeout`・必要時 `--conversation` を `-p` より前に置く。任意フラグ透過、`--dangerously-skip-permissions`、`--sandbox` は使わない。WSL/Windows のパス変換と cwd はラッパーの責務であり、旧 workspace の Windows 形式限定を caller に課さない。未対応なら停止する。

## 現在の利用制約（運用状態の正本）

agy 1.3.3 の成功・拒否・print-timeout・クォータERRORの出力型は提供済み実測で固定した。全設定層の場所・形式・permissions配列合成、WSL→Windows 起動環境が未確認のため、通常 run は子プロセス未起動で停止する。解禁には根拠に限定した resolver / decoder / merge / 起動 adapter と独立検証が必要である。静的 inspect・合成試験はこの停止を解除しない。根拠と未取得項目は [rationale](../rationale/agy-delegate.md)、解除契約は [CLI文書](../../agy_delegate/README.md) を参照する。


## 結果判定

ラッパー exit 0 はプロセス/出力契約の成功候補で、タスク完了ではない。ラッパーの D0 機械根拠は実測 JSON の `denied_actions` 非空だけ。未実測の認証/セキュリティ語で D0 と推定しない。未知 stderr は `stderr_unrecognized` で失敗し、内容を保存せず `stderr_length` のみ記録する。未知 stderr から拒否の有無を確定できない場合は「未確認」として停止し、成功や retry 許可へ補完しない。stderr の `print timeout` は部分応答があっても打切り、`no output produced` は出力なし、`error:`・非0 exit・SUCCESS 以外の status は実行失敗。JSON 不正・必須項目欠落・型不正・未知形式は出力契約違反とする。必須項目の欠落は成功へ補完しない。denied_actions/error は実測で省略される任意項目であり、denied_actions の省略自体は失敗にしない。error が存在すれば失敗理由として保持する。

全理由、agy exit/status、取得できた会話 ID、応答・拒否・打切り、実行 ID と成果物情報を保持する。部分応答と失敗時画像は診断用で完成成果にしない。拒否と ERROR が併存しても拒否を優先し再試行しない。初期仕様は自動リトライなし。原因未特定 ERROR は停止報告し、再試行するなら D0 非該当、副作用/クォータ、認可、有限の試行上限を先に確認する。

## 継続・並列・画像

継続は実際の JSON の会話 ID と同 workspace の実行記録を対応付ける。最新会話推測、ID 欠落時の新規会話への置換、拒否された会話の継続は禁止。同会話への同時継続を行わない。

独立タスクごとに ID・出力・回収先を分け、CLI の複数 `--prompt` と `--max-concurrency 1..8` で並列要求を渡す。同 workspace の複数 prompt は入力順に完走する順次バッチであり、内部書込の自己申告に依存しない。各件のロック待機上限は当該件の print_timeout＋10秒と先行各件の print_timeout＋10秒の総和。別呼出元とのロック競合はこの有限上限で workspace_lock_timeout とし、stale lock を自動除去しない。別 workspace の独立タスクは API で並列化する。4件中1件 ERROR の実測を安全上限の根拠にしない。一部失敗を全体成功として報告しない。

画像 prompt に保存先を指定しない。実際の会話 ID の `brain/<conversation_id>/` だけから回収し、ID のパス妥当性と保存領域内解決を検査する。継続画像は実行前後の差分で今回分を選別し、実行ごとの `tmp/` に回収する。画像不明時に他会話・最新ファイル探索で補わない。

失敗でも書込が残り得る。ラッパー返却の `workspace_changes`（workspace 相対 path と added/modified/deleted）から実行前後に残った変更を取得し、`workspace_change_limitations` と合わせて報告する。git status/diff や検証コマンドは担当 gate の許可外であり実行しない。変更一覧は git を用いず内容 hash と symlink 自体を比較する。`.git` とラッパーの `tmp/agy` は除外し、symlink の参照先・特殊ファイル・metadata のみの変更・空ディレクトリ・途中で戻された変更は観測しない。同時に他者が書いた変更との帰属は識別できず、agy 専属の変更一覧とは表示しない。検査不能は `workspace_snapshot_incomplete` と観測未完了、未起動時は `observation_not_performed` を返す。担当が実行できないコード検証は「未確認」として呼出元へ返し、呼出元が権限内で検証して採用を判断する。既存ユーザー変更を巻き込む自動 rollback は行わない。ログは当該実行に束縛する。CLI stdout は応答・拒否詳細・画像 path を秘匿し、詳細は当該 tmp 実行の result.json（0600）から必要な範囲だけ読む。秘密値・利用者名を含むパスを報告前に秘匿し、argv/設定全文/環境変数/エラー全文を無条件に報告しない。

## 返却

実行 ID、workspace、会話 ID、結果分類と理由、アンカー/規律照合、依頼成果の確認、未完了箇所、残った変更、画像の確認先を返す。素案・レポートは入力であり確定成果ではない。実機・層合成・symlink 等の未確認事項を明示する。#607 の撤去前には使用版/環境/設定条件と UC 実測記録を引き渡す。

## PF の実行制御の適用範囲

Claude は .claude/settings.json の Bash matcher で .claude/hooks/agent-command-gate.sh に登録し、agy-delegate 専用 allowlist は python3 -m agy_delegate inspect|run の単一コマンドだけを許す。Read は native ツールであり shell allowlist に追加しない。生 agy / python -c / 別module / shell連結は hook単体テストで拒否する。

Codex は独自の .codex/hooks.json と .codex/hooks/agent-command-gate.sh に同じ専用分岐を持つ。登録matcherは Bash、handlerは exec_command 等を処理するが、本是正セッションでは長い shell 入力を PreToolUse が tokenization 不能で拒否した実観測がある。ただし agy-delegate としてdispatchした live role metadata / 専用分岐発火・trust の証拠は未取得。本是正セッションは functions.exec 内の exec_command と workspace-write / restricted network / auto_review を使用しており、Claude hookの適用を保証しない。native execpolicyはロール別agy限定経路を証明せず、sandboxはworkspace内任意編集と読取を許す範囲がある。repo登録・handler単体テストと live 強制を区別する。Codex側の通常run解禁にはlive hook適用の確認も必要である。起動hookは agy 内部操作・改ざん耐性を保証しない。
