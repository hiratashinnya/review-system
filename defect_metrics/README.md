# defect_metrics — 欠陥混入率の機械計測（Issue #488）

merge 後に判明する「同時に処置すべきだった」欠陥の混入率（#370）を、**誰がいつ実行しても
同じ数字になる形**で算出し、機械可読なレポートとして出力する。標準ライブラリのみに依存する。

- 起票先区分：**どちらのシステムにも含有されない汎用開発ハーネス**
  （`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」）。
  したがって本ツールに対する指摘・改善は doc-system-v2 のノード起票ではなく Issue で扱う。
- 運用（publish・外部 cron・PAT・疎通確認）：`docs/methods/defect-metrics-external-cron-ops.md`
- publish 先：孤立ブランチ `defect-metrics` の `report.json`
  （`.github/workflows/defect-metrics.yml`）

## 1. なぜ作ったか

Issue #368 は基線を「2026-08-01〜08-16 の実測・15日・PR 1本あたり 1.86」と**散文で**記していた。
2026-09-06 に再計測したところ、1.86 を再現する窓は **`2026-08-02T00:00Z <= t < 2026-08-16T00:00Z`
（14日）に一意に定まる**ことが判明した（08-01 起点なら 2.38、08-16 を含めると 2.62）。
定義が散文にある限り、窓の起点・境界の開閉・分子の数え方が読み手ごとにずれ、同じズレが
再計測のたびに再発する。本ツールは定義を**コード上の定数と型**として固定する。

## 2. 固定した指標定義（正本＝`defect_metrics/model.py`）

| 要素 | 定義 | 実体 |
|---|---|---|
| 窓 | `lo <= t < hi` の半開区間・UTC | `model.Window` |
| 分母 | 窓内に merge された PR 数（`mergedAt`） | `metrics.compute_window_metrics` |
| 分子（主指標） | 窓内に作成された Issue のうち、本文が参照する PR（**`#N` 記法・同一リポジトリの `OWNER/REPO#N` 記法・同一リポジトリの完全 URL の3つを同一の参照として数える**）に「起票時刻から遡って **72 時間**以内に merge された PR」を1つ以上含むもの＝**派生 Issue** | `metrics.is_derived` / `metrics.referenced_numbers` / `model.DERIVATION_HORIZON` |
| 分子（副指標） | 窓内に作成された**全** Issue 数（起票粒度の変化に汚染されるため主指標と対で出す） | `WindowMetrics.created_issues` |
| open Issue 純増 | 窓内作成 − 窓内 close | `WindowMetrics.open_issue_net_change` |

補足：

- 参照は**本文だけ**を見る（タイトル・コメントは見ない）。`##` 見出しや `&#187;` のような
  HTML entity は除外する（＝`metrics.ISSUE_REFERENCE_RE`）。`owner/repo#N` のような
  リポジトリ修飾付きの形は owner/repo を見て採否を決める（自リポジトリなら数え、
  他リポジトリなら数えない＝`metrics.QUALIFIED_REFERENCE_RE`）。
- **`#N` 記法・`OWNER/REPO#N` 記法・完全 URL（`https://github.com/OWNER/REPO/pull/N`）は
  同じ参照として数える**（§2.1）。

### 2.1 なぜ3記法を同一視するか（Issue #493・オーナー確定＝案 (a)）

人間にとって `#487`・`hiratashinnya/review-system#487`・
`https://github.com/hiratashinnya/review-system/pull/487` は同じ意味であり、画面上の見え方も変わらない。
ところが **この記法差はツールからは見えない**。一部の記法だけを拾っていると、主指標の正しさが
「起票者がその記法で書き続ける」という **どこにも記録されていない前提** に乗る。
前提が崩れれば（起票者の習慣の変化・Issue テンプレートの導入・別ツールによる自動起票など）主指標は
静かに下振れし、その下振れは「欠陥混入が減った」ように見える。誰も疑わない。これは Issue #488 が
解こうとした失敗（散文定義による再現不能）が、定義の所在から記法への依存へ移動して残っていた形である。

