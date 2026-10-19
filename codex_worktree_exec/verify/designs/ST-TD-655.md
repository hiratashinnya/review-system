# ST-TD-655 — 工程入力検査の未追跡分類見直し（システムテスト設計・受入基準）

- 作成：ac-designer（Claude Code (AI)）／phase: verification_design／VD ルート：`verification_design/VD-655.toml`
- Issue：#655／run_id：`run-655-20261018-01`／target_key：`issue-655-vd-r12`
- 入力 snapshot：`3e9d96ad68f0b8db6d0f22fc7f44b7ab60856f53`／入力 digest（trusted caller 値）：`be61723b06fdbcd42a6906c40e23212575b404dff669e634254edeed90628fc3`
- 入力の Issue 本文：r8〜r11 と同じ版（r7 の入力から、Scope 5 と Acceptance criteria に比較基準 案 (i) のオーナー決定と手順の変更範囲が追記された版。§1）。Acceptance criteria は上から数えて17項目で、本 VD は追記された項目（手順どおりの `coverage run` の失敗 test id 集合の一致）を AC16、lint と単体テストの項目を AC17 と呼ぶ（AC1〜AC15 の番号は r7 と同じ）。
- snapshot：r12 は `3e9d96a` を入力にした（オーナー決定（案A）で基準を採り直した）。r10・r11 は `92f7cc0144bf1776ff55b7ce835e87e8db7adf46` を、r6〜r9 は `2fe2cd57131048d04196867018c1c7d014794a5f` を、r4・r5 は `128a32b947e026523eb048cea074ce981512ba67` を、r3 は `5e38863322b4c207f35c8e998647bda89c3c966c` を入力にした。
  - `92f7cc0`..`3e9d96a` の差分は66ファイルで、PR #670（`asset_parity/` の分割、`.github/typechecked-files.txt`、`tests/unit/test_asset_parity_*`、`tests/designs|logs|reports` の asset-parity-637 の記録）、PR #673（`.github/skills/issue-pipeline/SKILL.md`・`.ai/rationale/issue-pipeline.md`・`.claude/tailoring-registry.md`）、PR #666（`karte/__init__.py`・`karte/path_io.py`・`karte/paths.py`・`tests/unit/test_karte_cli.py`・`maintainability_lint/baseline.json` と、commit `05868c3` の unittest discovery の是正）による。
  - `05868c3`（#318）は、`.github/workflows/tests.yml` の `unittest` job の2 step（`python3 -m unittest discover -s tests/unit` と `python3 -m unittest discover -s tests/issue_envelope -t .`）を1 step `python3 -m unittest discover tests`（同ファイル L61-62）に置き換え、`tests/issue_envelope/` を `tests/issue_envelope_tests/` に改名した（8ファイル）。理由は、top-level を `tests` とする discover で `tests/issue_envelope/` が source package `issue_envelope` を shadow するためである（`issue_envelope/verify/reports/AC-EVIDENCE-371.md`・`issue_envelope/verify/reports/TEST-DISCOVERY-318.md`）。あわせて `tests/unit/` の6ファイルの import を `tests.` から始まる形に直した。
  - 本 VD が path:行で引く文書・コードのうち、この差分で変わったのは `.github/workflows/tests.yml` だけである。`on:` の L38-40 は変わらない。r11 が先例として引いた L64-65 の `tests/issue_envelope` の専用 step は無くなった（影響は §1 と ST-TD-655-16 で扱う）。`docs/methods/codex-workspace-binding.md`・`codex_worktree_exec/`・`issue_start/`・`.ai/skills/coverage-html/SKILL.md`・`.claude/skills/coverage-html/SKILL.md`・`.coveragerc`・`docs/tools/issue-start-and-branch-source.md`・`.ai/agents/`・`tests/unit/codex_worktree_exec_support.py`・ST-TD-655-14 が名指しする7つの `tests/unit` module は変わらず、行番号は r3〜r11 と同じである。C7a の `tmp/_karte/.writer.lock` を作る `writer_lock` は `karte/path_storage.py:21-34` のままで（同ファイルは差分に無い）、作る path は変わらない（本 VD は karte の path:行を判定に使わない）。
  - `2fe2cd5`..`92f7cc0`、`128a32b`..`2fe2cd5`、`5e38863`..`128a32b` の差分は r11 までに確認したとおりで、本 VD が path:行で引くファイルを変えていない。
- 参照した調査報告：主文脈作業領域の `tmp/phase-inputs/655/investigation-report.md`（InvestigationReport、sha256 `2aab1bc46597cfa7f77bcd08df9b969c85362ed55d06a46532bed5e1bc64f7cc`）。これは issue-investigator の報告を主文脈が転記した md で、`issue_envelope` の artifact ID を持たない。ac-designer は InvestigationReport の producer ではないため envelope を代わりに作れず、VD の `input_refs`（artifact ID 参照）には載せない。照合は上記 sha256 で行う。
- 対応する TC：[ST-TC-655](ST-TC-655.md)。IT は [codex_worktree_exec IT-TD](IT-TD-655.md)・[issue_start IT-TD](../../../issue_start/verify/designs/IT-TD-655.md)

## 1. 前提（オーナー決定・覆さない既存契約）

- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 1「オーナー決定済み」と推奨節）：別 runtime cache は 3A（無視）を採らない。3B（拒否維持＋診断＋明示 prune）と 3D（発生源の隔離）を併用する。F-655-01〜03 は本 Issue で処置する。
- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 1「オーナー決定済み（2026-10-18）」）：ST/IT-TC のうち自動テストの実コード化は、工程 2a（test_design）で test-writer が `tests/<tool>/`（本 Issue では `tests/codex_worktree_exec/`・`tests/issue_start/`）に Red の実テストとして行う。これは、test-writer の成果物を UT-TD/UT-TC と定める契約文言（`.ai/agents/test-writer.md:9`、`.ai/skills/issue-pipeline/SKILL.md:39` の test_design 行）に対する、オーナー承認の例外である。本 VD はこれらの契約文言を ST/IT 実コード化の根拠として引かない。契約文言の是正は別 Issue #663 で扱い、ac-designer の是正を同一 branch で継続する契約の欠落は別 Issue #662 で扱う（いずれも Issue 本文 Scope 1 に記載）。feedback ledger への記録は #537 で扱う。
- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 5「オーナー決定済み（2026-10-18）」と AC16）：coverage-html の手順で全テストを走らせたとき、bytecode の指定だけを理由に検査系テストが失敗しないことを、手順の `coverage run` の失敗 test id の集合が、環境変数なしの `unittest discover`（同じ commit、`-s tests -t .`、同じ interpreter）の集合と一致することで判定する（比較基準の案 (i)）。このため手順の discover に `-t .` を加え、実行 interpreter を `--python` で固定し、`-p` は比較基準と同じ test module の集合になる指定に揃える。bytecode の指定の選択とテスト側の干渉への対処は CP が決める（P9）。ST-TD-655-13 の 7・8、P9 の (b) と P10 はこの決定を根拠とし、版管理されない作業領域のレビュー記録には依らない。
- 覆さない既存契約：`docs/methods/codex-workspace-binding.md`「read-only工程のprimary → linked準備」の (a) ignore 設定を許可根拠にしない（L278）、(b) 別 runtime・source 不一致の cache は拒否する（L306-307）、(c) 検査は read-only で cache を自動削除・書換えしない（L308）。C2（対応 source が作業面にも HEAD にも無い cache）を `<tag>` によらず C2 とすることと (b) の関係は、P2 が 2A の場合は ST-TD-655-07 の 4 で CP に根拠を記録させ、P2 によらず ST-TD-655-08 の 3 で契約本文の現在形の記述として判定する。
- snapshot `3e9d96a` で変わった前提（#318、PR #666 の merge）：Issue 本文の Scope 6 は「`tests/codex_worktree_exec/`・`tests/issue_start/` の suite を専用 step で実行する（先例は #371 の `tests/issue_envelope`）」と書き、AC14 は2つのディレクトリ名を名指しする。snapshot では先例の専用 step が無くなり、`unittest` job の全体 step は top-level を `tests` とする `python3 -m unittest discover tests` になった。この全体 step のもとでは、`tests/` 直下に source package と同名の package（`__init__.py` を持つディレクトリ）を置くと source package を shadow する（#318 が `tests/issue_envelope/` を改名した理由）。本 VD は Issue の文言どおり2つのディレクトリ名と専用 step を保ち、shadow を避ける形を P11 として CP に選ばせる（ST-TD-655-16）。ディレクトリ名を `tests/<tool>_tests/` に変える案は Issue AC14・Scope 6 の文言を変えるため本 VD では採らない。#318 の決定（全体 step を `discover tests` とする）を覆す場合は、その根拠を CP に記録させる（P11 の A）。
- 判定の基準点と未判定：各 TC を判定する commit（判定時点）、比較の基準にする commit（基準点）、手順を実行できない場合の扱い（未判定と不合格の区別）は、[ST-TC-655](ST-TC-655.md) 冒頭の規則 (1)〜(4) で全 AC に共通に定める。本書の「判定時点」「基準点 P」「未判定」はその定義を指す。

