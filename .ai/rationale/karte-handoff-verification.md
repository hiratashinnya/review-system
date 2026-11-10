# karte handoff 検証の設計（Issue #683）

設計者＝Claude Code (AI)。**この文書は実装前の設計であり、実装は後続の是正ラウンドで行う**。Issue #683 の本文（Scope・AC・設計論点 a〜g・未決点 Q1〜Q3）を前提とする。K-01〜K-04 の分割（`.ai/rationale/karte-module-split.md`）を基盤とし、本 PR は第二弾である。**`maintainability_lint/baseline.json` は第一弾（PR #795〜#807）で更新済みで、本 PR では一切変更しない。**

## 1. オーナー確定（#683 の未決点）
| 未決点 | 確定 | 設計への反映 |
|---|---|---|
| Q1 外部投稿の事前確認 | **C**：verb は投稿内容をプレビュー表示し、確認を経て投稿する。確認なしの自動投稿はしない | `handoff-preview`（投稿しない）と `handoff-post`（プレビューの digest を確認トークンとして要求）に分ける。§4 |
| Q2 変更範囲 | **A**：handoff は無進捗（escalate）判定の計数からのみ除外する。verdict は不変 | `needs_remediation`・`check`・verdict は変更しない。無進捗の集計だけが別述語を通る。§6 |
| Q3 申し送り先が closed（completed）のとき | **A**：not planned と同様に計数へ復帰する | 再検証で closed（理由を問わない）を `invalid` にする。§7 |

オーナー承認の記録（この PR 本文にも載せる）：上記3点はオーナーが確定（#683 の本文末尾の原案どおり、Q1＝C・Q2＝A・Q3＝A）。ここで確定した判断を AI が覆さない。

## 2. 覆す既存設計と、残す保証範囲
- 覆す対象：`harm: none` の finding は `deferred` と書いても無進捗の計数から外れない（2026-09-07 オーナー確定。`karte/README.md`「`clean` の解除力は `harm: real` にだけ与える」）。
- 覆す根拠（#683 の本文と同じ）：解除条件を「`deferred` と書くこと」から「機械検証済みの転記が申し送り先に実在し、内容が現在の finding と一致し、申し送り先が open であること」へ置き換える。自己申告の2行では満たせない。**verdict の STOP（`no-harm-only` はオーナーへ打ち上げる）は維持する。**
- 保証するのは「記録が申し送り先に実在し続けること」まで。申し送りの適否はオーナー判断のまま。verb を実行するのは AI 自身なので、無関係な open Issue へ投稿して検証を通す余地は残る（Issue #129 と同種の限界）。

### 2026-09-07 確定の旧記述（移設・PR8 区分1）
書き換え（区分2）の前に、旧記述を次のとおり逐語で保全する。実装では README・docstring・SKILL を現行内容へ**書き換え**、この節へは追記しない。

`karte/README.md`「`clean` の解除力は `harm: real` にだけ与える（オーナー確定・2026-09-07）」：

```text
`harm: none` の finding に `disposition: deferred` / `waived` を書いても **verdict は動かない**
（記録としては残る）。`harm: none` の未解消がある間は verdict が `no-harm-only` のままになり、
「未解消がすべて実害なしになったらオーナーへ打ち上げる」STOP
（`.ai/skills/issue-pipeline/SKILL.md`「実害の定義とエスカレーション」）が生きる。

理由：`disposition` はそもそも「`harm: real` に対するオーナー判断の記録」として導入した
（Issue #495 の提案挙動 3〜5 はいずれも `harm: real` が主語）。解除力を `harm` の値によらず
与えると、実害なしの指摘に `deferred` と適当な Issue 番号を 2 行書くだけで verdict が
`clean` へ変わり、**AI が単独で既存のオーナー STOP を消せる**。それは本 Issue が塞いだ
「ラベルを書くだけで clean を通す」経路と同型のものを `harm: none` 側へ新設することになる。
```

`karte/__init__.py` のモジュール docstring の該当箇所：

```text
  **この解除力は ``harm: real`` にだけ与える**（オーナー確定・2026-09-07）
  ——``harm: none`` にも与えると、実害なしの指摘に ``deferred`` と書くだけで
  「未解消がすべて実害なしになったら打ち上げる」既存の STOP を消せてしまう。
  書式と移行措置の詳細は ``karte/README.md``。
```

