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

## 設定層の根拠と限定cohort（§6）

通常runは、内部校正workerが発行したprivate cohort proofと同じsnapshotだけを受理する。globalは公式optional schemaを厳密にdecodeし、project/sharedは一般schemaを推測せず、明示default-cli-projectの3scope表示で空を確認した全file fingerprintへ限定する。変更・未知snapshot・不正JSON・symlink・追加allow/askは停止する。Request.settingsは人工の論理templateであり、実globalへの束縛やproofの代わりにならない。

`Request.permission_root`は省略時workspace。明示する場合もcanonicalな非symlink directory配下のworkspaceだけを受け、内部校正proofがworkspaceとrootを別々に束縛する。論理templateは同じraw bytesのSHA-256で独立束縛し、native globalのhashで代用しない。論理allow/ask/commandはrootのexact集合を維持し、追加denyはroot内の既知literal子corpusだけを認める。実nativeはfile-onlyの2allow・ask空・各corpusと固定全command denyを同一生成元で検査する。

workspaceは引き続きcwd・lock・差分・会話保存の単位である。同workspaceのbatchは逐次、異なるworkspaceが祖先関係なら全件未起動で拒否し、非重複子だけ既存poolで並列実行する。会話summaryのroot欠落・不一致は推定移行せず拒否する。共有root内の完全隔離や全変更の実行者帰属は保証しない。

検証済みterminalの5整数token使用量は`Result.usage`とresult.jsonへ保持する。不正/未観測は`None`であり、ゼロ使用とは区別する。

支持する実globalはfile-onlyである。native表記のread_file/write_fileだけをallowし、corpus writeと全commandをdenyする。論理templateの限定Get-ChildItem allowより厳しいsubsetであり、一覧commandが実機で許可済みとは宣言しない。未知native ruleを既知として受理せず、file-onlyの制約を越えるUCは成功扱いしない。

proofは固定UID homeの0700/0600内部stateに保存し、期限・source集合・OS/user/home・canonical exe/hash・workspace入力projection・明示selector・global/project/shared bytes/ACL/ownerを照合する。通常runにproof path/manifest/verified flagを注入する入口は無い。Windowsのread-only helper子とagy子を区別し、proof欠落やoffline不正は全子0、Windows事実の差異はagy version/model0で停止する。排他待機後と版照会後にも再照合する。

native cwdの根拠は、本番WSL Pythonから同exeを起動して相対secret anchorを取得したwitnessである。PS Get-Location等の値で代用しない。native path欄は実入力の射影であり、新たなOS cwd観測を装わない。子だけのauto-update無効化、JSON/duration引数とdefault-cli-projectを固定する。

ProgramDataのadmin gateway candidate不存在と、ownerが証言する個人/組織accountの適用範囲を分ける。認証fileからaccount変更を検出しない。account変更時の再校正はownerの運用契約であり、未回答や未支持の管理policyを空と推測して発行しない。

既定の校正/5UCは承認済みtemporary保全sessionでsafe設定を保持し、その間だけproofを発行・使用してfinally元へ復元する。元snapshotへ戻ればproofはhash不一致で自然失効する。恒久設定変更や原rawの新永続backupを前提にしない。出版のcommitpointとdurability warning、残余制約は[cohort判断](../docs/methods/agy-runtime-cohort-628.md)を参照する。

## 実測出力契約（1.4.8正常JSON・1.3.3異常履歴）

必須項目は status / conversation_id / response（文字列）、duration_seconds（boolを除く有限非負数）、num_turns（boolを除く非負整数）、usage（input_tokens / output_tokens / thinking_tokens / cache_read_tokens / total_tokens の5キー、boolを除く非負整数）。token間の算術関係は推測しない。

denied_actionsとerrorは実測で省略される任意項目。denied_actionsがある場合は配列、各要素はaction/display_nameの2キーと非空文字列。errorがある場合は文字列で、停止理由と診断記録に保持する。未知キー・型・非標準数値・重複キーは拒否する。statusがSUCCESSでもstderrのtimeout/error/未知内容や非0exitを優先する。空IDは継続や画像回収に使えず失敗とする。

1.4.8の秘匿済み正常schemaは tests/fixtures/agy_delegate/1.4.8/success-shape.json、旧異常履歴は tests/fixtures/agy_delegate/1.3.3/ に保存。/usageは完全JSONが提供されていないためfixture化せず、空ID/追加commandの失敗を合成境界テストで確認する。実測で未提供の成功形式を推測して受理しない。

## 許可テンプレート

