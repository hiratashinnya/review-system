# agy 実効設定・WSL 起動の観測記録（Issue #628）

Codex (AI) による 2026-10-22 の部分的な実測記録。受入完了・通常 run の解除を意味しない。
下段は PR #627 head `f09f3d099952e9da8293ae88da3749b2c276973e`。
個人パスは `<windows-user>`、`<linux-user>` に置換して記録する。

## 使用版と実行環境

- Linux `6.18.33.2-microsoft-standard-WSL2`、WSL distro は Ubuntu。
- Linux 側起動入口 `~/.local/bin/agy` は Windows 側 `%LOCALAPPDATA%/agy/bin/agy.exe` へのリンク。
- `agy --version`: `1.3.5`。既存 wrapper の出力契約は 1.3.3 に束縛されている。版検査を緩めていない。
- sandbox 内の Windows 実行は `UtilBindVsockAnyPort: socket failed 1`。sandbox 外の読み取り実行では版表示成功。
- 実行 workspace: `\\wsl.localhost\Ubuntu\home\<linux-user>\ws_claude\review-system\tmp\worktrees\issue-628`。

## duration 観測と受理版の未確認契約

`agy --output-format json --print-timeout 15 -p /usage` は exit 2、
`time: missing unit in duration "15"` を返した。
同じ local command の `--print-timeout 15s` は exit 0、`status: SUCCESS`、
空の conversation ID、`num_turns: 0`、token 使用量 0 を返した。
この観測は 1.3.5 に限定され、wrapper の受理版 1.3.3 の互換性証拠にはならない。
第一弾ではこの結果を転用して `s` を付けたが、R1 で無根拠な変更を取り下げた。
内部 process の数値文字列は従来の合成試験用の挙動であり、1.3.3 での受理を保証しない。
本番 runtime は `print_timeout_format_unverified` で未起動を維持する。
解除には受理版の正確な実引数と実行結果、またはその版に束縛された公式根拠が必要である。
外側 `subprocess.run(timeout=...)` は数値秒のままとする。

## 読み取りで確認した層

| 層 | Windows 実行側で確認した場所 | 観測した形式・内容 | 未証明 |
| --- | --- | --- | --- |
| global | `%USERPROFILE%/.gemini/antigravity-cli/settings.json` | `permissions.allow` 13件、ask/deny キーなし | 他層との配列合成・拒否優先 |
| project mapping | `%USERPROFILE%/.gemini/antigravity-cli/cache/projects.json` | workspace の Windows path → UUID | 未登録 workspace の選定規則 |
| project | `%USERPROFILE%/.gemini/config/projects/<UUID>.json` | `id`, `name`, `projectResources.resources[].folderUri` | permissions の格納箇所・schema |
| shared user | `%USERPROFILE%/.gemini/config/config.json` | この環境では `userSettings.remoteControlHostname` のみ | permissions の schema・適用優先順 |
| admin | Linux `/etc/antigravity/admin_settings.json` は不存在 | Linux 側の不存在だけを確認 | Windows 側の実パス・全適用源・優先順 |

`agy --output-format json --print-timeout 15s -p /permissions` は
`command.data.permissions` に `project`、`shared`、`global` の3 scope を返した。
project/shared は scope のみ、global は allow 13件。admin の不存在証明にはならない。
`/config` の `command.data.config.permissions.allow` も13件だった。
非空の複数層・重複・allow/deny 競合を観測していないため、配列合成を推定しない。

## 現環境で解除できない理由と必要条件

global には `command(git status)` と `command(codex --help)`、別 workspace の
`git pull` / `fetch` を含む事前許可がある。既存の限定テンプレート以外の許可であり、
対象 workspace の read/write 許可・corpus deny がない。
設定を変更せず通常 run を許可すると、既存の安全契約を満たさない。
必要な設定差分は、全参加層から追加の command allow を除き、対象 workspace の
`read_file`・`write_file` と限定した単一 command のみを許可し、
`write_file(<workspace>/doc-system-v2/nodes)` を deny に加えること。
実際の Windows パス表現・規則の効力を先に測定する必要がある。
既存 user 設定は自動変更していない。

`/config` の `useG1Credits` は false、`/usage` は Gemini と Claude/GPT の週次枠100%を返した。
これだけで画像生成の無課金を保証しないため、実機 UC 5種は未実施。
この段階ではモデル推論を依頼していない。

## 後続の実測案と #607 への引継ぎ

公式 `agy --help` に config/home を切り替えるオプションはない。
`--project` は既存 user/global を隔離する証明にはならない。
専用 Windows user/home または公式に確認できた隔離機構で、認証ファイルをコピーせず
専用ログインし、無課金枠と自動課金無効を確認した上で次を測定する。

1. project/shared/global/admin の各入力に識別子を置き、`/permissions` と `/config` を照合。
2. 同じ rule の重複、異なる rule、allow/ask/deny 競合を各組合せで確認。
3. cwd sentinel を別 workspace に置き、Windows 起動の cwd と URI/path を照合。
4. 影響調査・素案・外部調査・画像生成・並列の5 UC を、版・設定・使用量とともに記録。

これは実験入力の書込みを伴い、read-only 観測だけでは合成規則を証明できない。
#607 への現時点の引継ぎは「撤去不可、実機証明未完」。
#513 の corpus 保護・D0・未検証成果不採用を緩めず、設定検査は sandbox ではないという
PR #627 の制約を維持する。merge guard は意図的に赤のままである。