`karte/karte_record.py::remediation_findings` の docstring 末尾：`除かれるのは **harm: real かつ** deferred/waived のものだけ（CLEARING_HARM）。harm: none は disposition を書いても残る。`

`.ai/skills/issue-pipeline/SKILL.md`「実害の定義とエスカレーション」：「**この解除力は `harm: real` の finding にだけ与える。** `harm: none` の finding に `disposition` を書いても記録が残るだけで verdict は動かない。」と、無進捗の項「**申し送り（`deferred`）／処置不要（`waived`）と決めた finding はこの計数から外れる**」。

**書き換え後の現行内容（実装で反映する）**：`clean` の解除力と verdict は従来どおり `harm: real` にだけ与える（`harm: none` の verdict は動かない）。**無進捗の計数だけは**、`harm: none`・`deferred` の finding が「検証済み handoff（申し送り先に実在し、内容が現在の finding と一致し、申し送り先が open）」を持つ場合に外れる。それ以外（`waived`、`harm: none` で未検証・無効の `deferred`）は従来どおり計数される。既知の限界は §2 の2点。

## 3. データ構造と書式（設計論点 b・c）
### 別フィールド（`status` 語彙は増やさない）
finding ブロックに**任意キー**を5つ追加する（`status` の語彙を増やすと `needs_remediation` を共有する verdict・`check` を巻き込むため）。

| キー | 意味 |
|---|---|
| `handoff_issue` | 申し送り先の Issue 番号（`deferred_to` と同じ解決可能な形から正規化） |
| `handoff_comment_url` | 投稿したコメントの URL |
| `handoff_content_hash` | 転記ブロックの内容ハッシュ（`sha256:<64桁hex>`） |
| `handoff_verified_at` | 最後に検証した UTC 時刻（ISO 8601） |
| `handoff_state` | `verified` または `invalid`（空＝記録なし） |

- 既存カルテとの互換：キーは**すべて任意で既定は空**。記録を持たない finding は `render_finding` が**これらのキーを出力しない**（既存カルテの出力はバイト単位で不変）。`FORMAT_VERSION` は 1 のまま（追加は加法的）。旧版の `karte` が新カルテを読むと未知キーとして拒否する（ロールバック時のみの前方非互換。既知の限界として README へ記す）。
- 保存先を別セクションにしない理由：`parse` は未知セクションを拒否し、`ingest-review` はセクション単位で書き直すため、別セクションは保持の仕組みを別に要する。finding ブロックのキーなら `apply_accepted` が上書きしない限り**全件再掲を跨いで保持される**（`apply_accepted` は handoff 系キーに触れない）。
- ID 再発番：記録は finding オブジェクトに付くので、**再発番された新しい finding には引き継がない**（記録なし＝計数される。fail-close）。`id` をハッシュに含めるため、他 finding のブロックを流用しても照合に失敗する。

### content_hash の対象（設計論点 c）
対象は `id`・`harm`・`summary`・`locus`（要素を整列）・`expected` の5項目を、固定の区切りと正規化（前後空白の除去・改行を含まない）で連結した文字列の sha256。`evidence`・`harm_detail`・`recheck`・`severity` は対象外（再掲での言い換えで毎ラウンド無効化されて偽陽性が戻るのを防ぐ）。対象を絞りすぎて内容変更を見逃す側のリスクは、`summary`・`expected` を含めることで限定する。ハッシュ対象の追加・変更は `HANDOFF_HASH_VERSION` の更新と既存記録の無効化を伴う（ブロックに `hash_version` を載せる）。

### 転記ブロック（申し送り先のコメント本文）
```text
<!-- karte-handoff:v1 -->
Claude Code (AI) による転記（karte handoff）
- finding: F-683-01
- harm: none
- summary: <summary 全文>
- locus: <a.py::f, b.toml::g>
- expected: <expected 全文>
- hash_version: 1
- content_hash: sha256:<64桁hex>
<!-- /karte-handoff -->
```
- 冒頭の1行は、実行した AI agent 由来であることの明記（`.ai/guidance/common.md`「言語・対外記録」。設計論点 e）。agent 名は `--agent` の必須引数（許可集合 `Claude Code` / `Codex`）から取り、既定値を持たない。
- 読み戻しでは、**投稿された本文のブロックから各項目を取り出してハッシュを再計算し**、(1) ブロック自身の `content_hash` と一致、(2) 現在の finding から計算したハッシュと一致、の2つを検査する。ブロックが複数ある・マーカーが無い・形式が違う場合は失敗。