- 実装＝`metrics.ISSUE_REFERENCE_RE` / `metrics.QUALIFIED_REFERENCE_RE` / `metrics.URL_REFERENCE_RE`
  と `metrics.referenced_numbers`。3記法を **PR 番号へ正規化した集合** で扱うので、同じ PR を
  複数記法で書いた本文が二重計上されることはない。
- **リポジトリ修飾付きの2記法（`OWNER/REPO#N` と完全 URL）は自リポジトリのものだけを採る**。
  他リポジトリを拾うと、他リポジトリの PR 番号が自リポジトリの PR 番号として誤ヒットする。
  逆に自リポジトリを指す `OWNER/REPO#N` まで落とすと、`#N` と URL で塞いだ穴が第三の記法に残る
  （Issue #493 のレビュー指摘 F-493-01）。判定に使う `OWNER/REPO` は `--repository` の値であり、
  読めない形式なら `ValueError` で止める（黙って旧定義へ戻らない＝PR4）。この検証は
  **窓内 Issue の有無に依らず CLI 入口で無条件に走る**（F-493-02。`referenced_numbers` の内側に
  だけ置くと、窓内に作成 Issue が無い入力では一度も呼ばれずデータ依存になる）。
- **リポジトリを改名すると旧 slug の参照は落ちる（既知の前提・オーナー判断 2026-09-08）。**
  照合は `--repository` の slug との完全一致なので、改名前に書かれた `OWNER/OLD-REPO#N` と
  `https://github.com/OWNER/OLD-REPO/pull/N` は、GitHub 側が旧 URL を転送していても参照として
  数えられなくなり、派生 Issue 数だけが静かに下がる。基線窓にはこの2記法由来の派生が0件のため
  `verify-baseline` でも検知できない。**API で正準 slug を引いて改名へ追随する案は採らない**
  ——ネットワーク照会は「`--issues-json` / `--pulls-json` だけで決定的に再現できる」という
  本ツールの性質（§4）を崩し、算出のたびに外部状態へ依存させるため。改名が実際に起きた時点で
  別途扱う（F-493-03）。
- `/issues/N` 形式の URL も受ける。`#N` は Issue と PR を区別しない記法であり、GitHub は PR への
  `/issues/N` URL を `/pull/N` へ転送する。PR でない番号は merged PR 辞書を引いた時点で自然に落ちる。
- **却下案（記録・消さない）**: (b) 現状維持して前提を明記するだけ＝記録するだけで検出はしないので
  PR4「観測できないものは持たない」に反する。(c) 記法別の内訳を `report.json` へ出す＝記法の
  移り変わり自体は観測できるが、(a) が全記法を同一視する以上、内訳は指標の正しさには
  不要でありスキーマを広げるコストに見合わない（オーナー判断）。将来 記法差の分析が必要になった
  時点で改めて検討する。
- 派生判定の参照先 PR は**窓の内外を問わない**。窓の先頭直前に merge された PR に由来する
  起票を落とさないため。分子を絞るのは「Issue の作成時刻」だけである。
- 起票より**後**に merge された PR への言及は原因になりえないので数えない。
- 分母が 0 のときは比率を 0 に潰さず「算出不能（`null`）」として持ち上げる。

## 3. 閾値判定（`defect_metrics/threshold.py`）

| コード | 条件 |
|---|---|
| `BASELINE_EXCEEDED` | 派生 Issue/PR が基線 **0.68** を超えた |
| `TRAILING_REGRESSION` | 直近4週（レポート窓の直前に接続する28日）の派生 Issue/PR に対し **50% 以上悪化**（`current >= trailing * 1.5`） |

**異常でなければ何も報告しない**——`alerts` が空のとき CLI は stderr に一切書かず exit 0 を返す
（レポート JSON 自体は毎回 publish するが、それは「異常の報告」ではなく計測結果の保存である）。

### 「直近4週」はプールド比（週次比の平均ではない）