## 2. 分類（本 VD の語彙）

名前の規則（R-PYC）：ファイル名が正規表現 `^[A-Za-z_][A-Za-z0-9_]*\.[a-z][a-z0-9]*-[0-9]+(\.opt-[12])?\.pyc$` に完全一致すること。`<stem>` は最初の `.` の前、`<tag>` は2番目の要素（例 `cpython-312`）。現行 tag は実行中の `sys.implementation.cache_tag`。R-PYC は、下記の優先順位 0 で通らなかった `.pyc` を、優先順位 1 で C0 とするか優先順位 3 で C2・C3・C6 などに振り分けるかを決めるためだけに使う。優先順位 0 の (d) の判定には R-PYC を使わない。

| 記号 | 対象 | Issue 観測 |
|---|---|---|
| C0 | 未承認の通常 source と緩和対象外の compiled file：tmp 外の未追跡 `.py`・TC・設定、tmp 内の `.py`、`.pyo`（場所を問わない。`__pycache__` 配下を含む）、R-PYC に一致しない `.pyc`、`__pycache__` 外の `.pyc`、下記 C1〜C8 のどれにも当たらない未追跡ファイル（下記の優先順位 0 で通すもの＝`tmp/` 配下6拡張子の通常ファイル・既存2 lock・登録済みの別 linked worktree 内のファイル・生成元検証に合格する `__pycache__` 配下の `.pyc` は除く） | 負例（必ず拒否） |
| C1 | 外部製品の runtime lock：`.claude/scheduled_tasks.lock`（repo ルート直下の `.claude/` のみ） | #1 |
| C2 | 孤児 cache：親が `__pycache__` で名前が R-PYC に一致し、対応 source が作業面にも HEAD にも存在しない | #2 |
| C3 | 別 runtime cache：親が `__pycache__` で名前が R-PYC に一致し、`<tag>` が現行 tag と異なり、対応 source は HEAD と一致して作業面に存在する | #3 |
| C4 | 計測ツール副産物：`.coverage`、`.coverage.*`、`htmlcov/**`（いずれも repo ルート直下） | #4 |
| C5 | 外部ツール領域：`.serena/**`（repo ルート直下） | #5 |
| C6 | 現行 runtime の stale cache：親が `__pycache__` で名前が R-PYC に一致し、`<tag>` が現行 tag、source も HEAD と一致するが、code bytes が現行 source の compile 結果と異なる | #6 |
| C7 | harness 自身の生成物：C7a `tmp/_karte/.writer.lock`、C7b `tmp/_adr-notify/<sha256>.root`、C7c `tmp/pr-diffs/pr-<N>-<hex>.diff`、C7d `tmp/_feedback/*.toml`、C7e ADR root 直下の `.write.lock`／`.file-issue.lock`。ADR root は repo 直下の1階層のディレクトリ `<tool>` に対する `<tool>/adr/`（`.ai/agents/creation-stage-contract.md:42` の配置。snapshot で実在するのは `issue_envelope/adr/`・`issue_start/adr/`） | #7 |
| C8 | tmp 内の許可拡張子外の残置（`.sh`・`.out` 等）。拡張子が `.py`・`.pyc`・`.pyo` のファイルは含めない | #8 |

分類の優先順位（上から順に適用し、どの未追跡ファイルも、0 で分類せず通すか、1〜4 のどれかで1つの分類に決まる）：

0. base で既に通る未追跡ファイルは分類せず通す（C0〜C8 のどれにもしない）。対象は `docs/methods/codex-workspace-binding.md:297-300` の例外の範囲そのままで、本 Issue はこの範囲を広げも狭めもしない。(a) `tmp/` 配下の通常ファイルで拡張子が `.json`・`.md`・`.yaml`・`.yml`・`.txt`・`.log` のもの、(b) 既存2 lock（`.ai/feedback/.writer.lock`・`tmp/_worktree/ledger.json.lock`）、(c) Git に登録された別 linked worktree の中のファイル、(d) `__pycache__` 配下の `.pyc` で、同文書 L301-305 の生成元検証（対応 source が HEAD の通常 `.py` と作業面 bytes で一致し、cache の path が現行 tag と optimization 0・1・2 のどれかについての `importlib.util.cache_from_source` の値に一致し、cache の code bytes が現行 source の compile 結果と一致）に合格するもの。(d) は名前が R-PYC に一致するかを問わない（例：HEAD と作業面で一致する `my-tool.py` から標準 compiler で作った `__pycache__/my-tool.<現行tag>.pyc` で code bytes が一致するものは、stem が識別子でなくても通る。非 ASCII 名の module の cache も同じ）。symlink は (a)〜(d) に当たらない（L300）。(a)〜(d) の個々の判定条件は snapshot の実装（`codex_worktree_exec/source_snapshot.py:23-38`・`codex_worktree_exec/compiled_cache.py`）どおりとする。
1. 0 で通らなかったファイルのうち、拡張子が `.py`・`.pyo` のファイル、R-PYC に一致しない `.pyc`、`__pycache__` 外の `.pyc` は、C1〜C8 の定義に重なる場合も C0 とする（例：`tmp/x.pyc`、`tmp/__pycache__/x.cpython-312.pyo`、`.serena/x.py`、code bytes が一致しない `__pycache__/my-tool.<現行tag>.pyc` はすべて C0）。
2. `tmp/` 配下で C7 に当たるファイルは C8 ではなく C7 とする。
3. R-PYC に一致する `__pycache__` 配下の `.pyc`（`tmp/` 配下を含み、0 の (d) で通るものを除く）は C2・C3・C6 のどれかとし、どれにも当たらないもの（source が HEAD のみ・未追跡・作業面で改変など）は、IT-TD-655-CWE-03 の CP 対応表が定める拒否分類に入る。C8 には入らない。
4. 0〜3 のどれにも当たらず C1〜C8 のどれにも当たらない未追跡ファイルは C0 とする。

## 3. 方式の語彙と、1b（ChangePlan）で確定するパラメータ

方式（P1 の語彙）：

| 記号 | 方式 | 判定 |
|---|---|---|
| M1 | 許可（exact path） | ST-TD-655-06 を満たすこと |
| M2 | 自動検出して無視 | C2 だけに使える。ST-TD-655-07 を満たすこと |
| M3 | 拒否＋回復コマンド（P6） | 回復コマンドの対象は ST-TD-655-15 の範囲（`__pycache__` 配下の未追跡 `.pyc`）なので、C2・C3・C6 だけに使える |
| M4 | 拒否＋案内 | 回復コマンドを持たない。診断に分類識別子・件数・代表例と、空でない案内文（承認経路または手動の対処手順）を出す。回復コマンドの条件は課さない |
| M5 | 発生源の隔離 | 生成元の出力先を作業面外へ移す。既に作業面に残るファイル（残置）は M5 では通さず、CP が残置ごとに M1・M3・M4 のどれかを定めて判定する |

分類ごとに選べる方式：C0＝M4（承認経路の案内）固定。C1・C4・C5＝M1・M4・M5。C2＝M2・M3。C3＝M3（M5 の併用は ST-TD-655-13 で判定）。C6＝M3。C7a〜C7e＝M1・M5（P3）。C8＝M1・M4。1分類で複数の方式を組み合わせる場合、CP は各方式が当たる条件（M1 の exact path、M2 の条件）を記録し、どのファイルにも方式が1つに決まるようにする。M2 以外の方式で、ディレクトリ・prefix・ワイルドカード・拡張子の照合によって検査を通すことはしない（Issue Out of scope）。