## 4. verb と流れ（Q1＝C・設計論点 d・e・f）
`karte/handoff_cli.py` が `register(subparsers, add_issue)` を提供し、`__main__.py` の `extra_registrars` に追加する（`owner_cli`・`reviewer_cli` と同じ経路）。**`cli.py`・`parser_core.py` は変更しない**（`cli.py` の61行を保つ）。全 verb は `fail_close` でロック要否を宣言する。

| verb | 役割 | ロック | GitHub | 台帳への書込 |
|---|---|---|---|---|
| `handoff-preview --finding <ID> --to <Issue> --agent <名>` | 投稿予定の全文・宛先（`OWNER/REPO#N`）・**確認トークン**を出力する | なし | 読取りのみ（宛先 Issue が open で同一 repository か） | なし |
| `handoff-post --finding <ID> --to <Issue> --agent <名> --confirm <確認トークン>` | 確認トークンがプレビューと一致するときだけ投稿 → 読み戻し → ハッシュ照合 → 記録 | あり | コメント投稿・読取り | 照合成功時だけ `handoff_*` を書く |
| `handoff-recheck [--finding <ID>...]` | 記録を持つ finding の再検証（最終検証の入口） | あり | 読取りのみ | 観測結果に従い `handoff_state` を `verified`/`invalid` へ |

- **確認トークン**：投稿予定の本文・宛先・agent 名・finding の content_hash の sha256。オーナーがプレビューを確認した後に主文脈が `--confirm` へ渡す。プレビュー後に finding や本文が変わるとトークンが一致せず**投稿しない**（確認なしの自動投稿をしない）。`handoff-post` は `--confirm` が無ければ使用エラー（`KarteUsageError`）。
- **対象は自リポジトリの既存 Issue のみ**：宛先の repository は `origin` から導出して固定し、別 repository・新規 Issue 作成は対象外（新規 Issue は `/gh-create-issue` で作った後、その番号を `--to` に渡す）。
- **投稿後の失敗**：投稿後に読み戻しやハッシュ照合が失敗したら、**検証済みを書かず**、コメント URL と失敗理由を出して `EXIT_ERROR`（コメントは削除しない。削除は他者に見える操作で、オーナー判断）。
- **fail-close**：`gh` 不在・ネットワーク不可・非 0 終了・JSON 不正は検証失敗として扱い、検証済みを書かない。
- **GitHub 呼び出しの境界**：`gh` を呼ぶのは `handoff_github.py` だけ（`subprocess` で `gh api` を実行し、標準ライブラリのみ）。他モジュールは関数引数で実行関数を受け取る（試験は `gh` を差し替えてオフラインで通す）。**`status`・`render`・`check` はネットワークを呼ばない**（設計論点 d。決定論を保つ）。
- **実行主体（設計論点 f）**：主文脈専用。`.claude/hooks/agent-command-gate.sh` と `.codex/hooks/agent-command-gate.sh` の `KARTE_SUBCOMMANDS_BY_ROLE` は許可リスト方式で、`issue-fixer` は `render/append/close-attempt/check/status`、`pr-reviewer` は `ingest-reviewer` のままとする（新 verb は**どのロールにも追加しない**＝既定で deny）。変更は不要で、**新 verb が両 gate で deny されることを試験で固定する**（Codex 側は `pr-reviewer` に karte verb を許可しない）。ゲートは sandbox ではない（既存の限界と同じ）。
- 遡及（設計論点 g）：導入前に手書きで申し送り済みの Issue のコメントにはブロックが無いので、`handoff-preview`→`handoff-post` でブロックを投稿し直す運用。読み戻しモードは設けない（手書き本文の転記一致は機械照合できないため）。

## 5. `ingest-review` と レポート入力
- 全件再掲を跨ぐ保持：`apply_accepted` は `handoff_*` に触れない。内容が変わらない再掲では記録が残り、ハッシュも一致するので計数から外れたまま。内容が変わる再掲では記録は残るが**ハッシュ不一致で除外が効かなくなる**（再 `handoff-post` で新しいブロックを投稿し直すまで計数に戻る）。
- レポート入力の拒否：`review_block`（`parse_review`・`ingest-reviewer` 共用）が `handoff_` で始まるキーを検出したら、**取り込みごと拒否**（`KarteFormatError`・fail-close）。記録は verb だけが書く。
- `decide`・`ingest-review` の保護モード・`activate` は挙動不変。