Issue #488 本文の「直近4週**平均**から 50% 以上悪化」には2通りの読み方がある。

- **(A) プールド比**：直近28日を**ひとまとめの窓**として `derived_issues / merged_prs` を取る。
- **(B) 週次比の平均**：週ごとに比を出し、その4本を平均する。

本ツールは **(A) を採る**。理由は3つある。

1. **少 PR 週の比が平均を支配する**。(B) は週ごとの比を等しい重みで平均するので、merged PR が
   1本しかない週の `1/1 = 1.0` が、10本 merge された週の `0/10 = 0.0` と同じ重みになる。
   週次比が `0/12, 0/10, 0/9, 1/1` の例では (A) が `1/32 ≒ 0.031`、(B) が `0.25` となり、
   レポート窓 0.10 に対して **(A) では `TRAILING_REGRESSION` が立ち (B) では立たない**。
   分母の少ない週ほど比が暴れるという性質が、そのまま判定の反転になる。
2. **分母0の週の扱いを定義できない**。(B) は merge が 0 本の週の比が算出不能になり、
   「除いて平均する」「0 とみなす」のどちらを選んでも新しい恣意が入る。(A) なら 28 日を
   まとめた分母が 0 のときだけ `skipped` にすればよく、判断が1箇所で済む。
3. **レポート窓側の集計と揃う**。レポート窓（既定7日）も窓全体の比なので、(A) なら
   「同じ計算を幅の違う窓に当てているだけ」になる。(B) は比較の両辺で集計方法が変わる。

この選択は `report.json` にも載る（`trailing_4_weeks.aggregation.method = "pooled"` と
`threshold.trailing_aggregation`）。フィールド名 `trailing_4_weeks` だけでは (A)/(B) を
区別できず、Issue #488 が排除しようとした「散文定義の曖昧さ」が閾値側に残ってしまうため。
Issue #488 本文の「平均」という語との差異も、同じフィールドの `detail` で追跡できる。

### 基線の再現検証はレポートにも載る

`report.json` の `baseline_verification` に、基線窓（2026-08-02〜08-16）の再計測値・
記録済み基線・`reproduced`・`mismatches` が入る（`verify-baseline` サブコマンドと同じ照合を
`report` 側でも行う）。Actions の step ログは既定 90 日で失効し、レポートを読む側（#461 の
報告経路）にも届かないため、照合結果を計測結果と同じ場所へ永続化する。

`reproduced` が `false` のとき、`threshold` の基線比較（定数 `0.68`）は
**「記録済み基線とは別定義の値」との比較**になっている。ワークフローはこの場合、レポートを
publish した**後で** job を失敗させる（`.github/workflows/defect-metrics.yml`・
`docs/methods/defect-metrics-external-cron-ops.md` §4.1）。

比較の精度を2本で意図的に変えている。

- 基線比較は**表示精度（小数2桁）どうし**。基線 0.68 は実測 15/22 = 0.6818… を2桁で記録した値で
  あり、厳密値どうしで比べると**基線の窓自身が「基線超過」になってしまう**。
- 直近4週比較は**有理数（`fractions.Fraction`）の厳密値**。float だと
  `0.2 * 1.5 == 0.30000000000000004` の表現誤差で「ちょうど1.5倍」の境界が裏返る。

比較不能な条件（分母0・直近4週にデータ無し）は「異常なし」に倒さず `skipped` に明示する
（観測できていないことを「正常」と読ませない＝PR4）。

## 4. 使い方

```
# レポート（既定＝現在時刻から遡る7日。異常時のみ stderr に出力し exit 20）
python3 -m defect_metrics report --repository OWNER/REPO --output report.json

# 窓を明示する（決定的・再現用）
python3 -m defect_metrics report --repository OWNER/REPO \
    --window-start 2026-08-02 --window-end 2026-08-16 --now 2026-08-16T00:00:00Z

# 基線窓の実測値（22 PR / 41 Issue / 1.86 / 派生 15 / 0.68）を再現できるか照合する
python3 -m defect_metrics verify-baseline --repository OWNER/REPO
```

