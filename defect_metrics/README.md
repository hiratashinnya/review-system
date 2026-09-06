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
| 分子（主指標） | 窓内に作成された Issue のうち、本文が参照する `#N` に「起票時刻から遡って **72 時間**以内に merge された PR」を1つ以上含むもの＝**派生 Issue** | `metrics.is_derived` / `model.DERIVATION_HORIZON` |
| 分子（副指標） | 窓内に作成された**全** Issue 数（起票粒度の変化に汚染されるため主指標と対で出す） | `WindowMetrics.created_issues` |
| open Issue 純増 | 窓内作成 − 窓内 close | `WindowMetrics.open_issue_net_change` |

補足：

- 参照は**本文の `#N` のみ**（`owner/repo#N` のような他リポジトリ参照、`##` 見出し、
  `&#187;` のような HTML entity は除外する＝`metrics.ISSUE_REFERENCE_RE`）。
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
| `--limit` | `gh ... list --limit`（既定 2000） |

終了コード：`0`=正常 / `20`=異常検知 / `21`=基線再現の不一致（`verify-baseline`）/ `1`=取得・解釈エラー。

## 5. 時刻依存 test data の扱い

`.claude/rules/04-test-data.md`「時刻依存 test data の規律」に従い、wall clock を読む経路を
`cli.resolve_now` の1箇所に閉じ込め、`--now` / `now=` で必ず注入できるようにしてある。
指標算出（`metrics`）と閾値判定（`threshold`）は現在時刻を一切読まず、渡された窓とレコード
だけで決まる純粋な計算である。したがって `tests/unit/test_defect_metrics.py` は絶対日付を
多用しても時間経過で赤くならない。`python3 -m time_fixture_lint check` の対象語彙
（`expires_at` 等の境界値フィールド名）に該当するフィールドは持たない。

## 6. 実データでの一致確認（2026-09-06 実測）

Issue #488「現状と根拠」の実測表に対し、本ツールが同じ値を返すことを確認済み。

| 窓（UTC・`lo <= t < hi`） | merged PR | 全 Issue | 全 Issue/PR | 派生 Issue | 派生/PR |
|---|---|---|---|---|---|
| 2026-08-02 〜 08-16（基線） | 22 | 41 | 1.86 | 15 | 0.68 |
| 2026-08-16 〜 09-06 | 56 | 52 | 0.93 | 17 | 0.30 |

基線窓の派生 Issue 15 件の内訳（`derived_issue_numbers`）：
#302 #317 #318 #337 #338 #339 #344 #345 #354 #355 #356 #360 #362 #363 #365。

## 7. 依存仕様

- 指標定義の一次アンカー：Issue #488「提案挙動」および「現状と根拠」の実測表、
  Issue #368「現状と根拠」（2026-09-06 訂正済み）。
- 入力フォーマット：`gh issue list --json number,createdAt,closedAt,body`（`--state all` は
  PR を含まない）／`gh pr list --state merged --json number,mergedAt`。`gh` の出力スキーマが
  変わったら `defect_metrics/collect.py` の `load_issues` / `load_pulls` が
  `CollectionError` で fail-close する。
- publish 方式：`.github/workflows/blocker-snapshot.yml`（孤立ブランチへの単一 commit
  force-push）と同一。