M3 を C2・C3・C6 に限る理由：C5（設定・memories を含み再生成できない可能性）と C8（生成元が未確定で手作業由来の可能性）は削除コマンドの対象にすると取り消せない損失になりうる。C4 は M5（Scope 5）で新規発生を止め、残置は M1 または M4 で扱える。C7 は Issue Scope 1 が「生成元で場所を変えるか exact path 許可に追加するか」の比較を求めている。

次の値は本 VD では決めない。CP が値を確定し、各 AC はその値で判定する。CP に値が無い場合は、その AC を判定不能として不合格にする（CP は本 PR の内容なので、[ST-TC-655](ST-TC-655.md) 冒頭 (4) の未判定には当たらない）。

| 記号 | 内容 | 制約（本 VD が固定する範囲） |
|---|---|---|
| P1 | C1〜C8 の各分類（C7 は C7a〜C7e ごと）の方式 | 上記の「分類ごとに選べる方式」に限る。M5 を選ぶ分類は残置の方式も記録する |
| P2 | C2 の方式（2A＝M2／2B＝M3） | 2A を採る場合は ST-TD-655-07 を満たすこと |
| P3 | C7 の扱い（M5 生成元で作業面外へ移す／M1 exact path 許可に追加） | M1 の場合は ST-TD-655-06 を満たすこと |
| P4 | 集約診断の出力形式（stderr 1行を維持するか、契約を改めるか） | どちらでも ST-TD-655-03・12 の必須要素を含むこと |
| P5 | 分類ごとの代表例の最大件数 N | N は1以上の整数定数 |
| P6 | 回復コマンド（prune 等）の名前・引数 | 1回の起動で完了すること。対象は ST-TD-655-15 の範囲に限る |
| P7 | 診断の分類識別子の語彙 | 分類ごとに一意で、正規表現 `^[A-Za-z0-9_.:-]+$` に一致する固定文字列 |
| P8 | `readonly_workspace` 準備経路の失敗識別子 | 正規表現 `^ISSUE_START_[A-Z0-9_]+$` に一致する固定文字列 |
| P9 | coverage-html の手順の `coverage run` に付ける (a) bytecode の指定（`PYTHONPYCACHEPREFIX=` と `PYTHONDONTWRITEBYTECODE=1` のどちらか）、(b) 実行 interpreter の指定（`uv run` の `--python` に渡す値 V）、(c) その指定のもとでテスト（本 Issue で追加するテストを含む）が干渉して失敗する場合の対処。対処が不要と判断する場合は、その判断と根拠 | (a) は ST-TD-655-13 の 2・3 を満たす1つに限る。(b) は空でない1つの値で、3a 環境の `python3` と同じ interpreter を uv に選ばせるもの（`--python` で固定することは §1 のオーナー決定（一次記録は Issue #655 本文 Scope 5）による。一致は ST-TD-655-13 の 8 の (b) で判定する）。discover の引数（top-level・start directory・pattern）は P9 で選ばず、ST-TD-655-13 の 7 で固定する。(c) の結果が ST-TD-655-13 の 8 を満たすこと |
| P10 | ST-TD-655-13 の 8（AC16）の測定手順：(a) 手順の `coverage run` が使った interpreter と、比較基準の `python3` の interpreter をそれぞれ記録する手順（記録のための起動の組み立てと、手順の行の uv オプション・環境変数代入の扱いを含む）と、2つの記録を同じ interpreter と判定する比較方法。(b) 手順の `coverage run` と比較基準の出力から、失敗 test id の集合を取り出す規則（対象とする行、id の切り出し、正規化の有無） | (a) の記録は、手順の `coverage run` を手順の行どおりに起動したときに実際に使われる interpreter を表す（行の uv オプションや環境変数代入で interpreter の選択が変わる場合も、その選択を反映する）。比較方法は、少なくとも Python の version と `sys.implementation.cache_tag` の違いを区別する。(b) は両方の出力に同じ規則を適用し、unittest が `FAIL` または `ERROR` として報告した test をそれぞれ1件の id として取り出す（報告された test を落とさず、別々の test を同じ id にまとめない） |
| P11 | 追加する2つの suite（`tests/codex_worktree_exec/`・`tests/issue_start/`）を CI で実行する形。(A) 2つのディレクトリを package（`__init__.py` あり）にし、専用 step の run を `python3 -m unittest discover -s tests/<suite> -t .` とし、`unittest` job の全体 step（snapshot の `.github/workflows/tests.yml:61-62`、`python3 -m unittest discover tests`）の run を `python3 -m unittest discover -s tests -t .` に変える（top-level を `tests` のままにすると2つの package が source package `codex_worktree_exec`・`issue_start` を shadow するため）。(B) 2つのディレクトリを package にせず（`__init__.py` を置かない）、専用 step の run を `python3 -m unittest discover -s tests/<suite>` とし、全体 step は変えない（unittest の discover は `__init__.py` の無いディレクトリへ再帰しないので、2つの suite は全体 step では実行されず、専用 step だけで実行される） | A か B のどちらか1つ。CP は選んだ理由と、もう一方の却下理由を記録する（B の場合は、全体 step と coverage の計測で2つの suite が実行されないことの扱いを含む）。A の場合は、全体 step の変更が #318（PR #666。`issue_envelope/verify/reports/TEST-DISCOVERY-318.md`）の決定を覆さない根拠、または覆す根拠も CP に記録する（`.claude/rules/01-principles.md`「意図的設計の尊重」）。どちらの場合も suite のディレクトリは Issue AC14・Scope 6 のとおり `tests/codex_worktree_exec/`・`tests/issue_start/` とする |

## 4. 受入基準（ST-TD）

「1b依存」欄の「なし」は CP の決定によらず判定できる AC、「P*」はそのパラメータで判定基準が確定する AC を表す。判定時点（merge 前の最終 head commit H か、merge 後の `mergeCommit` M か）、比較の基準点（P など）、手順を実行できない場合の未判定と不合格の区別は、[ST-TC-655](ST-TC-655.md) 冒頭の規則 (1)〜(4) で決まる。本書で「検査」「検査が通る」「拒否」は、特記なき限り、`verify_untracked_sources` と、`source_changes` を空にした `verify_source_snapshot` の両方について言い、両方で満たすときだけ満たすとする（ST-TC-655 冒頭 (5)）。

### ST-TD-655-01 方式と理由の記録（Issue AC1・Scope 1）
- 1b依存：P1・P2・P3
- 合格条件（すべて満たす）：
  1. CP または CP が参照する ADR に、C1〜C8（C7 は C7a〜C7e ごと）の12行（C1〜C6・C8 の7行と C7a〜C7e の5行）それぞれについて、方式（§3 の分類ごとに選べる方式）、選定理由（空でない）、不採用案ごとの却下理由（空でない）が記録されている。M5 の行には残置の方式もある。
  2. CP が、3A 不採用の根拠としてオーナー決定の一次記録（Issue #655 本文、または feedback ledger の該当エントリ）を参照している。オーナーの逐語を CP・ADR へ複製することは求めない。1B（`--exclude-standard` 等で ignore を一律除外）は契約 (a) 違反として却下されている。
  3. M3 の行には回復コマンド（P6）が、M4 の行には案内文が記録されている。
  4. M5 を選んだ C1・C5 の行には、生成元の出力先を作業面外へ移す設定（設定の path とキーまたはオプション）と、その設定で生成物が作業面の外に出ることの根拠（出典つき）が記録されている（C1・C5 の M5 の出力先は、他の AC では判定しないため本項で判定する）。
- 判定方法：文書検査（ST-TC-655-01-1）。

### ST-TD-655-02 分類ごとの回帰テスト（Issue AC2）
- 1b依存：P1
- 合格条件：一時 git リポジトリの fixture で C1〜C8 を1分類ずつ置き、各ファイルが P1 で定めた方式どおりの結果になる。次の各項目（例外の有無、拒否、診断の内容、回復コマンド後の結果）は、方式（M1〜M5）によらずすべて、`verify_untracked_sources` と、`source_changes` を空にした `verify_source_snapshot` の両方で判定し、両方で満たすときだけ満たすとする。
  - M1・M2 のファイル：例外を送出しない。
  - M3 のファイル：診断に、その分類の識別子、置いた件数と一致する件数、代表例1件以上、回復コマンドが含まれる。続けて回復コマンドを1回だけ起動すると、例外を送出しない。
  - M4 のファイル：診断に、その分類の識別子、置いた件数と一致する件数、代表例1件以上、空でない案内文が含まれる。
  - M5 の分類：fixture に置いたファイルは残置として扱い、CP が定めた残置の方式（M1・M3・M4）で上の各項目どおりに判定する。生成元の出力先は本 AC ではなく、C3・C4 は ST-TD-655-13、C7 は ST-TD-655-10、C1・C5 は ST-TD-655-01 の 4 で判定する。