主なオプション：

| オプション | 用途 |
|---|---|
| `--window-start` / `--window-end` / `--window-days` | 窓の指定。両端を省略したときだけ `--now` を終端に採る |
| `--now` | 現在時刻の固定。**本パッケージが wall clock を読むのはこの既定分岐 1 箇所だけ**（`cli.resolve_now`） |
| `--issues-json` / `--pulls-json` | `gh ... --json` 出力を保存したファイルから読む（ネットワーク・認証に依存せず再現できる） |
| `--output` | 出力先ファイル（省略時 stdout） |
| `--limit` | `gh ... list --limit`（既定 2000）。**取得件数がこの値に達したら打ち切りとみなして `CollectionError` で止まる**（下記） |

終了コード：`0`=正常 / `20`=異常検知 / `21`=基線再現の不一致（`verify-baseline`）/ `1`=取得・解釈エラー。

### 取得件数の打ち切りは致命エラー（fail-close）

`gh ... list --limit N` は**新しい方から N 件**を返して打ち切る。全件が N を超えると古い側が
黙って落ち、まず基線窓（過去の固定窓）の再現が壊れ、次に `is_derived` の参照先 PR 辞書が欠ける。
`gh` 自身は成功終了し JSON も正当なので、スキーマ検査には掛からない——**レポートは正常な体裁の
まま誤った数字を載せる**。そこで `collect._ensure_not_truncated` が「取得件数が `--limit` に
達した」時点で `CollectionError` を送出し、レポートを publish しない fail-close に乗せる
（ちょうど `--limit` 件のときは打ち切りかどうか区別できないので、打ち切り側に倒す）。
既定値を上げるだけの対処は同じ穴を先送りするだけなので採らない。

## 5. 時刻依存 test data の扱い

`.claude/rules/04-test-data.md`「時刻依存 test data の規律」に従い、wall clock を読む経路を
`cli.resolve_now` の1箇所に閉じ込め、`--now` / `now=` で必ず注入できるようにしてある。
指標算出（`metrics`）と閾値判定（`threshold`）は現在時刻を一切読まず、渡された窓とレコード
だけで決まる純粋な計算である。

**この性質はテスト構成に依存しない**——`tests/unit/test_defect_metrics.py` に今後どんな
テストを足しても、`cli.resolve_now` の既定分岐を通さない限り絶対日付は wall clock と
比較されず、時間経過だけで赤くなることはない。したがって本パッケージのテストで気を付ける
べき点は次の1つに集約される：**`resolve_now` の既定分岐（`--now` 未指定）を呼ぶテストでは、
固定日付と比較せず「UTC の aware datetime を返すこと」だけを検査する**（現在その分岐を
呼ぶのは `WindowResolutionTests.test_resolve_now_without_injection_returns_aware_utc` の
1件のみ）。窓の決定が現在時刻に依存する経路と閾値判定の「直近4週」は、必ず `--now` / `now=`
で固定値を注入する。

`python3 -m time_fixture_lint check` の対象語彙（`expires_at` 等の境界値フィールド名）に
該当するフィールドは、本パッケージも本テストも持たない。

## 6. 実データでの一致確認（2026-09-06 実測）

Issue #488「現状と根拠」の実測表に対し、本ツールが同じ値を返すことを確認済み。

| 窓（UTC・`lo <= t < hi`） | merged PR | 全 Issue | 全 Issue/PR | 派生 Issue | 派生/PR |
|---|---|---|---|---|---|
| 2026-08-02 〜 08-16（基線） | 22 | 41 | 1.86 | 15 | 0.68 |
| 2026-08-16 〜 09-06 | 56 | 52 | 0.93 | 17 | 0.30 |

基線窓の派生 Issue 15 件の内訳（`derived_issue_numbers`）：
#302 #317 #318 #337 #338 #339 #344 #345 #354 #355 #356 #360 #362 #363 #365。

