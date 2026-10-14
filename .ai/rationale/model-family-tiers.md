# Issue #626 の判断・調査記録

## 凍結セット

- module: `model_policy` の policy読込／catalog取得／resolver／template準備／CI検査を分離。
- interface: JSON policy、同一surface catalog envelope、CLI check/resolve/prepare-copilot。
- protocol: Codex `login status` / `debug models`、Copilot SDK/IDE列挙またはCLI手動表示。shellを経由しない。
- persistence: policyと停止templateを追跡。具体IDは証跡と無視対象runtime生成物だけに保持。
- orchestration:全必須層を解決後に準備し、実使用IDを照合して起動。STOP時に代替しない。
- prompt: Bloom本文と共通agent本文は不変。PF wrapperに正本と準備手順を接続。
- log/version: JSON証跡にpolicy/catalog hash、取得元、観測日時、resolved IDを出力。
- test strategy: 推論や認証不要の合成一覧でminor/patch更新、major境界、層欠落、停止とCI driftを検査。

## 論点・採用案

最新はpriority順と数値版最大のどちらか。一覧priorityは推薦順で版の意味を保証しないため、
許可されたfamily/major/tier内の数値版最大を採用。数値版以外と同版複数別名はSTOPする。
major変更は正本の明示変更が必要で、自動更新に跨がせない。

Copilot model未指定はdefault継承になる。具体IDを追跡生成する案は観測したminorを恒久設定に
戻すため却下。停止template＋同じloaderディレクトリの無視対象runtime生成を採用。
追跡対象の停止flagsがPFで無視される場合まで技術的に起動禁止を保証しないため、同一surfaceの
実モデル確認と手順上のSTOPを必須とする。runtime名を分けて元templateとの同名競合を避ける。

正本のCopilot系統/majorは既存中位`claude-sonnet-5`／最上位`claude-opus-4-8`運用を保存。
この記録の具体IDは移行元の履歴であり、現行IDの規範ではない。低位の新写像は作らない。
Codex公式 `filter_by_auth` に合わせ、ChatGPT/backendは可視一覧、API認証はAPI対応のみ候補とする。
`codex login status` を同じcontextで取得し、資格情報を表示・記録せず方式だけを証跡へ残す。
認証方式不明はSTOP。API非対応の新minorをbackendで誤って除外し旧minorを選ぶことを防ぐ。
認証方式・API可否flagだけでモデル実行成功とはみなさない。
`login status` の判定は default OpenAI provider・同一設定/アカウントを前提とし、custom provider、
profile、runtime override は effective provider と一覧・認証の同一context確認まで手順上STOPとする。

## 2026-10-13 調査・実測

codex-cli 0.159.2 の `codex debug models` は成功。候補に `gpt-6.1-sol`、`gpt-6-sol`、
`gpt-6-luna` があり、数値版最大規則では top=`gpt-6.1-sol`、low/mid=`gpt-6-luna`。
`codex exec --ephemeral` smokeは環境のCODEX_HOME書込制約で初期化失敗し、モデル推論は未測定。
`debug models` 自体はcache/bundled fallbackがあり、remote live取得成功を表す証拠ではない。
Copilotの同一アカウントCLI/IDE列挙とruntime実行は本環境では未測定。

2026-10-14T01:54:39 UTC に認証方式判定を含む実装 CLI `python3 -m model_policy resolve` が exit 0 で成功。
low/mid=`gpt-6-luna`、top=`gpt-6.1-sol` を解決し、policy SHA256 は
`168d5b46190bee79e64bdcc2bd7c157b41f9a602394107ff1a008221cf8e93a5`。
catalog SHA256 は `0f45965fddad6dec25e9c766638a3f49b7a3791f934281261d51abe03be81395`、
source=`codex debug models`、surface=`cli`、auth_mode=`backend`、selection=`numeric-version-max`。
JSON証跡のローカル保存先は `/tmp/issue-626-resolved-codex.json`。
これはCLI一覧の解決実測であり、remote live取得・モデル推論実行の成功とは区別する。
実使用 ID はモデル実行なし（exec 初期化失敗）。model-free 回帰テストもモデル実行なし。

## 2026-10-14 最終ローカル検証

- 認証方式別候補・API status実文字列を含む最終全unit: 1,958件、409.899秒、成功（退役済みtransport/parserの9件skip）。
- 新規model-free回帰19件、contract_split 13件成功。モデル推論は実行していない。
- model_policy、asset_parity、guidance_sync、maintainability_lint、time_fixture_lint、diff check成功。
- 独立レビューはquoted/duplicate YAML key、runtime自己記述、Git誤追跡、認証方式別候補を是正後clean。
- 初回途中版は中止、認証是正前全unitも比較用に保持し、最終認証是正後snapshotだけを完了証跡とする。

公式資料:

- [Copilot SDK compatibility](https://docs.github.com/en/copilot/how-tos/copilot-sdk/troubleshooting/compatibility): listModels() と session.rpc.model.getCurrent()。
- [VS Code Language Model API](https://code.visualstudio.com/api/extension-guides/ai/language-model): vendor/id/family/versionでIDE側一覧を取得。
- [Custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration): model省略時default継承、disable-model-invocation/user-invocable、infer退役。
- [Codex CLI source](https://github.com/openai/codex/blob/main/codex-rs/cli/src/main.rs): run_debug_models_commandはOnlineIfUncached。
- [Codex models manager](https://github.com/openai/codex/blob/main/codex-rs/models-manager/src/manager.rs): refresh失敗時もcatalogを返す。