`permissions.expected_rules(Path(workspace))` が単一のレビュー対象テンプレートを返す。read_file/write_fileはresolved workspace全体、denyは `workspace/doc-system-v2/nodes` のディレクトリ指定（globなし）。commandは `Get-ChildItem -Name '<workspace>'` の厳密全文一致だけ。設定の追加キー/追加rule/ask/広いallow/必要rule欠落は拒否する。

コマンド文字列の単なる部分一致は許さず、連結/改行/置換等を除外する。パスは ASCII 英数字・空白・/_.:-・ひらがな/カタカナ/漢字の許可集合のみ。引用符（Unicode引用符も含む）・タブ・括弧・%等は停止する。空白/日本語pathは合成テストで確認済み。テンプレート正規表現の実機エンジン互換性、設定層、path別名/symlinkのagy内部保護は未検証。

## 会話・並列・成果

会話はworkspaceの `tmp/agy/conversation-ID.json` と束縛する。記録なし/別workspace/既失敗の継続は拒否。返却ID不一致、子プロセス例外、拒否、画像不足等の失敗で記録を失敗へ更新し、古いsuccessを再利用しない。

CLIで --prompt TEXT を複数指定し、--max-concurrency 1..8 を必須指定する。複数promptと会話継続の併用は拒否する。各結果は入力順にJSON行で返す。API run_parallel も同じ有限上限を使う。同workspace複数promptは入力順の順次バッチで、各件のロック待機上限は当該件のprint_timeout＋10秒と先行各件のprint_timeout＋10秒の総和。別workspaceの制御APIは有限並列だが、現在の支持cohortは単一Wであり、別W同時実行はまだ実機認定していない。競合時のtimeoutは workspace_lock_timeout。stale lock は自動削除しない。Issue #606 の並列契約 の書込限定直列化との差分は rationale に記録する。

画像は返却IDのbrain directoryのみ、新規会話の既存directoryや継続の同一bytesを過去成果として除外し、symlinkも拒否する。実行別UUID directoryに回収する。画像bytesの意味的内容確認はcallerが行う。失敗の画像は診断限定。

CLI stdoutは応答/拒否詳細/画像pathを秘匿する。生データは実行別 `tmp/agy/RUN_ID/result.json`（0600）に保持する。ログを報告するときはcallerが秘密値を確認する。argv/環境/設定/stderr全文は保存/出力しない。run directoryは0700。実行失敗後の書込を自動rollbackしない。

成果の採用判断は呼出agentの契約として実施する。未接続の公開 adoption API は撤去し、期待アンカー・内容・成果物の検証は agent 正本に従う。全層監査は runtime.verify_runtime から呼ばれ、支持cohortが発行されていない場合は未確認理由を保持する。

版確認は固定project付き--versionを引数配列で渡し、exit0・stderr空・stdout完全一致1.4.8のみ受理する。未知形式/版違いはprompt0。使用版は結果と実行記録へ保存する。デフォルトClaude Sonnet 4.6 (Thinking)で実file読取/許可先writeとactualWSL相対解決を観測した。保護file不変は確認したがengine write試行/拒否は直接未観測であり、拒否成功と偽認定しない。現版5UC完了は別途実機検証する。

未実測の authentication / unauthorized / security denied を D0 語として固定しない。D0の機械根拠は実測 denied_actions。未知stderrのみでも失敗、全stderrは内容を保存せず stderr_length を実行記録へ残す。既知異常と未知内容が混在しても長さは残る。

会話記録には継続判定用の実行/会話ID・workspace・classification・reasons・exit/status・拒否・打切りだけを持ち、response/error/artifact全文は実行別result.jsonだけへ保存する。記録はos.open(mode=0600, O_NOFOLLOW)で作成し、既存ファイルも書込前に0600へ制限する。

PFの制御範囲とlive未検証事項は [agent正本](../.ai/agents/agy-delegate.md#pf-の実行制御の適用範囲) を参照する。

workspace_changes はgit不要の実行前後比較で、workspace相対pathとadded/modified/deletedをCLIと実行記録へ返す。workspace_change_limitationsも必ず併記する。agy以外の同時変更の帰属、途中で戻した変更、metadataのみ・空ディレクトリ、symlink参照先、特殊ファイルは観測できず、.gitとwrapper自身のtmp/agyを除外する。読取不能はworkspace_snapshot_incomplete、未起動はobservation_not_performedであり空一覧を「変更無し」と認定しない。担当がgate内で実行できないコード検証は「未確認」と返し、呼出元が検証して採用を判断する。
