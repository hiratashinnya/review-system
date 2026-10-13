# agy 直接実行 wrapper

標準ライブラリのみ。呼出契約は [共通 skill](../.ai/skills/agy-delegate/SKILL.md)、成果検証は [共通 agent](../.ai/agents/agy-delegate.md) を正本とする。

```text
python3 -m agy_delegate inspect --workspace PATH --settings PATH
python3 -m agy_delegate run --workspace PATH --settings PATH --executable PATH --prompt TEXT --print-timeout SECONDS --caller-state ready
```

`--caller-state ready|stopped` は必須で、未指定は拒否。run の追加指定は `--conversation ID`、`--images --brain PATH`。任意agyフラグ透過、検査省略、自動retryはない。promptはcallerも安全な引数配列/引用で渡す。wrapperはshellを使わずcwdをworkspaceに固定する。runの終了コードは成功候補だけ0、詳細はJSON。意味的完了は呼出agentが確認し、固定completed項目は公開しない。

## 現在の停止境界

運用状態の正本は [agent の現在の利用制約](../.ai/agents/agy-delegate.md#現在の利用制約運用状態の正本)。本書は CLI と停止契約を記述する。

`inspect` は#575の `settings.json` のpermissions.allow/ask/denyをread-only検査する。静的合格でも実効設定・ログイン・隔離を保証しない。適用はオーナーが手で行う。

## 設定層の根拠と解除条件（§6）

公式 [CHANGELOG](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md) の1.0.12は global `~/.gemini/antigravity-cli/settings.json` と projects `~/.gemini/config/projects/`、project設定優先を示す。1.0.5は project・Antigravity共有user・CLI settings.jsonのpermissions merge参加を示す。1.0.4の `cache/projects.json` はworkspace対応情報であり許可設定層として加えない。project優先は、permissions配列を置換する/和集合にする証拠ではない。adminの `/etc/antigravity/admin_settings.json` は提供済みexe文字列の候補だけで、公開schema・優先順の証明ではない。

`runtime.resolve_settings_layers` はこれらの境界を理由別STOPで保持する。`--settings`の任意pathだけではglobalへの束縛を証明できない。projectファイル名/スキーマとworkspace対応、共有userの場所/スキーマ、adminの適用有無/存在時優先、permissionsの配列合成は未特定。productionは実機探索も未確認層の読取もせず停止する。認証ファイルは検査対象に含めない。場所の推測や利用者manifest/verifiedフラグの入口は追加しない。

内部 `settings_layer_types` と `settings_layers.inspect_layer_resolution` は、根拠取得後のレビュー済みadapterが渡す全参加元のread-only監査用境界。全4参加元の識別/明示的不存在確認、schema decoder、全層読取を必要とする。不明/一部未読/形式不正は停止し、読取エラーを不存在に変えない。既知pathのlstatでFileNotFoundErrorになった明示的不存在だけを区別する。adminが存在する場合は優先根拠も必要である。層構成には認証情報や対応cacheを混ぜない。

許可監査は各層のallow/ask/denyを保守的に集め、deny/askを他層allowで消さず、未承認追加ruleとcorpus deny欠落を検出する。この集約は実際のmerge規則の実装ではなく、監査合格でも実効設定の合格を示さない。schema decoderはfixture固有の偽物だけをテストし、実際のproject/shared/admin schemaを固定していない。runtimeは監査合格でも `settings_permission_merge_unverified` と起動環境STOPを維持する。

実機の通常runを起動可能にするには、使用版/OS/実行ファイルに束縛された全層の場所・workspace対応・スキーマ・読取結果、admin不存在または存在時優先、permissions配列合成とdeny > ask > allowの根拠、WSL→Windows cwd/path引継ぎの証拠を揃える。その根拠に限定したresolver/decoder/実効合成/起動adapterを独立レビューし、全層検査不能・競合時未起動をfixtureで確認してから接続する。一部の層だけ読めても解除しない。D0/caller停止/成果検証と#513境界は維持する。

## 実測出力契約（agy 1.3.3）

必須項目は status / conversation_id / response（文字列）、duration_seconds（boolを除く有限非負数）、num_turns（boolを除く非負整数）、usage（input_tokens / output_tokens / thinking_tokens / cache_read_tokens / total_tokens の5キー、boolを除く非負整数）。token間の算術関係は推測しない。

denied_actionsとerrorは実測で省略される任意項目。denied_actionsがある場合は配列、各要素はaction/display_nameの2キーと非空文字列。errorがある場合は文字列で、停止理由と診断記録に保持する。未知キー・型・非標準数値・重複キーは拒否する。statusがSUCCESSでもstderrの拒否/timeout/errorや非0exitを優先する。空IDは継続や画像回収に使えず失敗とする。

実測fixtureは tests/fixtures/agy_delegate/1.3.3/ に保存。/usageは完全JSONが提供されていないためfixture化せず、空ID/追加commandの失敗を合成境界テストで確認する。実測で未提供の成功形式を推測して受理しない。

## 許可テンプレート

`permissions.expected_rules(Path(workspace))` が単一のレビュー対象テンプレートを返す。read_file/write_fileはresolved workspace全体、denyは `workspace/doc-system-v2/nodes` のディレクトリ指定（globなし）。commandは `Get-ChildItem -Name '<workspace>'` の厳密全文一致だけ。設定の追加キー/追加rule/ask/広いallow/必要rule欠落は拒否する。

コマンド文字列の単なる部分一致は許さず、連結/改行/置換等を除外する。パスは ASCII 英数字・空白・/_.:-・ひらがな/カタカナ/漢字の許可集合のみ。引用符（Unicode引用符も含む）・タブ・括弧・%等は停止する。空白/日本語pathは合成テストで確認済み。テンプレート正規表現の実機エンジン互換性、設定層、path別名/symlinkのagy内部保護は未検証。

## 会話・並列・成果

会話はworkspaceの `tmp/agy/conversation-ID.json` と束縛する。記録なし/別workspace/既失敗の継続は拒否。返却ID不一致、子プロセス例外、拒否、画像不足等の失敗で記録を失敗へ更新し、古いsuccessを再利用しない。

CLIで --prompt TEXT を複数指定し、--max-concurrency 1..8 を必須指定する。複数promptと会話継続の併用は拒否する。各結果は入力順にJSON行で返す。API run_parallel も同じ有限上限を使う。同workspace全実行は最大10秒待機の直列化で、timeoutは workspace_lock_timeout。stale lock は自動削除しない。Issue #606 の並列契約 の書込限定直列化との差分は rationale に記録する。

画像は返却IDのbrain directoryのみ、新規会話の既存directoryや継続の同一bytesを過去成果として除外し、symlinkも拒否する。実行別UUID directoryに回収する。画像bytesの意味的内容確認はcallerが行う。失敗の画像は診断限定。

CLI stdoutは応答/拒否詳細/画像pathを秘匿する。生データは実行別 `tmp/agy/RUN_ID/result.json`（0600）に保持する。ログを報告するときはcallerが秘密値を確認する。argv/環境/設定/stderr全文は保存/出力しない。run directoryは0700。実行失敗後の書込を自動rollbackしない。

成果の採用判断は呼出agentの契約として実施する。未接続の公開 adoption API は撤去し、期待アンカー・内容・成果物の検証は agent 正本に従う。全層監査は runtime.verify_runtime から呼ばれ、production resolver が未特定を返す間は未確認理由を保持する。

版確認は実行対象へ --version を引数配列で渡し、exit0・stderr空・stdout完全一致 1.3.3 のみを受理する。未知形式/版違いならprompt実行を停止し、成功した使用版は結果/実行記録の agy_version に保存する。このstrict形式は合成契約で実機未検証。版probeは runtime 検査より後であり通常停止時は呼ばれない。実測は --model gemini-3.8-flash-low 指定付き、wrapperはmodel指定を公開せずデフォルトを使う差が残る。デフォルトモデルの実機成功は未証明である。

未実測の authentication / unauthorized / security denied を D0 語として固定しない。D0の機械根拠は実測 denied_actions。未知stderrのみでも失敗、全stderrは内容を保存せず stderr_length を実行記録へ残す。既知異常と未知内容が混在しても長さは残る。

会話記録には継続判定用の実行/会話ID・workspace・classification・reasons・exit/status・拒否・打切りだけを持ち、response/error/artifact全文は実行別result.jsonだけへ保存する。記録はos.open(mode=0600, O_NOFOLLOW)で作成し、既存ファイルも書込前に0600へ制限する。

PFの制御範囲とlive未検証事項は [agent正本](../.ai/agents/agy-delegate.md#pf-の実行制御の適用範囲) を参照する。
