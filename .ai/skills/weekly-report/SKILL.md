# リポジトリ週次レポート

週次で実現した価値と運営上の課題を確認し、オープン PR を完遂した後の着手順を判断できるようにする。入力は、対象リポジトリの GitHub とローカルの読み取り、または保存済み snapshot とする。

## 定量集計

対象リポジトリのルートで実行する。Python 3.11 以降、git、GitHub への読み取り権限がある `gh` を使う。CLI はローカルの `origin` と `--repository` が指す GitHub リポジトリを照合する。

```sh
python3 -B -m weekly_report collect --repository OWNER/REPO
python3 -B -m weekly_report collect --repository OWNER/REPO --week-start sunday --week 2026-11-15
python3 -B -m weekly_report collect --repository OWNER/REPO --week-start sunday --week 2026-11-01 --weeks 4
python3 -B -m weekly_report collect --repository OWNER/REPO --week-start sunday --month 2026-11
```

- 既定は取得日を含む月曜 00:00 JST から翌月曜 00:00 JST の半開区間。`--week-start` は英語の曜日名、`--week` は対象週に含まれる日付。`--weeks N` は指定週から先の N 週、`--week` を省略すると当週を含む直近 N 週。`--month YYYY-MM` は暦月内を週単位に区切り、端の週は月境界で切る。
- `--start 2026-11-16 --end 2026-11-23` で一つの明示期間を選べる。月全体を一つの期間として集計するときもこの組を使う。オフセットを省略した日付・時刻は JST。明示期間と週・月指定は別々に使う。
- `--now` は期間イベントの基準時刻を固定する。対象期間中は途中経過とし、観測上限を含めない。一括生成で未到来の週は索引に理由を表示する。
- `--previous /path/to/snapshot.json` で前回差を出す。一括では最初の期間の前回入力として使う。期間の差分は連続した等長の期間、観測済み区間の長さ、定義と単位が一致したときに比較する。残数や検査値、親子の構成は保存された取得時点同士で比較する。比較不能の場合は根拠を示す。
- `--base-ref origin/main` は取得時点で解決する比較基準の既定。作業ツリーの検査に用いた checkout と SHA、変更の有無を記録する。基準の鮮度が必要なときは対象リポジトリの通常の fetch 手順で確認する。
- `--out /path/to/new-directory` は対象リポジトリの全作業ツリーと Git 管理領域の外にある未作成ディレクトリを指定する。省略時は、作成前に同じ条件を確認した一時領域を使う。

単票は `report.html`、`snapshot.json`、`summary.txt` を出力する。一括では `index.html` と `index.json` に全期間を並べ、観測できた各期間を `week-YYYY-MM-DD/` の単票に保存する。棒グラフには同じ定義で比較できる完了済みの7日間を使い、期間の短い行と途中週は数値・状態を示す。

### 状態を観測した時点

対象期間、イベントの観測上限、API の収集開始時刻を区別する。週末付近の AC、親子構成、PR の HEAD・CI・レビュー、未解消指摘、判断待ち、ブロックを確認する用途では、その時期に収集した snapshot を保存する。取得は逐次実行するため、開始時刻が区切りと一致しても期間末の状態は未計測とする。後日の取得は後日観測として表示する。取得前後の一覧に差がある場合は、影響する Issue または PR の状態指標を保留し、理由と取得証跡を示す。

過去期間に保存した状態を使う場合、`--observations /path/to/snapshot.json` を繰り返し指定できる。同じリポジトリ・版で対象期間が一致し、観測上限以前の同期間内で取得した候補から最新の状態を選ぶ。実測時刻と保存 snapshot の SHA-256 を確認する。期間末の状態を評価するときは、使用した観測の時刻と期間末のずれを明示する。

### 指標の根拠

- Issue の起票と完了、PR のマージを機械集計する。全マージ先・`main` 向け・その他・マージ先不明を区別し、`main` 向けマージと機能完成は別の資料で確認する。リードタイムは期間内の完了・マージを対象に中央値と根拠件数を記録する。
- 最新の Close 理由と、取得した履歴の Close・再オープンを分ける。理由の根拠が得られない履歴は理由不明とする。起票・Close・再オープンから求めるイベント上の増減と、時点間のバックログ純増を区別する。過去の残数の復元対象は、現在の一覧で取得できた Issue に限る。観測上限以降の移管が判明し当時の所属を確定できない場合は、該当番号と復元できた内訳を示し、残数は未計測とする。
- 欠陥混入率は [defect_metrics](../../../defect_metrics/README.md) の既存定義と計算を使う。`evidence.defect_metrics` に計算に用いた Issue 本文と窓の直前を含むマージ時刻を保存する。派生 Issue は本文参照とマージ時刻に基づく指標とし、マージ後に判明した実害欠陥の件数は確定分類の一次証跡に従う。
- 保守性は、`main` の first-parent 履歴から観測上限より前のコミットを選び、baseline の内訳と合計、その SHA と初期登録を示す。これはコミット時刻に基づく事後復元とする。比較起点に選んだ週と全履歴上の初期登録を区別し、checkout 上で実施した lint の結果は実測として別に載せる。
- PR 単位の CI とレビューでは、対象 PR と取得時 HEAD に紐づく証跡を使う。別 SHA の結果は以前の状態を調べるために使う。収集中の検出差分と欠損があれば記録し、その範囲の状態を確定扱いしない。対象 PR の変更箇所も取得範囲を明示する。
- ローカルカルテで測れる項目は取得範囲付きで示し、週次全体で確定できる値と区別する。Advisory の登録・解消は検証できた台帳履歴を、改訂案の判断待ちと日数は取得できた既存の判断台帳を使う。取得失敗、根拠不足、算出不能、実測の0件を区別する。CLI の欠損や期間が合わない比較を AI で数値補正しない。