- 判定方法：自動テスト（ST-TC-655-02-1〜02-8）。

### ST-TD-655-03 違反の分類別集約（Issue AC3）
- 1b依存：なし（出力形式は P4）
- 合格条件：方式が拒否に固定された分類 C0・C3・C6 を各2件置いた fixture で、検査の各関数を1回だけ呼ぶ。
  1. 関数ごとに、例外は1回だけ送出される。
  2. 診断に、置いた全分類の識別子があり、分類ごとの件数が置いた件数と完全に一致する。
  3. ファイル名を変えて `git ls-files` の列挙順を入れ替えても（例：C0 の違反が最初になる名前と最後になる名前）、2 の結果は変わらない。
- 閾値：分類の欠落0件、件数誤差0件。
- 判定方法：自動テスト（ST-TC-655-03-1・03-2）。

### ST-TD-655-04 負例：未承認 source の拒否維持（Issue AC4）
- 1b依存：なし
- 合格条件：次の各ファイルを1件ずつ未追跡で置いたとき、`.gitignore`・`.git/info/exclude`・`core.excludesFile` のどれにも載せない場合、どれか1つに載せた場合、3つ全部に載せた場合のすべてで、検査が拒否し、そのファイルが C0 として件数1で数えられる。
  - `source.py`（ルート）、`pkg/module.py`、`tests/unit/test_extra.py`、`tool/config.toml`、`tmp/injected.py`
  - 許可・無視の名前に似せたもの：`sub/.claude/scheduled_tasks.lock`（別ディレクトリの同名）、`__pycache__` 配下の `.py`、`__pycache__/module.pyc`（R-PYC に一致しない名前）、`__pycache__` 外の `module.pyc`
  - tmp 内の compiled file（§2 の優先順位 1 で C8 ではなく C0）：`tmp/x.pyc`、`tmp/__pycache__/x.<現行tag>.pyo`
  - `source_changes` に path と正しい sha256 を渡しても、上の未追跡ファイルは `verify_source_snapshot` で拒否される。
- 閾値：拒否されないケース0件。
- 判定方法：自動テスト（ST-TC-655-04-1・04-2）。

### ST-TD-655-05 負例：現行 runtime cache の source 一致検証を維持（Issue AC5）
- 1b依存：なし
- 合格条件：
  1. `tests/unit/test_codex_compiled_cache.py` の既存の拒否ケース（source の HEAD 不一致、旧 version の cache、header 不正、未対応 tag）が、同じ入力で引き続き拒否される。比較の基準は本 PR の merge 直前の base tip である基準点 P（[ST-TC-655](ST-TC-655.md) 冒頭 (3)。snapshot ではない）で、判定は M で行う。(a) P の同ファイルの test method 名（class 名と method 名の組）がすべて M の同ファイルにある（削除・改名していない）。(b) M で同ファイルを実行して失敗・エラーが0件。(c) Python の `ast` で数えた、属性名が `assertRaises` または `assertRaisesRegex` の呼出しの数が、M で P 以上（拒否メッセージの文字列を変える場合も、拒否であることを確かめる assertion は削らない）。P を定められなければ未判定とする。
  2. C2 の判定（2A を採る場合）が、次の場合に適用されず拒否のまま残る：source が HEAD にあり作業面だけで削除されている、source が作業面にあり未追跡、source が作業面で改変されている、HEAD に無い source の位置に空のディレクトリがある（`lexists` が真）。
  3. 現行 tag の cache で、source が HEAD と一致するが code bytes が異なるもの（C6）は、回復コマンドの実行前は拒否される。
- 閾値：既存拒否ケースの通過0件。
- 判定方法：自動テスト（1 は ST-TC-655-05-1、2 は ST-TC-655-05-2、3 は ST-TC-655-05-3）。

### ST-TD-655-06 許可・無視の範囲（Issue AC6・Out of scope）
- 1b依存：P1・P3（M1 を使わない場合も 2〜4 を判定する。1 は追加エントリが無ければ満たすものとする。2・3 は、追加エントリと既存の exact 2 lock（§2 の優先順位 0 の (b)）の両方に適用する）
- 追加エントリ：検査コードの exact path 許可表のエントリのうち、M にあって基準点 P（[ST-TC-655](ST-TC-655.md) 冒頭 (3)）に無いもの（本 PR が加えたもの。snapshot 以後に base 側で加わったエントリは含めない）。P を定められなければ 1 と 4 は未判定とする。
- 合格条件：
  1. 追加エントリはすべて、repo 相対の exact path 文字列であり、`*`・`?`・`[` を含まず、末尾が `/` でない。照合は完全一致で、prefix 一致・ディレクトリ一致をしない。
  2. 許可の照合は、regular file かつ path の全要素が symlink でない場合だけ成立する。
  3. 許可した各 path（既存の exact 2 lock を含む）について、(a) その path が symlink、(b) その path の親ディレクトリが symlink、(c) 同じ basename を別ディレクトリに置いたもの、のいずれも拒否される。
  4. P から M までの差分で、M2（C2）以外に、ディレクトリ・prefix・ワイルドカード・拡張子の照合で検査を通す分岐が加わっていない。C1・C4・C5・C7・C8 の置き場と同じディレクトリまたは同じ拡張子で、M1 のどのエントリとも完全一致しないファイルは拒否される（base に既存の `tmp/` 配下6拡張子の例外は対象外）。
- 判定方法：差分の文書検査と自動テスト（ST-TC-655-06-1・06-2）。

### ST-TD-655-07 孤児 cache の無視条件と実証（Issue AC7）
- 1b依存：P2。2B を採る場合は、下の合格条件 1〜4 を適用せず、CP に P2 が 2B であることと 2A 不採用の理由（空でない）が記録されていることだけで判定する（ST-TD-655-02 など他の AC の結果は使わない）。CP に P2 が無い場合は §3 の規則により不合格。
- 合格条件（2A を採る場合）：
  1. 次の4条件をすべて満たす cache だけが無視される。条件を1つだけ外した fixture では、すべて拒否される。
     (i) 親ディレクトリ名が厳密に `__pycache__`、(ii) ファイル名が R-PYC に一致する、(iii) 対応 source が作業面に無く（`lexists` が偽）かつ HEAD にも無い、(iv) regular file で path の全要素が symlink でない。
  2. 実証記録が `codex_worktree_exec/verify/logs/` に commit されている。記録は現行 runtime（`python3`）で、timestamp・checked-hash・unchecked-hash の3種の cache それぞれについて、source を削除した後の `import` が `ModuleNotFoundError` になり、cache に埋めた副作用（marker ファイル作成）が実行されないことを示す。実行コマンド、Python の version と `sys.implementation.cache_tag`、終了コード、出力を含む。
  3. 無視した cache の source が後から HEAD に現れた fixture（別内容で commit）では、次の検査がその cache を通常の検証で拒否する。
  4. CP が次の3点を記録している。
     - 実証の範囲が import 経路であることと、`python3 <cache path>` のような直接 path 実行を検査の脅威範囲外とする判断（または範囲内とする対策）。
     - 現行と異なる `<tag>` の孤児 cache も C2 に含める根拠（2 の実証は現行 runtime だけで行うため、他 version の CPython も対応 source の無い `__pycache__` 配下の cache を import しないことの根拠と、その出典）と、それが 3A 不採用の理由（対応 source が存在する別 runtime cache を、その version の runtime が import しうること）に当たらないこと。
     - C2 を `<tag>` によらず定めることが契約 (b)（`docs/methods/codex-workspace-binding.md:306-307` の、別 source・別 runtime・未対応 compiler 形式の cache を拒否する定め）を覆さない根拠、または (b) の適用範囲の読み（例：(b) の別 runtime を理由とする拒否は対応 source が作業面にある cache に対するもので、対応 source が作業面にも HEAD にも無い cache には及ばない）と、その読みの根拠。