## 6. 述語と計数（設計論点 a・Q2＝A）
- `Finding.needs_remediation`・`Karte.remediation_findings`・verdict・`check`・`#614` の領域は**変更しない**。
- 新しい純関数 `handoff_exemption.is_stall_exempt(finding)` を追加する。真の条件は**すべて**：`status == "open"`、`harm == "none"`、`disposition == "deferred"`、`handoff_state == "verified"`、`handoff_content_hash` が現在の finding から再計算したハッシュと一致。
- `stall_detection.stalled_ids` は `remediation_findings()` から `is_stall_exempt` を除いて数える。`render` の `★無進捗` は `stalled_ids` を引くので**同じ判定に従う**（経路別の再実装をしない）。`status` の `stalled_findings`・`escalate` も同じ。
- **`#614` との整合**：`check` 側の決定（診断網羅要求の除外規則）はこの PR で変えない。`handoff_exemption` を単一点にしてあるので、#614 が検証付き除外を採る場合は同じ述語を `check` から呼べる。経路ごとに別規則を作らない。
- `status --json` には、除外された finding がある場合に限り `handoff_exempt_findings`（ID の配列）を追加する（無い場合はキーを出さず、既存の golden・消費者 `karte_notify` に影響しない）。本文出力にも同じ条件で1行を追加する。

## 7. 計数への復帰（AC：各場合に試験）
| 場合 | 検出と処置 |
|---|---|
| ハッシュ不一致（再掲で内容が変わった） | `status` 時に再計算して不一致 → 除外されない（ネットワーク不要・記録は残す） |
| 申し送り先が closed（completed・not planned とも。Q3＝A） | `handoff-recheck` が `closed` を観測 → `handoff_state: invalid` |
| コメントの削除・編集 | `handoff-recheck` が 404 または本文のハッシュ不一致を観測 → `invalid` |
| `gh`・ネットワーク不可 | `handoff-recheck` が観測できない → `invalid`（保守側。再実行で観測できれば `verified` へ戻せる）。`status` は記録だけを読むのでネットワークは呼ばない |
| 申し送り先が open へ戻った・コメントが復旧した | 再実行した `handoff-recheck` が全条件を満たせば `verified` へ戻す |

最終検証の入口：`issue-pipeline` の合流前確認（②-d の `pr_merge_gate report` の前）に `python3 -m karte handoff-recheck` を実行し、`invalid` や不一致があれば出力で指摘する。実行は主文脈。SKILL の運用規定は §9。

## 8. モジュール分割（新規 Python module は100行以内・`dataclass` と具象ロジック class は別 file・連続4行以上の行コメント禁止）
命名は既存の `handoff_header.py`・`handoff_path.py`（レビュー handoff の取り込み用）と区別するため、本機能のモジュールは `finding_handoff_*` を使う。

| モジュール | 責務 |
|---|---|
| `finding_handoff_record.py` | `HandoffRecord`（frozen dataclass のみ。キー5つ） |
| `finding_handoff_keys.py` | キー名・`HANDOFF_KEYS`・`HANDOFF_HASH_VERSION`・レポートからの拒否判定 |
| `finding_handoff_hash.py` | `content_hash(id, harm, summary, locus, expected)`（純関数） |
| `finding_handoff_block.py` | 転記ブロックの生成と解析（純関数） |
| `finding_handoff_ledger.py` | ブロック（台帳の finding ブロック）との相互変換（`record_from_block`・`emit_lines`） |
| `finding_handoff_exemption.py` | `is_stall_exempt(finding)` |
| `finding_handoff_preview.py` | プレビュー本文・確認トークンの生成 |
| `finding_handoff_github.py` | `gh api` 呼び出しの唯一の場所（投稿・コメント読取・Issue 状態読取。実行関数を引数で差し替え可能） |
| `finding_handoff_verify.py` | 読み戻し本文と現在の finding の照合（`VerifyResult` を返す） |
| `finding_handoff_result.py` | `VerifyResult`（frozen dataclass のみ） |
| `finding_handoff_store.py` | ロック内での記録の書込・`handoff_state` の更新（台帳 I/O は `karte_loader`・`paths` 経由） |
| `verb_handoff_preview.py` / `verb_handoff_post.py` / `verb_handoff_recheck.py` | 各 verb（`@fail_close` を宣言） |
| `handoff_cli.py` | 引数定義と `register(subparsers, add_issue)`（`parser_*` と同じ流儀で1ファイルに収める。100行を超えるなら `parser_handoff_args.py` に分ける） |