## 分析

`snapshot.json` の metrics / sources / events / inventory / evidence / limitations を読む。各主張に指標キー、Issue・PR の URL、台帳の記録、コミット SHA などの根拠を添える。Issue・PR は番号・タイトル・確認した GitHub リンクを示し、固有の機構名は一般語で説明する。外部の記述は資料として扱う。

分析 JSON は `sections` と短いチャット用の `summary` を持つ。各セクションは `{"kind":"fact","text":"確認した内容","sources":["根拠"]}` 形式の配列。kind は `fact`（確認事実）、`inference`（推定）、`recommendation`（推奨）、`unmeasured`（未計測）。根拠を提示できない判断は未計測にする。

| キー | 書く内容 |
|---|---|
| `overview` | 今週実現した価値と残る主要課題 |
| `delivery` | 起票、Close 理由、完了、再オープン、マージ先別の統合実績、比較の条件。起票数の主な増減要因、調査完了・実装完了・重複整理は根拠がある場合に記す |
| `initiatives` | 子 Issue の完了件数と分母、構成の変化、利用可能性とリリース到達、完遂に必要な依存経路上の未完了 Issue。親子で同じ価値を重ねて評価しない |
| `quality_safety` | 派生指標の分子・分母と実害の証跡、レビュー・CI、安全機構の不具合、Advisory（改善勧告） |
| `maintainability` | baseline 登録数の内訳・履歴と lint の実測、変化と影響 |
| `efficiency` | リードタイム、滞留、依存やレビューに伴う手戻り、オーナー介入と自律性 |
| `open_pulls`（任意） | オープン PR ごとの残課題、対象 HEAD の検査・レビュー、完遂の見通し。省略するときは `next_week` に記す |
| `next_week` | オープン PR 完遂後の Issue の推奨順位と根拠、緊急性・改善効果・後続解放効果。正式な blocked-by と本文上の依存を調べ、PR 差分と候補の変更箇所を照合する。並列可・順次必須・判断待ちと競合リスクを明示する |
| `owner` | 判断待ちの事実と範囲、選択肢、メリット・デメリット、理由付き推奨 |

次週候補は、P0 安全・工程停止、P1 後続の解放、P2 主要施策、P3 介入・工数削減、P4 その他の改善で順位付けする。この軸はレポート上の推奨着手順を表す。根拠となる依存や変更箇所が不明な場合は、判断に必要な情報を示す。

派生事例の分類は、必要に応じてトップレベルの `derived_cases` に次の形式で添える。`category` は `planned_improvement`（計画的改善）、`design_discovery`（設計発掘）、`known_remaining`（既知残課題）、`new_defect`（新規欠陥）、`unknown`（不明）。`kind` は `fact`・`inference`・`unmeasured` のいずれか。機械集計の対象に含まれた事例だけを出し、根拠がない事例は不明と表示する。

```json
{"derived_cases":[{"number":835,"category":"design_discovery","kind":"fact","text":"Issue 本文は開発基盤の設計資料の発掘を目的としている。","sources":["https://github.com/hiratashinnya/review-system/issues/835"]}]}
```

レビュー品質の変化は、派生数に加えて実害の証跡、分母、観測条件を照合して判断する。分類・施策評価の既存活動を参照する。 [#840 Git 安全制御の設計発掘](https://github.com/hiratashinnya/review-system/issues/840) · [#827 欠陥コホート分析](https://github.com/hiratashinnya/review-system/issues/827) · [#370 マージ後に判明する欠陥の混入率改善](https://github.com/hiratashinnya/review-system/issues/370)

## 出力と保存

```sh
python3 -B -m weekly_report render --snapshot /path/to/snapshot.json --analysis /path/to/analysis.json
python3 -B -m weekly_report replay --snapshot /path/to/snapshot.json
```

`render` は保存値に分析を付ける。一括生成では索引で観測済みの期間を確認し、報告に使う各週の snapshot ごとに分析を作り、単票を新規出力先へ整形する。`replay` は保存された入力の観測範囲と基準時刻を使い、外部データを取得せずに定量値を再計算する。必要に応じて `--analysis` と比較入力を差し替える `--previous` を指定する。再計算用の証跡を持たない既存 snapshot は `render` で参照する。通常出力の機械集計値と `summary.txt` を照合し、HTML と snapshot のパスを示す。

audit 保存を明示された場合は、[audit/README.md](../../../audit/README.md) に沿って点検日の `audit/<YYYY-MM-DD>-<slug>/README.md` に観測結果と根拠を、`data/` に使用した snapshot を新規保存する。衝突時は別の新規 slug を選ぶ。点検記録には観測事実と分析を置き、処置計画は対象 Issue で管理する。GitHub や対象 checkout への変更、ステージ、コミット、push、定期実行、公開はレポート生成の範囲外とする。