- 判定方法：2A の場合は自動テスト（ST-TC-655-07-1・07-2）と、実証ログと CP の文書検査（ST-TC-655-07-3）。2B の場合は CP の文書検査（ST-TC-655-07-3）だけで、07-1・07-2 は実行しない。

### ST-TD-655-08 不変条件・read-only 性・契約文書（Issue AC8・F-655-02）
- 1b依存：なし（版判断の結論は CP）
- 合格条件：
  1. 本 PR が加えた差分が、`.codex/config.toml`、`codex_worktree_exec/profile_pin.py`、`codex_worktree_exec/project_trust.py`、`codex_worktree_exec/worktree_binding.py` で0行である（D1 profile pin・read-only profile・project trust・D5）。本 PR が加えた差分とは、判定時点の PR の base branch（`main`）の tip B と PR の最終 head commit H の merge-base から、H までの差分（`git diff B...H` の三点記法）をいう。snapshot 以後に base branch 側でこれらのファイルが変わっていても、本 PR が加えた変更でなければ判定に含めない。判定時点は merge 前（H）。
  2. C0〜C8 をすべて置いた fixture で検査を呼ぶ前後で、`.git` を除く作業面の全ファイルの（相対 path、種別、size、sha256、mode、`mtime_ns`）の集合と、`git status --porcelain=v1 -z --ignored` の出力が一致する。検査が通る場合と拒否する場合の両方で確かめる。
  3. `docs/methods/codex-workspace-binding.md` の「未追跡通常source…」段落（snapshot 時点の L296〜313）が新しい分類と方式を現在形で記述し、旧記述に訂正を追記する形になっていない。同文書末尾の「本是正は同一PR内の2.0遷移の補完であり…」の文が残っていない。加えて、書き換えた段落が次の2点を現在形で述べている：(i) 孤児 cache（対応 source が作業面にも HEAD にも無い `__pycache__` 配下の cache）は `<tag>` によらず C2 として扱うこと（方式は P2）、(ii) 別 runtime（現行と異なる tag）を理由とする拒否は、対応 source のある cache に限ること。
  4. 版付き文書の bump 要否の判断が `.ai/guidance/common.md`「正本・実装規約」に従って CP に記録され、M の内容がその判断と整合している。判定は M で行い、比べる旧版は基準点 P（[ST-TC-655](ST-TC-655.md) 冒頭 (3)）の値とする（snapshot の値や literal `issue-start/2.0` とは比べない。P を定められなければ未判定とする）。
     - 値の取り出し：V0 は P の、V1 は M の `issue_start/gate_support.py` で、行頭が `ISSUE_START_POLICY_VERSION = "` で始まる代入行の `"` で囲まれた文字列とする。M にその代入行がちょうど1つ無ければ不合格。P にちょうど1つ無ければ未判定。
     - 旧版の検索：M の追跡ファイル全体（`git grep -n -F <V0> M`）で、V0 の直後が数字でない出現を含む行を集める。次の (h1)(h2) に当たる行を除いた残りを「旧版を現行として述べる行」とする。(h1) 版の遷移を述べる履歴記述：同じ行に V0 と、V0 と異なる `issue-start/<数字>.<数字>` の literal の両方があり、かつ「から」と「へ」、または `→` がある行（例：`docs/tools/issue-start-and-branch-source.md:39`）。(h2) 記録・検証成果物とテスト：path が `tests/` 配下、`verify/`・`verification_design/`・`change_plan/`・`adr/` を path 要素に含むもの、`.ai/feedback/`・`.ai/rationale/`・`archive/`・`doc-system-v1-archive/` 配下のファイル（時点の値を保存する記録であり、テストの値と定数の整合は ST-TD-655-14 のテスト実行で確かめる）。
     - bump する場合：CP が bump の区分（MAJOR か MINOR）と、その区分の理由（空でない）を記録している。V1 は正規表現 `^issue-start/(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$` に一致し、V0 から CP の区分どおりにちょうど1段上がった値である（V0 を `issue-start/<a>.<b>` とすると、MAJOR なら `issue-start/<a+1>.0`、MINOR なら `issue-start/<a>.<b+1>`）。旧版を現行として述べる行が0件である。
     - 据え置く場合：V1 が V0 と同じである。CP に据え置きの判断と理由（空でない）がある。版を据え置く旨とその理由を述べる文が、`docs/methods/codex-workspace-binding.md` か、旧版を現行として述べる行を含むファイルのどれかの本文にある。
     - CP に版判断が無い、または bump・据え置きのどちらの条件も満たさなければ不合格。
- 判定方法：差分検査・自動テスト・文書検査（ST-TC-655-08-1〜08-3）。

### ST-TD-655-09 削除 pull と別 runtime 実行の再現（Issue AC9）
- 1b依存：P1・P2・P6
- 合格条件：
  1. 削除 pull：source を2件 commit し、現行 runtime で import して cache を作る。別 clone で1件の削除を commit し、元の作業面で `git pull --ff-only` する。その後、検査が通る。または回復コマンドを1回起動した後に検査が通る。オーナー許可の手作業削除を手順に含まない。
  2. 別 runtime（模擬）：HEAD と一致する source の `__pycache__` に、現行と異なる tag の cache を3件置く。回復前は C3 として拒否され、診断に件数と回復コマンドが出る。回復コマンドを1回起動した後は検査が通る。
  3. 別 runtime（実機）：3a で、本 PR の `mergeCommit` M の作業面で `uv run --python <W>`（W は現行と異なる version）で起動した Python が作業面の module を import した後に、回復前は C3 として拒否され、診断に C3 の件数（作られた現行と異なる tag の cache の数と一致）と回復コマンドが出て、回復コマンドを1回起動した後は検査が通る。
- 判定方法：自動テスト（ST-TC-655-09-1・09-2）と 3a の実機確認（ST-TC-655-09-3）。3 の手順を [ST-TC-655](ST-TC-655.md) 冒頭 (4) の (u1)・(u2)（uv が無い、W の interpreter が無い）で実行できない場合は STOP して未判定とし、AC9 を合格とも不合格ともしない。3 の実行の有無・結果は他の AC の判定に使わない。

### ST-TD-655-10 harness 生成物で止まらない（Issue AC10・観測 #7・F-655-01）
- 1b依存：P3（検査が通ることは P3 の選択によらず求める。CP に P3 が無ければ §3 の規則により不合格）
- 合格条件：一時 repo で次の生成元の実コード経路を実行した後、検査が通る（C7 は M1・M5 のどちらかなので回復コマンドを要しない）。
  - `karte append`（`tmp/_karte/.writer.lock`）、`adr new-entry`（`tmp/_adr-notify/*.root` と ADR root の `.write.lock`）、ADR の `file-issue` 経路（`.file-issue.lock`）、`gitgate show-pr-diff` の差分ファイル保存経路（4096 byte を超える差分）、feedback 下書き保存（`tmp/_feedback/*.toml`）
  - P3 で M5 とした生成元：生成物の実 path が作業面の外にある。
  - P3 で M1 とした生成物：実 path が CP の M1 のエントリのどれかと完全一致する（ST-TD-655-06 の条件は AC6 で判定し、本 AC の合否には使わない）。
- 判定方法：自動テスト（ST-TC-655-10-1）。

### ST-TD-655-11 内容だけ変わる pull（Issue AC11・観測 #6）
- 1b依存：P6
- 合格条件：source を commit して現行 runtime で cache を作り、別 clone で同じ source の内容だけを変える commit を作って `git pull --ff-only` する。回復前は C6 として拒否され、診断に件数と回復コマンドが出る。回復コマンドを1回起動した後は検査が通る。
- 判定方法：自動テスト（ST-TC-655-11-1）。

### ST-TD-655-12 全経路の集約診断・識別子付きエラー（Issue AC12・F-655-03）
- 1b依存：P4・P5・P7・P8
- 合格条件：
  1. 次の4経路それぞれで、ST-TD-655-03 と同じ fixture から、置いた全分類の識別子と件数を含む診断が1回の失敗で出る。`codex_worktree_exec.artifact_binding.verify_artifact_binding`（`CODEX_EXEC_BINDING_INVALID`）、`issue_start.phase_dispatch.validate_phase_dispatch`（`ISSUE_START_PHASE_BINDING_INVALID`）、`issue_start.readonly_workspace`（P8）、`issue_start.pr_rereview.validate_pr_rereview`（`ISSUE_START_PR_REREVIEW_INVALID`）。
  2. `python3 -m issue_start.readonly_workspace` の準備で未追跡検査が失敗したとき、終了コードが0以外で、stderr に P8 の識別子があり、`Traceback` を含まない。
  3. 各分類の診断は、分類識別子（P7）、件数、代表例1件以上 N 件以下（P5）、回復手順（M3 は回復コマンド、M4 は案内文。C0 は承認経路の案内。空にしない）を含む。1分類に300件を置いた fixture でも代表例は N 件以下で、件数は300と表示される。
  4. 診断の行数が、P4 で記録した契約と一致する（テストで固定する）。