既存ファイルの変更（**各ファイルが100行以内に収まること**が条件。超える場合は責務で更に分割する）：
- `finding_record.py`（現70行）：`handoff: HandoffRecord | None = None` の追加。
- `block_records.py`（現88行・追加余地が小さい）：ledger のブロックから `handoff_*` を読む呼び出しを `finding_handoff_ledger.record_from_block` に委ねる（本体は増やさない）。
- `karte_render.py`（現72行）：記録がある場合だけ `finding_handoff_ledger.emit_lines` を呼ぶ。
- `review_block.py`（現84行）：`handoff_` キーの拒否を `finding_handoff_keys` へ委ねる。
- `stall_detection.py`（現15行）：`is_stall_exempt` を除外。
- `status_payload.py`（現46行）・`status_text.py`（現92行・追加余地が小さい。超えるなら `status_handoff_lines.py` を新設）：除外 finding の出力。
- `__main__.py`：`extra_registrars` へ `handoff_cli.register` を追加。
- `model.py`：公開名の再エクスポート（`HandoffRecord` 等）が必要なら最小限。入口は100行以内を保つ。

**`maintainability_lint` への見込み**：新規モジュールはすべて100行以内・`dataclass` は `finding_handoff_record.py` と `finding_handoff_result.py` の2ファイルだけで具象ロジック class を同居させない・連続4行以上の行コメントを作らない。したがって `python3 -m maintainability_lint check` は `violations=0 accepted_debt=58` のまま通る見込みで、**`baseline.json` の変更は発生しない**。既存ファイルの変更で100行を超える場合は新規違反（baseline 外）として check が失敗するので、その場合は分割で対処し、baseline は更新しない。

## 9. 文書の更新（PR8 区分1→区分2）
1. 先に §2 の旧記述を本ファイルへ保全する（本 commit で実施済み）。
2. `karte/README.md`「`clean` の解除力は `harm: real` にだけ与える」節を、§2 の「書き換え後の現行内容」へ**書き換える**（追記で覆さない）。覆す根拠・保証範囲（記録が失われないこと）・既知の限界（§2）・新 verb・`handoff_*` キー・計数復帰の表（§7）を載せる。
3. `karte/__init__.py` の docstring と `karte/karte_record.py::remediation_findings` の docstring の該当記述を同様に書き換える。
4. `.ai/skills/issue-pipeline/SKILL.md`「②-c」の申し送り手順に、「`deferred` で申し送るときは `handoff-preview`（オーナー確認）→ `handoff-post` を使う」を追加し、「実害の定義とエスカレーション」の2記述を書き換える。②-d の合流前確認に `handoff-recheck` を追加する。`decide`・`activate`・`ingest-review` と同じく**新 verb は主文脈専用**で、是正当事者ロールは実行できない。`.claude/skills/`・`.agents/skills/` 等の生成物や写しの同期は、`guidance_sync`・`asset_parity` の手順に従う（実装時に各 README で確認し、`python3 -m asset_parity check` を通す）。
5. Q1〜Q3 のオーナー決定と理由は本ファイル §1 と、#683 本体にも残す。

