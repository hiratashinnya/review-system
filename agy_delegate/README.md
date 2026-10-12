# agy 直接実行 wrapper

標準ライブラリのみ。呼出契約は [共通 skill](../.ai/skills/agy-delegate/SKILL.md)、成果検証は [共通 agent](../.ai/agents/agy-delegate.md) を正本とする。

```text
python3 -m agy_delegate inspect --workspace PATH --settings PATH
python3 -m agy_delegate run --workspace PATH --settings PATH --executable PATH --prompt TEXT --print-timeout SECONDS
```

run の追加指定は `--conversation ID`、`--writes`、`--images --brain PATH`、`--caller-stopped`。任意agyフラグ透過、検査省略、自動retryはない。promptはcallerも安全な引数配列/引用で渡す。wrapperはshellを使わずcwdをworkspaceに固定する。runの終了コードは成功候補だけ0、詳細はJSON。意味的完了は自動認定せずcompleted=false。

## 現在の停止境界

agy 1.3.3 の成功・拒否・print-timeout・クォータERRORの実測JSONを型契約とfixtureに反映した。設定の参加元・project優先には公式根拠があるが、全層の場所/形式/許可配列合成、WSL→Windows起動の証拠が揃わないため、**通常runは必ずagy未起動で停止する**。`runtime.verify_runtime` の停止は利用者フラグで解除できない。実測fixtureは正規化の証拠、合成fixture/検証関数注入はfake起動のテストであり、wrapperの実機動作の証明ではない。実測資料とレビュー済みadapterなしでテストの注入を流用しない。

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

コマンド文字列の単なる部分一致は許さず、連結/改行/置換等を除外する。パス中のapostrophe・shellメタ文字は未対応として停止する。空白/日本語pathは合成テストで確認済み。テンプレート正規表現の実機エンジン互換性、設定層、path別名/symlinkのagy内部保護は未検証。

## 会話・並列・成果

会話はworkspaceの `tmp/agy/conversation-ID.json` と束縛する。記録なし/別workspace/既失敗の継続は拒否。返却ID不一致、子プロセス例外、拒否、画像不足等の失敗で記録を失敗へ更新し、古いsuccessを再利用しない。

`runner.run_parallel(requests, max_concurrency=N)` は明示1〜8、各Resultを入力順で返す。全実行をworkspace単位で排他するため、同workspace競合はworkspace_busyとして返す。異なるworkspaceだけ並列可能。--writesはscope申告で内部操作を強制するものではない。stale lockは自動削除しない。

画像は返却IDのbrain directoryのみ、新規会話の既存directoryや継続の同一bytesを過去成果として除外し、symlinkも拒否する。実行別UUID directoryに回収する。画像bytesの意味的内容確認はcallerが行う。失敗の画像は診断限定。

CLI stdoutは応答/拒否詳細/画像pathを秘匿する。生データは実行別 `tmp/agy/RUN_ID/result.json`（0600）に保持する。ログを報告するときはcallerが秘密値を確認する。argv/環境/設定/stderr全文は保存/出力しない。run directoryは0700。実行失敗後の書込を自動rollbackしない。

`adoption.adoption_reasons` はcallerが保持した期待アンカー、観測アンカー、意味的検証実施有無、必要成果物の実在を検査する。期待値をpromptへ渡さない。前置きのみを長さで完了扱いせず、source/内容確認はagentが行う。

Claude/Codex双方の既存hookに外側wrapper起動を投入したunit testがある。agy-delegateは限定3ロール用allowlistの対象外であり、共通merge等denyは通る。内部agy操作へhookは及ばず許可設定が担う。#513停止条件の自動統合保証はなく規範とcaller_stopped申告を区別する。現在は通常run全停止が代替経路を遮断する。
