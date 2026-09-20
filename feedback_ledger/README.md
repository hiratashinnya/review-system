# `feedback_ledger` — オーナー判断フィードバック台帳の CLI と機械 lint

オーナーが AI の推奨を曲げた判断を、**改ざん検知可能な形**で版管理下に蓄積する（Issue #522）。
捕捉（I2）・週次棚卸し（I3）・反映（I4）はいずれもこのスキーマと CLI の上に載る。

区分: どちらのシステム（doc_system / review_system）にも含有されない**汎用開発ハーネス**
（`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」）。指摘・改善は
ノード起票ではなく Issue で起票する。

## 使い方

```
# 下書きを tmp/_feedback/ に書いてから CLI に食わせる（直接 .ai/feedback/ へは書けない）
python3 -m feedback_ledger new-entry      --from tmp/_feedback/FBK-20260919-example.toml
python3 -m feedback_ledger propose        --from tmp/_feedback/FBP-20260919-example.toml
python3 -m feedback_ledger amend-proposal --from tmp/_feedback/FBP-20260919-example.toml
python3 -m feedback_ledger propose        --from <新案> --supersede FBP-20260919-example

python3 -m feedback_ledger approve    --proposal FBP-… --triage TRG-2026-W38 --by owner
python3 -m feedback_ledger reject     --proposal FBP-… --by owner --reason "…"
python3 -m feedback_ledger apply-done --proposal FBP-… --issue-ref "#530" --applied-pr 531

python3 -m feedback_ledger triage-open  --week 2026-W38 --now 2026-09-19
python3 -m feedback_ledger triage-close --from tmp/_feedback/TRG-2026-W38.toml