## 10. 試験（`gh` はモック・オフライン）
追加するテストと fixture は、`tests/unit/test_karte_finding_handoff_*.py` と `tests/fixtures/karte/` 配下。`gh` は `finding_handoff_github` の実行関数を差し替える。
- 転記ブロックの生成→解析→ハッシュの往復、対象フィールド以外の変更でハッシュが変わらないこと、対象フィールドの変更で変わること。
- `handoff-preview` が投稿も書込もしないこと、`handoff-post` が確認トークン無し・不一致で使用エラーになり**投稿しない**こと（確認なしの自動投稿をしない）。
- 投稿→読み戻し→照合→記録の一気通貫。照合失敗（本文改変・ブロック欠落・複数ブロック）で**検証済みを書かない**こと。投稿後の失敗でコメントを削除しないこと。
- 記録は verb だけが書く：レポートの `handoff_*` キーを `ingest-review`・`ingest-reviewer` が取り込みごと拒否すること。
- 全件再掲（内容が同じ）を跨いで記録が保持されること。内容が変わる再掲でハッシュ不一致により除外が外れること。
- 検証済み handoff を持つ `harm: none`・`deferred`・open の finding が、無進捗の計数と `render` の `★無進捗` から外れ、**verdict が `no-harm-only` のまま**であること。`harm: real` の `deferred`・`waived`・未検証・`invalid` の finding の計数が従来どおりであること（回帰）。
- §7 の復帰条件の各行（ハッシュ不一致・closed completed・closed not planned・コメント削除・コメント編集・`gh` 不可・復旧）。
- `status`・`render`・`check` がネットワークを呼ばないこと（`finding_handoff_github` を呼んだら失敗するモックで固定）。
- PR #627 の F-606-29・F-606-30 相当（`harm: none`・`deferred`・`rounds` が11ラウンド連続・申し送り先 open）のフィクスチャで、`escalate` の偽陽性が出ないこと。
- 両 gate（`.claude/hooks/agent-command-gate.sh`・`.codex/hooks/agent-command-gate.sh`）が新 verb を `issue-fixer`・`pr-reviewer` に対して deny すること。
- 既存の golden（K-01〜K-04）が**無変更で通る**こと（記録の無いカルテの出力が不変）。

## 11. AC との対応表
| AC（#683） | 設計の箇所 |
|---|---|
| verb 1回で転記ブロック生成→投稿→読み戻し→照合→記録。照合失敗時は検証済みを書かない | §3・§4（`handoff-post`・失敗時は書かない） |
| 検証済み記録は verb だけが書ける。レポートの handoff 系キーは取り込みごと拒否 | §5（`review_block` の拒否）・§4（記録は `handoff_store` 経由） |
| 検証済み handoff を持つ `harm: none`・`deferred` が無進捗の計数と `★無進捗` に出ない。verdict 不変 | §6 |
| ハッシュ不一致・closed・コメント削除/編集・`gh` 不可で計数へ戻る（各試験） | §7・§10 |
| 全件再掲を跨いで記録が保持される試験 | §5・§10 |
| 最終検証時に再検証でき、不一致や closed を出力で指摘 | §4（`handoff-recheck`）・§7・§9 |
| 試験は `gh` をモックしてオフライン。`status` はネットワークを呼ばない | §4（`finding_handoff_github` の境界）・§10 |
| README・docstring の 2026-09-07 記述の書換え・経緯の移設・覆す根拠と既知の限界 | §2・§9 |
| SKILL ②-c の更新。是正当事者ロールが verb を実行できないことの機械確認 | §4（両 gate の deny を試験で固定）・§9 |
| Q1〜Q3 のオーナー決定と理由の記録 | §1 |
| PR #627 の F-606-29・F-606-30 相当で `escalate` の偽陽性が出ない | §10 |
| `unittest discover` が green・`maintainability_lint check` が通る | §8（baseline 変更なし） |

## 12. 他 Issue との関係
- **#691 / #786**：自動 deferred は本 PR の検証済み handoff（`HandoffRecord`・`finding_handoff_verify`）を再利用する。本 PR に triager・policy を入れない。
- **#513**：停止要件の機械強制は別。本 PR の偽陽性の削減が #513 の全 deny の前提になる。
- **#614**：`check` の診断網羅要求は変更しない。述語の単一点（`finding_handoff_exemption`）を共有できる形にしてある。
- **#375・#496 系**：保護モードの `disposition`/`scope` の保持は変更しない。`decide` の記録は handoff を触らない。

## 13. 未確認事項（実装時に確認）
- `block_records.py`・`status_text.py` が100行以内に収まるか（収まらなければ分割し、baseline は更新しない）。
- `gh api` の出力（コメントの `body`・`html_url`、Issue の `state`・`state_reason`）の形と、`gh` の最小バージョン。
- 旧版の `karte` が新カルテを読んで未知キーを拒否する前方非互換の範囲（ロールバック時のみ）。
- `.ai/skills/` と `.claude/skills/` の同期手順（`guidance_sync`・`asset_parity`）。