- 判定方法：自動テスト（ST-TC-655-12-1〜12-3）。本 AC の「検査」は4経路の入口であり、§4 冒頭の2関数の規則は 3 の300件の fixture（ST-TC-655-12-3）に適用する。

### ST-TD-655-13 coverage 実行で作業面に残さない・手順書の整合（1〜4＝Issue Scope 5、5＝AC13、6＝AC15、7・8＝AC16）
- 項目と合否の対応：1〜4 は Issue Scope 5 の「手順のコマンドに出力先を作業面外へ出す指定を加える」（4 は他 PF の写しが欠けないこと）、5 は AC13、6 は AC15（Claude 側 wrapper を含む）、7・8 は AC16（§1 の比較基準 案 (i) のオーナー決定）に対応する。Scope 5（1〜4）・AC13・AC15・AC16 の合否は、それぞれ対応する項目の条件だけで決め、他の項目の合否を使わない。AC16 は 7 と 8 の両方を満たすときだけ合格とする。ST-TR にはこの4つの合否を別々に記録する。2・3 は他の項目が使う指定方法と作業面外の定義であり、それ自体で合否を持たない。
- 1b依存：P9（bytecode の指定と実行 interpreter の指定の選択と、テスト側の干渉への対処）・P10（8 の測定手順）。5 と 7 の判定条件は P9・P10 の選択によらない
- 合格条件：
  1. `.ai/skills/coverage-html/SKILL.md` の手順の3コマンドそれぞれで、次の出力先が作業面外に指定されている。
     - `coverage run`：coverage data file と bytecode の出力先
     - `coverage html`：coverage data file と HTML 出力先
     - `coverage report`：coverage data file
  2. 指定として認めるのは次だけである。(i) そのコマンド行の環境変数代入またはオプション（data file は `COVERAGE_FILE=` または `--data-file`、HTML は `-d`／`--directory`、bytecode は `PYTHONPYCACHEPREFIX=` または `PYTHONDONTWRITEBYTECODE=1`）。(ii) data file と HTML 出力先に限り、追跡済み `.coveragerc` の `[run] data_file` と `[html] directory`。別のコードブロックや手順外の `export`、利用者のシェル設定・環境での指定は認めない。bytecode の指定は P9 で CP が選んだ方とする。data file または HTML 出力先に複数の指定がある場合は、coverage が実際に使う1つを判定に使う。その優先順位は、オプション（`--data-file`・`-d`／`--directory`）、環境変数代入（`COVERAGE_FILE=`）、`.coveragerc` の順とする（例：snapshot の `.coveragerc` は `[html] directory = htmlcov` なので、`coverage html` の行に `-d` が無ければ HTML 出力先の指定値は `htmlcov` になる）。同じ優先順位の指定が1つのコマンド行に2つ以上ある場合は、その出力先は指定されていないものとする。
  3. 作業面外の定義。指定値（下記の取り出し方で得た文字列）が作業面外であるとは、次の手順で得た絶対 path X が、判定に使う worktree で `git worktree list --porcelain` が列挙するすべての worktree の root（primary checkout と全 linked worktree）のどれとも一致せず、どの root の配下（root に `/` で続く path）にもないことをいう。判定に使った worktree の一覧と X を ST-TR に記録する。1・6 (i)(ii)・ST-TC-655-13-1 の (A)(B) はすべてこの定義を使う。
     - (α) 指定値が `/` で始まる場合：X は指定値を字句的に正規化したもの（`os.path.normpath` と同じく `.`・`..`・連続する `/` を解決する。例：`/tmp/../<worktree root>/htmlcov` の X は `<worktree root>/htmlcov` で作業面外ではない）。
     - (β) 指定値が環境変数参照で始まる場合：参照の形は `$NAME`・`${NAME}`・`${NAME:-default}`（default は `$`・バッククォート・`}` を含まない文字列）だけを認め、NAME は許可する名前 `TMPDIR`・`HOME`・`XDG_CACHE_HOME` のどれかに限る（許可する名前の一覧であり、`PWD`・`CLAUDE_PROJECT_DIR`・`GITHUB_WORKSPACE` などそれ以外の名前は作業面外としない）。さらに `.ai/skills/coverage-html/SKILL.md` と `.claude/skills/coverage-html/SKILL.md` のどこにも NAME への代入（`NAME=`・`export NAME=`）が無いこと。判定環境の値で参照を展開し（`${NAME:-default}` は NAME が未設定または空なら default）、展開結果が `/` で始まらなければ作業面外としない。`/` で始まれば (α) と同じく正規化したものを X とする。展開に使った値を ST-TR に記録する。
     - X の存在する最長の祖先 path を symlink を解決した実 path（`os.path.realpath`）に置き換え、残りの要素を付け直した path も、上の root の一致・配下の条件に当たらないこと（作業面を指す symlink を経由する指定を作業面外としない）。
     - 相対 path、`./`・`../`・`~` で始まるもの、上記以外の形の環境変数参照、コマンド置換（`$(`・バッククォート）で始まるものは作業面外としない。
     - 指定値の取り出し方：`NAME=値`・`--option=値` の形では最初の `=` より右の部分、`-d 値`・`--option 値` の形では次の空白区切りの語、`.coveragerc` ではキーの値であり、いずれも前後を囲む `"` または `'` を1組除いたものとする。`PYTHONDONTWRITEBYTECODE=1` は bytecode を書かない指定として合格とする。
  4. `python3 -m asset_parity check` が `MISSING` を出さない。
  5. （AC13）3a で、ST-TC-655-13-2 の (1)〜(3) を順に実行し、(1) と (3) の差分に、`.coverage`、`.coverage.*`、`htmlcov/` 配下、現行と異なる tag の `.pyc` が1件も無い。(1) `git ls-files --others` の記録、(2) 手順どおりの3コマンドの実行、(3) `git ls-files --others` の再記録。加えて、(2) の `coverage html` と `coverage report` の終了コードがともに0である（3コマンドが実行されずに差分が0件になる場合を合格にしないため。`coverage run` はテストの失敗で終了コードが0以外になりうるので条件にしない）。判定時点は merge 後で、(1)〜(3) を行う commit は本 PR の `mergeCommit` M とする。
     - 5 は、手順の行が 7 を満たすかどうか、CP に P10 があるかどうか、8 の結果によらず判定する。手順の行が 7 を満たさない場合も、手順の行のまま (1)〜(3) を実行して判定する。
     - (2) を [ST-TC-655](ST-TC-655.md) 冒頭 (4) の (u1)・(u2)（uv が無い、手順の行の `--python` の interpreter が無い）で実行できない場合は STOP して未判定とし、AC13 を合格とも不合格ともしない。
  6. （AC15）手順書の path 表記が作業面外の出力先と整合している。対象は共通本文 `.ai/skills/coverage-html/SKILL.md` と Claude 側 wrapper `.claude/skills/coverage-html/SKILL.md` の2ファイルである（他 PF の写し `.agents/skills`・`.github/skills` は path の記述を持たないため対象外）。
     - (i) 手順2の `coverage html` の HTML 出力先の指定値を、2 の指定方法（複数あれば 2 の優先順位で決まる1つ）と 3 の取り出し方で、1 の合否によらず取り出す。指定が無ければ 6 は不合格とする。取り出した指定値自体が 3 の作業面外の定義を満たさなければ 6 は不合格とする（3 の定義を指定値に直接当てはめ、1 の合否は使わない。例：`-d coverage_report` は相対 path なので、`htmlcov` を含まなくても不合格。`-d $CLAUDE_PROJECT_DIR/htmlcov` は許可しない名前なので不合格）。次の5箇所それぞれで、下記の切り出しによる path 部分のうち、その指定値と一致するもの、または指定値に `/` で続くものが1つ以上ある：`.ai/skills/coverage-html/SKILL.md` の説明文（snapshot の L3）、手順2の出力先の記述（同 L25）、done 条件の HTML 生成の確認項目（同 L34）、`.claude/skills/coverage-html/SKILL.md` の frontmatter `description`（snapshot の L3）、`SendUserFile` で送るファイルの記述（同 L12）。
     - (ii) 2ファイルそれぞれの全体で、下記の path 部分のうち `htmlcov` を含むものがすべて 3 の作業面外の定義を満たす（`htmlcov/index.html`・`./htmlcov/` のような作業面内の path 表記が0件。否定文中の言及も数える）。
     - path 部分の切り出し：(a) バッククォートで囲まれた文字列、(b) コードブロック内、(c) frontmatter の `description` の値、のそれぞれを空白で区切って語にする。(c) の語では最初に、語の末尾から `,`・`.`・`;`・`:`・`)`・バッククォート（`` ` ``）を、語の先頭から `(`・バッククォートを、それぞれ該当する文字が無くなるまで繰り返し除く。次に (a)〜(c) 共通で、`=` を含む語は最初の `=` までの部分（`=` を含む）を除き、前後を囲む `"` または `'` を1組除く。残りを path 部分とする。description 内のバッククォートで囲まれた語のように (a) と (c) の両方に当たる語は、両方の切り出しの path 部分を判定に含める（上の除去により、両者は同じ path 部分になる）。
     - 例：`--directory=/tmp/x/htmlcov` の path 部分は `/tmp/x/htmlcov`。`-d "$TMPDIR/htmlcov"` の2語目の path 部分は `$TMPDIR/htmlcov`。description の `htmlcov/index.html,` の path 部分は `htmlcov/index.html`（作業面内なので不合格）。description の ``writes `${TMPDIR:-/tmp}/cov/htmlcov/index.html`.`` の2語目は、(c) でも (a) でも path 部分が `${TMPDIR:-/tmp}/cov/htmlcov/index.html`（判定環境で展開した X が全 worktree root の外なら合格）。description の `(/tmp/cov/htmlcov/index.html)` と ``(`/tmp/cov/htmlcov/index.html`),`` の path 部分はどちらも `/tmp/cov/htmlcov/index.html`（合格。後者は (a) でも同じ）。
  7. （AC16 の手順の変更範囲）手順の `coverage run` の行（共通本文 `.ai/skills/coverage-html/SKILL.md` の手順1のコードブロック。snapshot の L18）が、8 の比較基準と discover の引数と実行 interpreter を揃える次の (i)(ii) をすべて満たす（揃えることは §1 のオーナー決定による。一次記録は Issue #655 本文 Scope 5 と AC16）。行は空白で区切って語にし、各語の前後を囲む `"` または `'` を1組除いて読む。判定時点は merge 前（PR の最終 head commit H）。
     - (i) 語の列で最初に現れる、語 `uv` の直後の語が `run` である箇所を uv 起動の先頭とする。それより後で最初に現れる、語 `coverage` であって直後の語が `run` であるものを coverage コマンド名とする（`--with coverage` の `coverage` は直後の語が `run` でないので coverage コマンド名にならない）。uv 起動の先頭の `run` の次の語から coverage コマンド名の直前の語までを uv オプション範囲とする。uv 起動の先頭または coverage コマンド名が見つからなければ 7 は不合格。uv オプション範囲に `--python <V>`（値は次の語）または `--python=<V>`（値は `=` の右）が合わせてちょうど1つあり、短形 `-p` が無く、V は空でなく、CP が P9 で記録した値と文字列として一致する。uv オプション範囲のその他の語（`--with coverage` や、CP が加える他の uv オプション）は 7 では制限しない。
     - (i) の判定例（V は CP が P9 で記録した値とする）：
       - `uv run --with coverage --python V coverage run -m unittest discover -s tests -t .`：4語目の `coverage` は直後が `--python` なので coverage コマンド名ではなく、7語目の `coverage`（直後が `run`）が coverage コマンド名。uv オプション範囲は `--with coverage --python V` で `--python` がちょうど1つ、`-p` は無いので (i) を満たす。`-m unittest` より後は `discover -s tests -t .` で (ii) も満たす。
       - `uv run --python V --no-managed-python --with coverage coverage run -m unittest discover -s tests -t .`：7語目の `coverage`（`--with` の値）は直後が `coverage` なので coverage コマンド名ではなく、8語目の `coverage`（直後が `run`）が coverage コマンド名。uv オプション範囲は `--python V --no-managed-python --with coverage` で (i) を満たし、(ii) も満たす。
     - (ii) `-m unittest` より後の語の列が `discover` で始まり、残りが「`-s tests`」と「`-t .`」の2組（順不同）だけ、またはそれに「`-p test*.py`」を加えた3組（順不同）だけからなる。`-s`・`-t`・`-p` の長形 `--start-directory`・`--top-level-directory`・`--pattern` も同じものとみなし、値は次の語または `=` の右とする。`test*.py` は unittest の既定の pattern なので、8 の比較基準と同じ test module の集合を選ぶ。これ以外の値の `-p`（snapshot の `test_*.py` を含む）や、これ以外のオプションがあれば不合格。
     - snapshot の L18（`uv run --with coverage coverage run -m unittest discover -s tests -p "test_*.py"`）は、uv オプション範囲が `--with coverage` で `--python` が無いので (i) を、`-t .` が無く `-p` の値が `test_*.py` なので (ii) を満たさず、7 は不合格になる。したがって snapshot の手順のままでは、8 も (a) により不合格になる（負例）。
  8. （AC16）3a で、ST-TC-655-13-3 の手順により次の (a)〜(d) をすべて満たす。判定時点は merge 後で、実行する commit は本 PR の `mergeCommit` M とする。比べる2つは次のとおりで、比較基準をこの環境変数なしの discover とすることは §1 のオーナー決定（比較基準の案 (i)。一次記録は Issue #655 本文 Scope 5 と AC16）による。
     - 手順側：手順1の `coverage run` を、手順の行どおりに実行したもの。
     - 比較基準：同じ worktree・同じ commit で、環境から `PYTHONPYCACHEPREFIX` と `PYTHONDONTWRITEBYTECODE` を除いた `python3 -m unittest discover -s tests -t .`。
     - (a) M の手順1の `coverage run` の行が 7 を満たす（満たさなければ測定せず 8 は不合格）。
     - (b) P10 (a) の手順で記録した手順側の interpreter と比較基準の interpreter が、P10 (a) の比較方法で同じ interpreter と判定される。
     - (c) P10 (b) の規則で取り出した手順側の失敗 test id の集合が、比較基準の失敗 test id の集合と一致する（手順側にだけある id と比較基準にだけある id がともに0件）。
     - (d) 手順側と比較基準の出力のそれぞれに unittest の `Ran N tests` の行がちょうど1つあり、2つの N が等しい（手順側のテストが実行されずに失敗 test id の集合が空になる場合を合格にしないため）。
     - CP に P10 が無い場合、(b)(c) を判定できないので 8 は不合格とする（§3 の規則）。8 の不合格は AC16 の不合格であり、5（AC13）の判定には使わない。
     - (a) を満たし CP に P10 がある場合に、手順側の起動を [ST-TC-655](ST-TC-655.md) 冒頭 (4) の (u1)・(u2)（uv が無い、手順の行の `--python` の V の interpreter が無い）で実行できないときは STOP して未判定とし、AC16 を合格とも不合格ともしない（13-2 と同じ言葉と範囲）。
     - (a)(b) により、両側の差は bytecode の指定の有無と、`coverage run` の計測下で実行するかどうかの2つだけになる。discover の top-level・start directory・pattern と実行 interpreter は両側で同じである。
     - top-level と interpreter を揃える理由：`-t` を省いた discover は start directory（`tests`）を top-level として `sys.path` の先頭に入れる（unittest の仕様）。このため手順側では、module 名の先頭に `tests.` が付かない差だけでなく、`tests/` 直下に source package と同名の package があるとそれが source package を shadow し、import の ERROR になりうる。この shadow は #318 で実際に起き、`tests/issue_envelope/` を `tests/issue_envelope_tests/` に改名して解消された（snapshot の `issue_envelope/verify/reports/AC-EVIDENCE-371.md`・`TEST-DISCOVERY-318.md`）。本 Issue が追加する `tests/codex_worktree_exec/`・`tests/issue_start/` も、package にする場合（P11 の A）は同じ shadow を起こしうる。この ERROR は bytecode の指定と無関係に手順側だけに出る。7 は手順の文字列で判定するので、判定は shadow が実際に起きるかどうかに依存しない。interpreter も同じ理由で揃える（snapshot の手順の `uv run --with coverage` は interpreter を固定せず、リポジトリに `.python-version`・`pyproject.toml` が無いため、uv が `python3` と異なる interpreter を選びうる）。
     - bytecode の指定（`PYTHONPYCACHEPREFIX=` と `PYTHONDONTWRITEBYTECODE=1` のどちらを使うか）、実行 interpreter の指定（`--python` の値 V）、その指定のもとでテストが干渉して 8 を満たさなくなる場合の対処は P9 として、interpreter の記録・比較と失敗 test id の取り出しの手順は P10 として、本 VD では決めず CP が決める。
- 判定方法：文書検査（1〜4（Scope 5）と 6（AC15）は ST-TC-655-13-1、7（AC16）は merge 前の ST-TC-655-13-4）と 3a の実機確認（5（AC13）は ST-TC-655-13-2、8（AC16）は ST-TC-655-13-3）。

### ST-TD-655-14 lint と単体テスト（Issue AC17）
- 1b依存：P11（2つの suite のコマンドの形）
- 判定時点：merge 後。本 PR の `mergeCommit` M で判定する。比較の基準点は P（[ST-TC-655](ST-TC-655.md) 冒頭 (3)。merge 方式によらず merge 直前の base tip を指し、M の第1親とは限らない）。
- 合格条件：
  1. M で次がすべて終了コード0。
     - `python3 -m maintainability_lint check`
     - `python3 -m issue_envelope check --repo .`
     - `python3 -m unittest tests.unit.test_codex_source_snapshot tests.unit.test_codex_compiled_cache tests.unit.test_codex_artifact_binding tests.unit.test_readonly_workspace tests.unit.test_phase_dispatch_binding tests.unit.test_legacy_pr_rereview tests.unit.test_issue_start_gate`
     - ST-TD-655-16 の 1 で P11 が定める2つの専用 step のコマンド（A なら `python3 -m unittest discover -s tests/<suite> -t .`、B なら `python3 -m unittest discover -s tests/<suite>`）。
     - その他のテストモジュール：P から M までの差分（`git diff --name-status P M`）で、状態が追加（A）・変更（M）・改名（R。改名後の path を使う）の、`tests/` 配下でファイル名が `test*.py` に一致し、M に存在するファイル。削除（D）されたファイルと改名前の path は含めない。前掲のコマンドが実行するもの（`tests/codex_worktree_exec/`・`tests/issue_start/` 配下と、前掲の7 module）は除く。module 名は path から末尾の `.py` を除き `/` を `.` に置き換えたもの（例：`tests/unit/test_x.py` は `tests.unit.test_x`）で、repo root を cwd として `python3 -m unittest <module 名>` で1つずつ実行する。ただし snapshot の `.github/workflows/tests.yml` で start directory を top-level として個別に実行される suite（`tests/time_fixture_lint/`・`tests/jev_hooks/`）の中のファイルは、module 名ではなく CI と同じ `python3 -m unittest discover -s <そのディレクトリ>` で実行する。
  2. `python3 -m unittest discover -s tests -t .` は終了コードを条件にせず、M と P のそれぞれで実行し、M の失敗 test id の集合から P の集合を引いた差（新しい失敗）が0件である。M の出力に `Ran N tests` の行がちょうど1つ無ければ不合格、P の出力に無ければ未判定とする。失敗 test id は、出力の行のうち `FAIL: ` または `ERROR: ` で始まる行（unittest の失敗見出し）から、その接頭辞を除いた残り全体（前後の空白を除く）とする（両側に同じ規則を使う）。snapshot 以後に base branch 側で入った変更による失敗を本 PR に帰属させないため、P は merge 直前の base tip とする。
- P を定められない場合（[ST-TC-655](ST-TC-655.md) 冒頭 (4) の (u3)）、P の出力に `Ran N tests` の行が無い場合（同 (u5)）、または CI が導入する依存物が判定環境に無い場合（同 (u7)）は、1 の「その他のテストモジュール」と 2 を STOP して未判定とし、AC17 を合格とも不合格ともしない。ST-TR に M と P の OID、P の決め方（同 (3) の (m1)・(m2) のどちらか）、実行したテストモジュールの一覧を記録する。
- 判定方法：コマンド実行（ST-TC-655-14-1）。

### ST-TD-655-15 回復コマンド（prune）の安全性（Scope 1 の 3B・契約 (c)）
- 1b依存：P6（コマンド名・引数）
- 合格条件：
  1. 回復コマンドは検査とは別のコマンドで、検査の呼出し経路（4経路）から呼ばれない。
  2. 削除する対象は、指定した作業面の中で、親ディレクトリ名が `__pycache__`、拡張子が `.pyc`、git で未追跡、regular file、path の全要素が symlink でない、のすべてを満たすファイルだけである。次は削除しない（実行前後で bytes と存在が一致）：追跡済みの `.pyc`、`__pycache__` 外の `.pyc`、`__pycache__` 内の `.py` などの他の拡張子、symlink とその参照先、作業面の中に置かれた別の登録済み linked worktree の中身、作業面の外のファイル。
  3. 2回続けて起動すると、2回目は削除0件で終了コード0。
  4. 両 PF の `agent-command-gate.sh` が、gated ロール（`issue-implementer`・`issue-fixer`・`pr-reviewer`・工程6ロール）による回復コマンドの起動を拒否する。
- 判定方法：自動テスト（ST-TC-655-15-1・15-2）。

### ST-TD-655-16 追加 suite を PR の CI で実行する（Issue AC14・Scope 6）
- 1b依存：P11
- 合格条件：
  1. `.github/workflows/tests.yml` の `unittest` job に、`run` が（前後の空白を除いて）P11 の形の `python3 -m unittest discover -s tests/codex_worktree_exec`（A なら末尾に ` -t .`）に一致する step と、`python3 -m unittest discover -s tests/issue_start`（A なら末尾に ` -t .`）に一致する step が、それぞれちょうど1つある。2つのディレクトリの `__init__.py` の有無が P11 と一致する（A なら両方にあり、B なら両方に無い）。
  2. 同 job に全体 step がちょうど1つあり、その `run` が、P11 が B なら snapshot と同じ `python3 -m unittest discover tests`、A なら `python3 -m unittest discover -s tests -t .` である。2つの専用 step、全体 step と `unittest` job に `if:` と `continue-on-error:` が無い。workflow の `on:` に `pull_request` が残っている（snapshot の同ファイル L38-40）。
  3. CI の run の選び方：`tests` workflow の run のうち、event が `pull_request` で head commit が PR の最終 head commit H であるものの中で、作成時刻が最も新しい run を使う（同じ run に再実行があれば attempt 番号が最大のもの）。その run が未完了なら完了を待って判定する。選んだ run の `unittest` job の conclusion が `success` である（cancelled・failure などは不合格。新しい run ができたら、その run で判定し直す）。該当する run が1つも無ければ不合格。
  4. 選んだ run の `unittest` job が実際に実行した commit C（ログの `GITHUB_SHA`。`pull_request` event の run は PR の merge ref を checkout するので、C は H ではない）を、checkout step のログから完全 OID で取り出す（`git log -1 --format=%H` の出力行。無ければ `HEAD is now at <短縮 OID>` の短縮 OID を、C を fetch したローカルで完全 OID に解決したもの）。2つの専用 step のログそれぞれに `Ran N tests` があり、N は1以上で、C を checkout したローカルで同じコマンドを実行したときの N と一致する。結果行は `OK` で、`skipped`・`expected failures` を含まない。
- run・ログ・C を GitHub から取得できない場合（[ST-TC-655](ST-TC-655.md) 冒頭 (4) の (u4)）は STOP して未判定とする。
- 判定時点：merge 前（PR の最終 head commit H）。判定後に H が変わったら、新しい H で 1〜4 を再判定する。merge 後の ST-TR には run の URL、attempt 番号、H、C、各 step の N を記録する。
- 判定方法：差分検査と CI 結果の確認（ST-TC-655-16-1）。