python3 -m feedback_ledger check --canonical
python3 -m feedback_ledger check --canonical --require-base   # CI（base 未解決を ERROR にする）
python3 -m feedback_ledger status --now 2026-09-19 --json
python3 -m feedback_ledger index
```

終了コードは `dsv2` / `karte` と揃える: `0` 正常 ／ `2` 未検出 ／ `4` 前提違反・検証失敗。

## 規則一覧

| 規則 | 内容 | 実装 |
|---|---|---|
| L1 | キー集合の完全一致（欠落・未知とも拒否）、型、enum、`id` 書式、`id` とファイル名の一致 | `model.py` / `store.py` |
| L2 | `affected_assets` / `target_assets` の全パスが実在する | `check.py` |
| L3 | 文書 id 参照（`supersedes` / `decided_in`）の実在 | `check.py` |
| L4 | `owner_verbatim` への推測語彙の混入を拒否 | `model.py` |
| L5 | `inferred_reason` は `推測：` マーカー必須・断定語彙を拒否 | `model.py` |
| L6 | immutability: merge base に在る台帳エントリのバイト変更・削除を拒否 | `check.py` |
| L7 | canonical: パース→再シリアライズ→バイト比較（`check --canonical`） | `check.py` |
| P1 | 改訂案の状態遷移（`pending→approved→applied` / `pending→rejected` / `*→superseded`） | `check.py` / `cli.py` |
| P2 | `approved` に `decided_by`/`decided_at`/`decided_in`、`rejected` に `decision_reason`、`applied` に `issue_ref`/`applied_pr` | `check.py` |
| P3 | `derived_from` が非空で実在する台帳エントリを指す | `check.py` |
| P4 | `routing` が起票先の判定表と一致する | `check.py` / `routing.py` |
| T1 | `reviewed` と `outcomes[].entry` の集合一致、参照の実在、verdict ごとの必須欄、id と ISO 週の一致、週の重複（ERROR）・欠落（WARN） | `check.py` |

**L3 は Issue #522 の規則一覧が空けていた番号**（L1・L2・L4〜L7 で L3 が欠番）に、L2 と対になる
「参照 id の実在」を割り当てたもの。

誤検出（L4/L5）は `feedback_ledger/allowlist.py` に **理由必須**で登録する（理由が空なら
import 時 `ValueError`。`time_fixture_lint/allowlist.py`・`asset_parity/exceptions.py` と同じ運用）。

## 設計判断

### TOML を自前でシリアライズする（読みは `tomllib`）

オーナー確定（2026-09-19）。標準ライブラリの `tomllib` は**読み専用**で `dump`/`dumps` を持たず、
`tomli_w`/`toml`/`tomlkit` はいずれも未インストール。本リポジトリには依存マニフェストが無く、
既存ハーネスは全件が標準ライブラリのみで動く。**サードパーティ依存を追加しない**方針をここでも守る。
canonical バイト列の決定権を自前に持つことが L7 の安定性の根拠でもある（外部ライブラリだと版が
上がるたびに canonical の定義が動き、リポジトリ側の変更ゼロで CI が赤くなりうる）。
`store.write_document` は**書込み→読み戻し→再正規化して一致確認**までを毎回行う
（自前シリアライザの「書けたが読み戻せない」バグが黙って台帳を壊さないようにするため）。

### 台帳側に `status` を保存しない（PR5）

エントリの状態は改訂案と棚卸し記録から毎回導出できるので、`status.py` が算出する。保存すると
二重帳簿になり、片方だけ古くなる。滞留判定の wall clock は `--now` で注入する
（`.claude/rules/04-test-data.md`「時刻依存 test data の規律」）。

### 導出状態に `closed` を足した

Issue #522 が列挙した6状態（`untriaged`/`carried`/`proposed`/`approved`/`applied`/`rejected`）には
`no-change` / `merged-into` で決着したエントリの置き場が無い。`untriaged` に落とすと決着済みの
エントリが毎週の棚卸し入力に出続けるため、決着を表す `closed` を追加した。

### `approve` に `--proposal` を要求する

Issue #522 の verb 一覧は `approve --triage <TRG-id> --by <who>` だが、どの改訂案を承認するかを
指定しないと動作が決まらないため `--proposal` を必須にした。

### 訂正シナリオは CLI だけで完結する

| シナリオ | 手順 |
|---|---|
| 台帳エントリの誤記訂正 | `new-entry --from`（新しい id ＋ `supersedes = <旧 id>`）。旧エントリは L6 により変更できない |
| 改訂案本文の差し替え | `amend-proposal --from`（`pending` のときのみ） |
| 承認の取り消し | `propose --from <新案> --supersede <承認済み id>`（旧案を `superseded` にする。`approved→pending` の逆行遷移は作らない） |
| 棚卸し記録の追記 | `triage-close --from`（同じ週の記録を再確定する。棚卸し記録は L6 の対象外＝次節） |

### 棚卸し記録（`triage/`）を L6 の対象外にした理由

`check_immutability` が見るのは `LEDGER_PREFIX`（`.ai/feedback/ledger/`）だけで、
週次棚卸し記録は追記のみの制約を受けない。**台帳エントリと棚卸し記録では「何が一次情報か」が
違う**ため、意図的にこの非対称を採っている（F-522-07）。

* **棚卸しは週内に何度も追記されうる一つの作業単位**である。対象エントリを見落として
  後から足す、`need-more-evidence` のまま置いた項目に verdict を入れる、といった更新が
  同じ週の記録に対して普通に起きる。ここを追記のみにすると、更新のたびに `TRG-2026-W38b`
  のような別 id を作るか、週の粒度を捨てるかの二択になり、**id が ISO 週と一対一である**
  という T1 の前提（`period_start`/`period_end` の一致検査・週の重複と欠落の検出）が壊れる。
* **失われる情報が無い**。台帳エントリの `owner_verbatim` は**その場でしか取れない一次情報**
  （後から再構成できない）なので、バイト単位の不変性を機械で守る価値がある。対して棚卸し記録に
  載るのは「どの改訂案を起票したか」「どの台帳エントリへ merge したか」という**他の版管理下の
  文書への参照**であり、決定そのものは改訂案側の `status`／`decided_in`／`decided_by`／
  `decided_at` に記録される。棚卸し記録を書き換えても、決定の実体は改訂案側に残る。
* **書き換えは git 履歴と `decided_in` で追える**。`.ai/feedback/` は版管理下なので、
  棚卸し記録の変更は PR の差分として必ずレビューに載る（L6 が無くても「黙って変わる」ことは
  ない）。加えて改訂案の `decided_in` がどの週の記録で決着したかを指すため、
  記録の書き換えと決定の対応は後から突き合わせられる。
* **それでも L7（canonical）と T1 は掛かる**。手編集による整形崩れと、参照の実在・verdict ごとの
  必須欄・id と ISO 週の一致は棚卸し記録にも適用される。対象外にしたのは L6 だけである。

## 既知の限界（多層防御の一枚であって sandbox ではない）

* **`permissions.deny` の実効性は決定的観測で決着済み（F-522-04・2026-09-20 主文脈が実施）。**
  非隔離の主文脈がメインチェックアウトの `tmp/_karte/probe-pattern-522.md` へ `Write` を試みたところ
  "File is in a directory that is denied by your permission settings." で拒否された
  （当時の `permissions.deny` は `Edit(/tmp/_karte/**)` の1エントリのみで `settings.local.json` は
  存在しなかった）。先頭 `/` は設定ファイルのあるディレクトリ（メインチェックアウト）相対として
  解決され、意図どおり発火する。
* **隔離ロールに対する保護は別機構＝worktree isolation が担う。** 隔離 worktree の probe エージェントが
  メインチェックアウトの同パスへ `Write` を試みたところ "This agent is isolated in the worktree
  <path>. Edit the worktree copy of this file instead of the shared-checkout path." で拒否された。
  同じ probe が自分の worktree 内へ `Write`/`Edit` するのは成功し、メインチェックアウトからの `Read`
  も成功した。すなわち台帳の保護は**二層**——非隔離の書き手には `permissions.deny`、隔離ロールには
  worktree isolation——で成立しており、片方だけでは完結しない。
* **worktree 内の `tmp/_karte/` や `.ai/feedback/` は CLI が読まない場所であり本物の台帳ではない。**
  `karte/paths.py::main_worktree_root`（K-01）は linked worktree から必ずメインチェックアウトへ収束
  するため、本物の台帳は常にメイン側にある。隔離ロールが自分の worktree 内へ書き込めても、それは
  CLI が参照しない場所への書込みであって台帳の改ざんにはならない。
* **`permissions.deny` は Claude Code の Write/Edit ツール経由の書込みしか塞がない。**
  Bash 経由の `sed -i`・`tee`・シェルリダイレクトによる直接改変には掛からない
  （`karte/model.py`「改ざん防止の機械的裏付けと既知の限界」・`.claude/hooks/agent-command-gate.sh`
  の静的検査と同じ制約＝Issue #129）。**ただしこちらは版管理下にあるため、迂回して書き換えても
  L6（immutability）と L7（canonical）が PR 上で検出する**——`tmp/` に置かれるカルテには無い後段の網。
* **`decided_by` がオーナー本人かは機械検証していない。** `approve --by <who>` の値は文字列として
  記録されるだけで、署名も認証もない。機械が強制するのは**記録があること**までで、記録者の同一性は
  運用規律（`.claude/rules/03-operational.md`「「対応不要」を AI が独断で書かない」）と PR レビューに依る。
  `issue_ref` も形式検査だけで Issue の実在は見ない。
* **語彙一致 lint（L4/L5）は取りこぼす。** 決定論的な部分文字列一致なので、列挙していない言い回しの
  推測（「〜と受け取れる」等）や、断定を避けた体裁の断定は通る。逆に正当な用法を誤検出することもある
  （その場合は `allowlist.py` へ理由付きで登録する）。網羅ではなく**明白な混同を止める**ための網。
* **L6 / P1 は git が使えない環境・merge base を解決できない環境では skip する（WARN）。**
  shallow clone でビルドが必ず落ちる事態を避けるための意図的な非対称で、skip したことは WARN として
  必ず出力される（黙って通ることはない）。**CI では `fetch-depth: 0` に加えて
  `check --canonical --require-base` を実行し、base 未解決そのものを ERROR に昇格させている**
  ——WARN のままだと ERROR 閾値でしか落ちない CI は緑を保つため、`fetch-depth: 0` が外れた
  瞬間に改ざん検知と状態遷移検査が無言で無効化される（F-522-02）。`--require-base` を
  付けない既定の挙動は WARN のままなので、ローカル実行や git の無い環境は影響を受けない。
* **`.ai/feedback/` は worktree ごとに独立している。** `karte` と違い main worktree へ収束させない
  （版管理下の内容なので、linked worktree ではそのブランチのチェックアウトを読み書きするのが正しい）。
