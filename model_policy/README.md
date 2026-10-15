# 系統・層によるモデル解決（Issue #626）

系統・major・層・Codex 予算・Copilot agent 分類の正本は
[.ai/model-policy.json](../.ai/model-policy.json) だけに置く。Bloom 12セルは
`.ai/skills/bloom-model-tier/SKILL.md` を変更せず使用する。
低位／中位／最上位は `low`／`mid`／`top` に対応する。
具体 minor ID は設定・skill・追跡対象 agent・テストの正解値に固定しない。

## Codex

`python3 -m model_policy resolve` は `codex debug models` を timeout 60秒で呼び出す。
同一 context の `codex login status` で認証方式を確認し、資格情報を表示せず証跡には方式だけを記録する。
認証方式判定の適用前提は default OpenAI provider と同一設定・アカウントでの一覧確認である。
custom provider、profile、runtime override では effective provider と一覧・認証の同一 context を
確認できるまで手順上 STOP する。provider を別の設定へ勝手に変更しない。
成功した `models[].slug` のうち `visibility: list` の項目を使い、ChatGPT/backend認証は
API非対応も候補、API key認証は `supported_in_api: true` のみ候補にする。認証方式不明はSTOP。
許可 major と層が完全一致する数値版だけを候補にし、minor／patch の数値 tuple 最大を選ぶ。
bare major は minor 0相当で、末尾ゼロは同一版。別名が同一最大版なら曖昧として STOP。
一覧順・priority・文字列辞書順で決めない。別 major・別層・preview/日付 alias へ跨がない。
取得失敗、空一覧、不正形式、全必須層のいずれか欠落、refresh error は非0で STOP。

`resolved` の対象層を session/config の `model` に指定する。予算は正本の `budgets` から
独立に `model_reasoning_effort` へ写像する。custom-agent TOML は session を継承する。
実際の session model が一致するまで起動しない。低い層や旧 major への代替は禁止する。

`debug models` は公式実装で OnlineIfUncached を使い、refresh 失敗時も cache／bundled
catalog を返し得る。stderr の model/catalog/refresh 関連の error/failed/fallback は拒否し、
PATH alias 作成失敗など一覧更新に無関係な warning は区別する。exit 0 だけで remote
live 取得や鮮度・実行権限を証明できない。出力証跡は「CLI が返した利用可能一覧」と記録する。
freshness の保証が必要な作業では CLI の取得元・cache 状態を別途確認できるまで STOP。

## Copilot の同一 surface 一覧

SDK は CLI 用 `listModels()`、IDE は
`vscode.lm.selectChatModels({vendor: 'copilot'})` の結果を使う。
機械的取得が使えない CLI では `/model` の実表示から完全な ID を転記する。
公式サイトの全体モデル表や別アカウント・別 surface の一覧を代用しない。
SDK `policy.state: disabled` と `available: false` は除外する。
UI 由来でも disabled／利用不可のモデルは `available: false` として記録する。

取得結果を次の envelope に正規化し、現在のアカウント・対象 surface で準備直前に取得する。
古い一覧の自動再利用は禁止。ID は取得結果をそのまま記録し、SDK/IDE の名称から推測しない。

```json
{
  "surface": "cli",
  "source": "sdk.listModels",
  "observed_at": "<取得日時 ISO 8601>",
  "models": [{"id": "<同一surfaceで取得したID>", "available": true}]
}
```

IDE の source は `vscode.lm.selectChatModels`、手動 CLI は `/model`。
手動 CLI は `manual_reason` に SDK 等の機械的取得が使えなかった具体理由を非空文字列で記録し、証跡へ保持する。
`python3 -m model_policy prepare-copilot --surface cli --catalog <一覧.json>` を実行する。
全必須層を解決してから `.github/agents/runtime-<name>.agent.md` を生成する。
runtime ファイルは gitignore 対象で、loader discovery の既存ディレクトリに置く。
共通本文の相対リンクは同じディレクトリなので維持される。元 template と別名にして優先順位競合を避ける。
起動先には evidence の `agents` にある runtime 名を指定する。

追跡対象 template は `disable-model-invocation: true` と `user-invocable: false` で停止する。
model 未指定が default を継承するため、そのまま起動しない。生成物を明示選択し、呼び出す
著作・検証・反映などの役割名も runtime 名へ読み替える。起動時のモデル表示を resolved と照合する。
実行 surface が model や停止 flags を無視する場合、その surface の委譲は STOP し、別モデルで続けない。
SDK では `session.rpc.model.getCurrent()` で確認可能。IDE は実際のモデル選択表示を記録する。
本環境では Copilot ログイン／flags enforcement／runtime 実行を実測していない。

## 証跡・検証

CLI の JSON 出力を PR／handoff／実測を伴う TD/TR に保存・参照する。最低限、policy hash、
取得方法、surface、観測日時、catalog hash、数値版最大という選定規則、層ごとの resolved ID、
実際に使った ID、実行確認の有無・結果を記録する。具体 ID は実測証跡として記録できる。
準備済み ID と実使用 ID が異なれば fallback／降格として STOP。model-free テストは
モデル推論を呼ばず selector／候補／制約を検証するため、TD/TR に実使用 ID は「モデル実行なし」と記す。

`python3 -m model_policy check` は正本参照、ID固定、template停止 flags、agent一覧を検査する。
template frontmatter は単純なキー・引用済み description・tools リストに限定し、quoted key、重複キー、YAML merge 等の未対応形式は STOP する。
全 unit tests と asset-parity CI で実行し、guidance は既存 `guidance_sync` で生成する。

公式根拠と判断記録は [.ai/rationale/model-family-tiers.md](../.ai/rationale/model-family-tiers.md) を参照。