### 6.1 記法を広げた後の再計算（2026-09-08 実測・**変化なし**）

Issue #493 で定義を広げた（§2.1）ので、追加した2記法それぞれについて基線窓を再計算した。
**上表の値はいずれも変わらなかった。** したがって `model.BASELINE_*` の5定数・`verify-baseline`
の期待値・本 README・`docs/methods/defect-metrics-external-cron-ops.md` の記載値はすべて据え置きである。

走査範囲：基線窓に作成された Issue の番号は **302〜367** に収まる（#301 は `2026-08-01T15:12:55Z` で
窓の手前、#368 は `2026-08-16T05:27:06Z` で窓の外。Issue/PR は作成順に採番されるので、この2点で
範囲が閉じる）。以下いずれも、Issue・PR の別を問わない**上位集合の全番号**の本文を走査している。

**完全 URL（初回実装時の確認・`gh issue view <N> --json number,createdAt,body`）**

- 302〜367 の本文に現れる自リポジトリの完全 URL は #323 → `issues/323` と #339 → `issues/339` の
  **自己参照2件だけ**で、どちらも Issue であって merged PR ではない。
- 2 行目の窓（2026-08-16 〜 09-06・番号 368〜479）では #385・#452・#471・#456 の4件。#385/#452 は
  自己参照、#471 の参照先 #470 は Issue（merged PR ではない）、#456 の参照先 PR #455 は
  **同じ本文に `#455` が既にある**ため参照集合が変わらない。

**`OWNER/REPO#N`（F-493-01 の是正時の確認・2026-09-08）**

- 走査コマンドは `gh issue view <N> --json body --jq '(.body // "")|test("review-system#";"i")'`
  を 302〜367 と 368〜479 の**全番号に対して1件ずつ**実行するもの（真偽値を返すので、判定が
  ランキングや目視に依存しない）。
- 基線窓の該当は **#320 と #345 の2件だけ**。#320 は URL が `/pull/320` で **Issue ではなく PR** の
  ため分子の母集団（`gh issue list` が返す Issue）に入らない。#345 は Issue だが
  `derived_issue_numbers`（下記）に既に含まれており、参照が増えても派生判定は変わらない。
- 2 行目の窓（368〜479）は **該当0件**。

**共通の理由**：参照の追加は派生判定を **増やす方向にしか働かない**（`is_derived` は参照集合の
いずれかが条件を満たせば true）。新たに派生になる Issue が無い以上、派生 Issue は 15 件のまま、
分母（merged PR）と副指標（全 Issue 数）は定義自体が変わっていないので不変。なお、この判断が
誤っていた場合は `verify-baseline`（`report` サブコマンドにも同梱）が実データに対して
`reproduced: false` を返し、ワークフローが job を失敗させる（§3「基線の再現検証はレポートにも
載る」）ので、誤りは黙って通らない。

## 7. 依存仕様

- 指標定義の一次アンカー：Issue #488「提案挙動」および「現状と根拠」の実測表、
  Issue #368「現状と根拠」（2026-09-06 訂正済み）、Issue #493「提案挙動（オーナー確定：案 (a)）」
  （参照の記法＝`#N`・`OWNER/REPO#N`・完全 URL の同一視・§2.1）。
- 入力フォーマット：`gh issue list --json number,createdAt,closedAt,body`（`--state all` は
  PR を含まない）／`gh pr list --state merged --json number,mergedAt`。`gh` の出力スキーマが
  変わったら `defect_metrics/collect.py` の `load_issues` / `load_pulls` が
  `CollectionError` で fail-close する。
- 取得件数の上限：`gh ... list --limit` が新しい側から打ち切る仕様に依存する。件数が
  `--limit` に達したら `collect._ensure_not_truncated` が `CollectionError` で fail-close する
  （§4「取得件数の打ち切りは致命エラー」）。
- publish 方式：`.github/workflows/blocker-snapshot.yml`（孤立ブランチへの単一 commit
  force-push）と同一。
