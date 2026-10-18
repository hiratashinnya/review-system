# ST-TD-655 — 工程入力検査の未追跡分類見直し（システムテスト設計・受入基準）

- 作成：ac-designer（Claude Code (AI)）／phase: verification_design／VD ルート：`verification_design/VD-655.toml`
- Issue：#655／run_id：`run-655-20261018-01`／target_key：`issue-655-vd-r9`
- 入力 snapshot：`2fe2cd57131048d04196867018c1c7d014794a5f`／入力 digest（trusted caller 値）：`be61723b06fdbcd42a6906c40e23212575b404dff669e634254edeed90628fc3`
- 入力の Issue 本文：r8 と同じ版（r7 の入力から、Scope 5 と Acceptance criteria に比較基準 案 (i) のオーナー決定と手順の変更範囲が追記された版。§1）。Acceptance criteria は上から数えて17項目で、本 VD は追記された項目（手順どおりの `coverage run` の失敗 test id 集合の一致）を AC16、lint と単体テストの項目を AC17 と呼ぶ（AC1〜AC15 の番号は r7 と同じ）。
- snapshot：r6〜r8 も同じ `2fe2cd5` を入力にした。r4・r5 は `128a32b947e026523eb048cea074ce981512ba67` を、r3 は `5e38863322b4c207f35c8e998647bda89c3c966c` を入力にした。`128a32b`..`2fe2cd5` の差分は #537 の merge による `feedback_ledger/`・`.ai/feedback/`・`.ai/schema/feedback-ledger-v1.json`・decision-capture skill（`.ai`・`.claude`・`.agents`・`.github` の4ツリー）・`audit/2026-09-21-pipeline-redesign/`・`tests/unit/` の feedback／retired codex launch のテスト5ファイルの74ファイルだけで、`5e38863`..`128a32b` の差分は `blocker_gate/`・その単体テスト・`.ai/rationale/issue-469-transport.md` の11ファイルだけである。どちらも、本 VD が path:行で引く文書・コード・workflow・SKILL.md に変更は無い（行番号は r3〜r8 と同じ）。
- 参照した調査報告：主文脈作業領域の `tmp/phase-inputs/655/investigation-report.md`（InvestigationReport、sha256 `2aab1bc46597cfa7f77bcd08df9b969c85362ed55d06a46532bed5e1bc64f7cc`）。これは issue-investigator の報告を主文脈が転記した md で、`issue_envelope` の artifact ID を持たない。ac-designer は InvestigationReport の producer ではないため envelope を代わりに作れず、VD の `input_refs`（artifact ID 参照）には載せない。照合は上記 sha256 で行う。
- 対応する TC：[ST-TC-655](ST-TC-655.md)。IT は [codex_worktree_exec IT-TD](IT-TD-655.md)・[issue_start IT-TD](../../../issue_start/verify/designs/IT-TD-655.md)

## 1. 前提（オーナー決定・覆さない既存契約）

- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 1「オーナー決定済み」と推奨節）：別 runtime cache は 3A（無視）を採らない。3B（拒否維持＋診断＋明示 prune）と 3D（発生源の隔離）を併用する。F-655-01〜03 は本 Issue で処置する。
- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 1「オーナー決定済み（2026-10-18）」）：ST/IT-TC のうち自動テストの実コード化は、工程 2a（test_design）で test-writer が `tests/<tool>/`（本 Issue では `tests/codex_worktree_exec/`・`tests/issue_start/`）に Red の実テストとして行う。これは、test-writer の成果物を UT-TD/UT-TC と定める契約文言（`.ai/agents/test-writer.md:9`、`.ai/skills/issue-pipeline/SKILL.md:39` の test_design 行）に対する、オーナー承認の例外である。本 VD はこれらの契約文言を ST/IT 実コード化の根拠として引かない。契約文言の是正は別 Issue #663 で扱い、ac-designer の是正を同一 branch で継続する契約の欠落は別 Issue #662 で扱う（いずれも Issue 本文 Scope 1 に記載）。feedback ledger への記録は #537 で扱う。
- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 5「オーナー決定済み（2026-10-18）」と AC16）：coverage-html の手順で全テストを走らせたとき、bytecode の指定だけを理由に検査系テストが失敗しないことを、手順の `coverage run` の失敗 test id の集合が、環境変数なしの `unittest discover`（同じ commit、`-s tests -t .`、同じ interpreter）の集合と一致することで判定する（比較基準の案 (i)）。このため手順の discover に `-t .` を加え、実行 interpreter を `--python` で固定し、`-p` は比較基準と同じ test module の集合になる指定に揃える。bytecode の指定の選択とテスト側の干渉への対処は CP が決める（P9）。ST-TD-655-13 の 7・8、P9 の (b) と P10 はこの決定を根拠とし、版管理されない作業領域のレビュー記録には依らない。
- 覆さない既存契約：`docs/methods/codex-workspace-binding.md`「read-only工程のprimary → linked準備」の (a) ignore 設定を許可根拠にしない（L278）、(b) 別 runtime・source 不一致の cache は拒否する（L306-307）、(c) 検査は read-only で cache を自動削除・書換えしない（L308）。C2（対応 source が作業面にも HEAD にも無い cache）を `<tag>` によらず C2 とすることと (b) の関係は、ST-TD-655-07 の 4 で CP に根拠を記録させ、ST-TD-655-08 の 3 で契約本文の現在形の記述として判定する。

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

次の値は本 VD では決めない。CP が値を確定し、各 AC はその値で判定する。CP に値が無い場合は、その AC を判定不能として不合格にする。

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

## 4. 受入基準（ST-TD）

「1b依存」欄の「なし」は CP の決定によらず判定できる AC、「P*」はそのパラメータで判定基準が確定する AC を表す。

### ST-TD-655-01 方式と理由の記録（Issue AC1・Scope 1）
- 1b依存：P1・P2・P3
- 合格条件（すべて満たす）：
  1. CP または CP が参照する ADR に、C1〜C8（C7 は C7a〜C7e ごと）の12行（C1〜C6・C8 の7行と C7a〜C7e の5行）それぞれについて、方式（§3 の分類ごとに選べる方式）、選定理由（空でない）、不採用案ごとの却下理由（空でない）が記録されている。M5 の行には残置の方式もある。
  2. CP が、3A 不採用の根拠としてオーナー決定の一次記録（Issue #655 本文、または feedback ledger の該当エントリ）を参照している。オーナーの逐語を CP・ADR へ複製することは求めない。1B（`--exclude-standard` 等で ignore を一律除外）は契約 (a) 違反として却下されている。
  3. M3 の行には回復コマンド（P6）が、M4 の行には案内文が記録されている。
- 判定方法：文書検査（ST-TC-655-01-1）。

### ST-TD-655-02 分類ごとの回帰テスト（Issue AC2）
- 1b依存：P1
- 合格条件：一時 git リポジトリの fixture で C1〜C8 を1分類ずつ置き、各ファイルが P1 で定めた方式どおりの結果になる。
  - M1・M2 のファイル：`verify_untracked_sources` と `verify_source_snapshot` が例外を送出しない。
  - M3 のファイル：診断に、その分類の識別子、置いた件数と一致する件数、代表例1件以上、回復コマンドが含まれる。続けて回復コマンドを1回だけ起動すると、検査が例外を送出しない。
  - M4 のファイル：診断に、その分類の識別子、置いた件数と一致する件数、代表例1件以上、空でない案内文が含まれる。
  - M5 の分類：fixture に置いたファイルは残置として扱い、CP が定めた残置の方式（M1・M3・M4）で上の各項目どおりに判定する。生成元の出力先は本 AC ではなく、C3・C4 は ST-TD-655-13、C7 は ST-TD-655-10 で判定する。
- 判定方法：自動テスト（ST-TC-655-02-1〜02-8）。

### ST-TD-655-03 違反の分類別集約（Issue AC3）
- 1b依存：なし（出力形式は P4）
- 合格条件：方式が拒否に固定された分類 C0・C3・C6 を各2件置いた fixture で、検査を1回だけ呼ぶ。
  1. 例外は1回だけ送出される。
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
  - `source_changes` に path と正しい sha256 を渡しても、上の未追跡ファイルは拒否される。
- 閾値：拒否されないケース0件。
- 判定方法：自動テスト（ST-TC-655-04-1・04-2）。

### ST-TD-655-05 負例：現行 runtime cache の source 一致検証を維持（Issue AC5）
- 1b依存：なし
- 合格条件：
  1. `tests/unit/test_codex_compiled_cache.py` の既存の拒否ケース（source の HEAD 不一致、旧 version の cache、header 不正、未対応 tag）が、同じ入力で引き続き拒否される。拒否メッセージの文字列を変える場合も、拒否であることを確かめる assertion は削らない。
  2. C2 の判定（2A を採る場合）が、次の場合に適用されず拒否のまま残る：source が HEAD にあり作業面だけで削除されている、source が作業面にあり未追跡、source が作業面で改変されている、HEAD に無い source の位置に空のディレクトリがある（`lexists` が真）。
  3. 現行 tag の cache で、source が HEAD と一致するが code bytes が異なるもの（C6）は、回復コマンドの実行前は拒否される。
- 閾値：既存拒否ケースの通過0件。
- 判定方法：自動テスト（ST-TC-655-05-1・05-2）。

### ST-TD-655-06 許可・無視の範囲（Issue AC6・Out of scope）
- 1b依存：P1・P3（M1 を使わない場合、本 AC は2と4を判定する）
- 合格条件：
  1. 追加した M1 の許可エントリはすべて、repo 相対の exact path 文字列であり、`*`・`?`・`[` を含まず、末尾が `/` でない。照合は完全一致で、prefix 一致・ディレクトリ一致をしない。
  2. 許可の照合は、regular file かつ path の全要素が symlink でない場合だけ成立する。
  3. 許可した各 path について、(a) その path が symlink、(b) その path の親ディレクトリが symlink、(c) 同じ basename を別ディレクトリに置いたもの、のいずれも拒否される。
  4. M2（C2）以外に、ディレクトリ・prefix・ワイルドカード・拡張子の照合で検査を通す分岐が追加されていない。C1・C4・C5・C7・C8 の置き場と同じディレクトリまたは同じ拡張子で、M1 のどのエントリとも完全一致しないファイルは拒否される（base に既存の `tmp/` 配下6拡張子の例外は対象外）。
- 判定方法：差分の文書検査と自動テスト（ST-TC-655-06-1・06-2）。

### ST-TD-655-07 孤児 cache の無視条件と実証（Issue AC7）
- 1b依存：P2（2B を採る場合は、CP に 2A 不採用の理由があり、C2 が ST-TD-655-02 の M3 として判定されることで合格）
- 合格条件（2A を採る場合）：
  1. 次の4条件をすべて満たす cache だけが無視される。条件を1つだけ外した fixture では、すべて拒否される。
     (i) 親ディレクトリ名が厳密に `__pycache__`、(ii) ファイル名が R-PYC に一致する、(iii) 対応 source が作業面に無く（`lexists` が偽）かつ HEAD にも無い、(iv) regular file で path の全要素が symlink でない。
  2. 実証記録が `codex_worktree_exec/verify/logs/` に commit されている。記録は現行 runtime（`python3`）で、timestamp・checked-hash・unchecked-hash の3種の cache それぞれについて、source を削除した後の `import` が `ModuleNotFoundError` になり、cache に埋めた副作用（marker ファイル作成）が実行されないことを示す。実行コマンド、Python の version と `sys.implementation.cache_tag`、終了コード、出力を含む。
  3. 無視した cache の source が後から HEAD に現れた fixture（別内容で commit）では、次の検査がその cache を通常の検証で拒否する。
  4. CP が次の3点を記録している。
     - 実証の範囲が import 経路であることと、`python3 <cache path>` のような直接 path 実行を検査の脅威範囲外とする判断（または範囲内とする対策）。
     - 現行と異なる `<tag>` の孤児 cache も C2 に含める根拠（2 の実証は現行 runtime だけで行うため、他 version の CPython も対応 source の無い `__pycache__` 配下の cache を import しないことの根拠と、その出典）と、それが 3A 不採用の理由（対応 source が存在する別 runtime cache を、その version の runtime が import しうること）に当たらないこと。
     - C2 を `<tag>` によらず定めることが契約 (b)（`docs/methods/codex-workspace-binding.md:306-307` の、別 source・別 runtime・未対応 compiler 形式の cache を拒否する定め）を覆さない根拠、または (b) の適用範囲の読み（例：(b) の別 runtime を理由とする拒否は対応 source が作業面にある cache に対するもので、対応 source が作業面にも HEAD にも無い cache には及ばない）と、その読みの根拠。
- 判定方法：自動テスト（ST-TC-655-07-1・07-2）と、実証ログと CP の文書検査（ST-TC-655-07-3）。

### ST-TD-655-08 不変条件・read-only 性・契約文書（Issue AC8・F-655-02）
- 1b依存：なし（版判断の結論は CP）
- 合格条件：
  1. 本 PR が加えた差分が、`.codex/config.toml`、`codex_worktree_exec/profile_pin.py`、`codex_worktree_exec/project_trust.py`、`codex_worktree_exec/worktree_binding.py` で0行である（D1 profile pin・read-only profile・project trust・D5）。本 PR が加えた差分とは、PR の base branch（`main`）の判定時点の tip と PR の最終 head commit の merge-base から、最終 head commit までの差分（`git diff <base tip>...<最終 head commit>` の三点記法）をいう。snapshot 以後に base branch 側でこれらのファイルが変わっていても、本 PR が加えた変更でなければ判定に含めない。判定時点は merge 前（PR の最終 head commit）。
  2. C0〜C8 をすべて置いた fixture で検査を呼ぶ前後で、`.git` を除く作業面の全ファイルの（相対 path、種別、size、sha256、mode、`mtime_ns`）の集合と、`git status --porcelain=v1 -z --ignored` の出力が一致する。検査が通る場合と拒否する場合の両方で確かめる。
  3. `docs/methods/codex-workspace-binding.md` の「未追跡通常source…」段落（snapshot 時点の L296〜313）が新しい分類と方式を現在形で記述し、旧記述に訂正を追記する形になっていない。同文書末尾の「本是正は同一PR内の2.0遷移の補完であり…」の文が残っていない。加えて、書き換えた段落が次の2点を現在形で述べている：(i) 孤児 cache（対応 source が作業面にも HEAD にも無い `__pycache__` 配下の cache）は `<tag>` によらず C2 として扱うこと（方式は P2）、(ii) 別 runtime（現行と異なる tag）を理由とする拒否は、対応 source のある cache に限ること。
  4. 版付き文書の bump 要否の判断が `.ai/guidance/common.md`「正本・実装規約」に従って CP に記録されている。版の判定対象は現行版の定義箇所に限る：`issue_start/gate_support.py` の `ISSUE_START_POLICY_VERSION` と、CP が path:行で列挙した、現行版を述べる契約本文の箇所。版の遷移を述べる履歴記述（例：`docs/tools/issue-start-and-branch-source.md:39` の `issue-start/1.0` から `issue-start/2.0` への記述）は判定から除外する。
     - bump する場合：`ISSUE_START_POLICY_VERSION` が `issue-start/2.0` と異なる新しい値であり、判定対象のすべての箇所がその値と同じ。
     - 据え置く場合：`ISSUE_START_POLICY_VERSION` が `issue-start/2.0` のままであり、据え置きの理由が CP の列挙した契約本文のどれかに書かれている。
- 判定方法：差分検査・自動テスト・文書検査（ST-TC-655-08-1〜08-3）。

### ST-TD-655-09 削除 pull と別 runtime 実行の再現（Issue AC9）
- 1b依存：P1・P2・P6
- 合格条件：
  1. 削除 pull：source を2件 commit し、現行 runtime で import して cache を作る。別 clone で1件の削除を commit し、元の作業面で `git pull --ff-only` する。その後、検査が通る。または回復コマンドを1回起動した後に検査が通る。オーナー許可の手作業削除を手順に含まない。
  2. 別 runtime（模擬）：HEAD と一致する source の `__pycache__` に、現行と異なる tag の cache を3件置く。回復前は C3 として拒否され、診断に件数と回復コマンドが出る。回復コマンドを1回起動した後は検査が通る。
  3. 別 runtime（実機）：3a で、`uv run` で起動した現行と異なる version の Python が作業面の module を import した後に、2 と同じ結果になる。
- 判定方法：自動テスト（ST-TC-655-09-1・09-2）と 3a の実機確認（ST-TC-655-09-3）。

### ST-TD-655-10 harness 生成物で止まらない（Issue AC10・観測 #7・F-655-01）
- 1b依存：P3（判定する結果は P3 によらない）
- 合格条件：一時 repo で次の生成元の実コード経路を実行した後、検査が通る（C7 は M1・M5 のどちらかなので回復コマンドを要しない）。
  - `karte append`（`tmp/_karte/.writer.lock`）、`adr new-entry`（`tmp/_adr-notify/*.root` と ADR root の `.write.lock`）、ADR の `file-issue` 経路（`.file-issue.lock`）、`gitgate show-pr-diff` の差分ファイル保存経路（4096 byte を超える差分）、feedback 下書き保存（`tmp/_feedback/*.toml`）
  - P3 で M5 とした生成元：生成物の実 path が作業面の外にある。
  - P3 で M1 とした生成物：ST-TD-655-06 を満たす。
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
- 判定方法：自動テスト（ST-TC-655-12-1〜12-3）。

### ST-TD-655-13 coverage 実行で作業面に残さない・手順書の整合（Issue AC13・AC15・AC16・Scope 5。AC15 は Claude 側 wrapper を含む。AC16 は §1 の比較基準 案 (i) のオーナー決定。AC13 は 5、AC16 は 7・8 で、互いに独立に判定する）
- 1b依存：P9（bytecode の指定と実行 interpreter の指定の選択と、テスト側の干渉への対処）・P10（8 の測定手順）。5 と 7 の判定条件は P9・P10 の選択によらない
- 合格条件：
  1. `.ai/skills/coverage-html/SKILL.md` の手順の3コマンドそれぞれで、次の出力先が作業面外に指定されている。
     - `coverage run`：coverage data file と bytecode の出力先
     - `coverage html`：coverage data file と HTML 出力先
     - `coverage report`：coverage data file
  2. 指定として認めるのは次だけである。(i) そのコマンド行の環境変数代入またはオプション（data file は `COVERAGE_FILE=` または `--data-file`、HTML は `-d`／`--directory`、bytecode は `PYTHONPYCACHEPREFIX=` または `PYTHONDONTWRITEBYTECODE=1`）。(ii) data file と HTML 出力先に限り、追跡済み `.coveragerc` の `[run] data_file` と `[html] directory`。別のコードブロックや手順外の `export`、利用者のシェル設定・環境での指定は認めない。bytecode の指定は P9 で CP が選んだ方とする。
  3. 作業面外とは、指定値が `/` または環境変数参照（`$HOME`、`${TMPDIR:-/tmp}` 等）で始まり、相対 path・`./`・`../` で始まらないことをいう。指定値は、`NAME=値`・`--option=値` の形では最初の `=` より右の部分、`-d 値`・`--option 値` の形では次の空白区切りの語、`.coveragerc` ではキーの値であり、いずれも前後を囲む `"` または `'` を1組除いたものとする。`PYTHONDONTWRITEBYTECODE=1` は bytecode を書かない指定として合格とする。
  4. `python3 -m asset_parity check` が `MISSING` を出さない。
  5. （AC13）3a で、ST-TC-655-13-2 の (1)〜(3) を順に実行し、(1) と (3) の差分に、`.coverage`、`.coverage.*`、`htmlcov/` 配下、現行と異なる tag の `.pyc` が1件も無い。(1) `git ls-files --others` の記録、(2) 手順どおりの3コマンドの実行、(3) `git ls-files --others` の再記録。判定時点は merge 後で、(1)〜(3) を行う commit は本 PR の `mergeCommit` の OID とする。
     - 5 は、手順の行が 7 を満たすかどうか、CP に P10 があるかどうか、8 の結果によらず判定する。手順の行が 7 を満たさない場合も、手順の行のまま (1)〜(3) を実行して判定する。
  6. 手順書の path 表記が作業面外の出力先と整合している。対象は共通本文 `.ai/skills/coverage-html/SKILL.md` と Claude 側 wrapper `.claude/skills/coverage-html/SKILL.md` の2ファイルである（他 PF の写し `.agents/skills`・`.github/skills` は path の記述を持たないため対象外）。
     - (i) 次の5箇所それぞれが、1 で `coverage html` の HTML 出力先として指定した値（`.coveragerc` で指定した場合はその値。3 の指定値）を文字列として含む path を示す：`.ai/skills/coverage-html/SKILL.md` の説明文（snapshot の L3）、手順2の出力先の記述（同 L25）、done 条件の HTML 生成の確認項目（同 L34）、`.claude/skills/coverage-html/SKILL.md` の frontmatter `description`（snapshot の L3）、`SendUserFile` で送るファイルの記述（同 L12）。
     - (ii) 2ファイルそれぞれの全体で、下記の path 部分のうち `htmlcov` を含むものがすべて 3 の作業面外の条件を満たす（`htmlcov/index.html`・`./htmlcov/` のような作業面内の path 表記が0件。否定文中の言及も数える）。
     - path 部分の切り出し：(a) バッククォートで囲まれた文字列、(b) コードブロック内、(c) frontmatter の `description` の値、のそれぞれを空白で区切って語にする。(c) の語では最初に、語の末尾から `,`・`.`・`;`・`:`・`)`・バッククォート（`` ` ``）を、語の先頭から `(`・バッククォートを、それぞれ該当する文字が無くなるまで繰り返し除く。次に (a)〜(c) 共通で、`=` を含む語は最初の `=` までの部分（`=` を含む）を除き、前後を囲む `"` または `'` を1組除く。残りを path 部分とする。description 内のバッククォートで囲まれた語のように (a) と (c) の両方に当たる語は、両方の切り出しの path 部分を判定に含める（上の除去により、両者は同じ path 部分になる）。
     - 例：`--directory=/tmp/x/htmlcov` の path 部分は `/tmp/x/htmlcov`。`-d "$TMPDIR/htmlcov"` の2語目の path 部分は `$TMPDIR/htmlcov`。description の `htmlcov/index.html,` の path 部分は `htmlcov/index.html`（作業面内なので不合格）。description の ``writes `${TMPDIR:-/tmp}/cov/htmlcov/index.html`.`` の2語目は、(c) でも (a) でも path 部分が `${TMPDIR:-/tmp}/cov/htmlcov/index.html`（合格）。description の `(/tmp/cov/htmlcov/index.html)` と ``(`/tmp/cov/htmlcov/index.html`),`` の path 部分はどちらも `/tmp/cov/htmlcov/index.html`（合格。後者は (a) でも同じ）。
  7. （AC16 の手順の変更範囲）手順の `coverage run` の行（共通本文 `.ai/skills/coverage-html/SKILL.md` の手順1のコードブロック。snapshot の L18）が、8 の比較基準と discover の引数と実行 interpreter を揃える次の (i)(ii) をすべて満たす（揃えることは §1 のオーナー決定による。一次記録は Issue #655 本文 Scope 5 と AC16）。行は空白で区切って語にし、各語の前後を囲む `"` または `'` を1組除いて読む。判定時点は merge 前（PR の最終 head commit）。
     - (i) 語の列で最初に現れる、語 `uv` の直後の語が `run` である箇所を uv 起動の先頭とする。それより後で最初に現れる、語 `coverage` であって直後の語が `run` であるものを coverage コマンド名とする（`--with coverage` の `coverage` は直後の語が `run` でないので coverage コマンド名にならない）。uv 起動の先頭の `run` の次の語から coverage コマンド名の直前の語までを uv オプション範囲とする。uv 起動の先頭または coverage コマンド名が見つからなければ 7 は不合格。uv オプション範囲に `--python <V>`（値は次の語）または `--python=<V>`（値は `=` の右）が合わせてちょうど1つあり、短形 `-p` が無く、V は空でなく、CP が P9 で記録した値と文字列として一致する。uv オプション範囲のその他の語（`--with coverage` や、CP が加える他の uv オプション）は 7 では制限しない。
     - (i) の判定例（V は CP が P9 で記録した値とする）：
       - `uv run --with coverage --python V coverage run -m unittest discover -s tests -t .`：4語目の `coverage` は直後が `--python` なので coverage コマンド名ではなく、7語目の `coverage`（直後が `run`）が coverage コマンド名。uv オプション範囲は `--with coverage --python V` で `--python` がちょうど1つ、`-p` は無いので (i) を満たす。`-m unittest` より後は `discover -s tests -t .` で (ii) も満たす。
       - `uv run --python V --no-managed-python --with coverage coverage run -m unittest discover -s tests -t .`：7語目の `coverage`（`--with` の値）は直後が `coverage` なので coverage コマンド名ではなく、8語目の `coverage`（直後が `run`）が coverage コマンド名。uv オプション範囲は `--python V --no-managed-python --with coverage` で (i) を満たし、(ii) も満たす。
     - (ii) `-m unittest` より後の語の列が `discover` で始まり、残りが「`-s tests`」と「`-t .`」の2組（順不同）だけ、またはそれに「`-p test*.py`」を加えた3組（順不同）だけからなる。`-s`・`-t`・`-p` の長形 `--start-directory`・`--top-level-directory`・`--pattern` も同じものとみなし、値は次の語または `=` の右とする。`test*.py` は unittest の既定の pattern なので、8 の比較基準と同じ test module の集合を選ぶ。これ以外の値の `-p`（snapshot の `test_*.py` を含む）や、これ以外のオプションがあれば不合格。
     - snapshot の L18（`uv run --with coverage coverage run -m unittest discover -s tests -p "test_*.py"`）は、uv オプション範囲が `--with coverage` で `--python` が無いので (i) を、`-t .` が無く `-p` の値が `test_*.py` なので (ii) を満たさず、7 は不合格になる。したがって snapshot の手順のままでは、8 も (a) により不合格になる（負例）。
  8. （AC16）3a で、ST-TC-655-13-3 の手順により次の (a)〜(c) をすべて満たす。判定時点は merge 後で、実行する commit は本 PR の `mergeCommit` の OID とする。比べる2つは次のとおりで、比較基準をこの環境変数なしの discover とすることは §1 のオーナー決定（比較基準の案 (i)。一次記録は Issue #655 本文 Scope 5 と AC16）による。
     - 手順側：手順1の `coverage run` を、手順の行どおりに実行したもの。
     - 比較基準：同じ worktree・同じ commit で、環境から `PYTHONPYCACHEPREFIX` と `PYTHONDONTWRITEBYTECODE` を除いた `python3 -m unittest discover -s tests -t .`。
     - (a) `mergeCommit` の手順1の `coverage run` の行が 7 を満たす（満たさなければ測定せず 8 は不合格）。
     - (b) P10 (a) の手順で記録した手順側の interpreter と比較基準の interpreter が、P10 (a) の比較方法で同じ interpreter と判定される。
     - (c) P10 (b) の規則で取り出した手順側の失敗 test id の集合が、比較基準の失敗 test id の集合と一致する（手順側にだけある id と比較基準にだけある id がともに0件）。
     - CP に P10 が無い場合、(b)(c) を判定できないので 8 は不合格とする（§3 の規則）。8 の不合格は AC16 の不合格であり、5（AC13）の判定には使わない。
     - (a)(b) により、両側の差は bytecode の指定の有無と、`coverage run` の計測下で実行するかどうかの2つだけになる。discover の top-level・start directory・pattern と実行 interpreter は両側で同じである。
     - top-level と interpreter を揃える理由：`-t` を省いた discover は start directory（`tests`）を top-level として `sys.path` の先頭に入れる（unittest の仕様）。このため手順側では、module 名の先頭に `tests.` が付かない差だけでなく、`tests/issue_envelope/` のように tool package と同名の `tests/` 配下の package が tool package を shadow し、例えば `tests/unit/test_codex_compiled_cache.py:8` の `from issue_envelope.path_binding import committed_bytes` が import の ERROR になりうる（本 Issue が追加する `tests/codex_worktree_exec/`・`tests/issue_start/` も同様）。この ERROR は bytecode の指定と無関係に手順側だけに出る。shadow は unittest の仕様とファイル配置からの推論で実測していないが、7 は手順の文字列で判定するので、判定は shadow が実際に起きるかどうかに依存しない。interpreter も同じ理由で揃える（snapshot の手順の `uv run --with coverage` は interpreter を固定せず、リポジトリに `.python-version`・`pyproject.toml` が無いため、uv が `python3` と異なる interpreter を選びうる）。
     - bytecode の指定（`PYTHONPYCACHEPREFIX=` と `PYTHONDONTWRITEBYTECODE=1` のどちらを使うか）、実行 interpreter の指定（`--python` の値 V）、その指定のもとでテストが干渉して 8 を満たさなくなる場合の対処は P9 として、interpreter の記録・比較と失敗 test id の取り出しの手順は P10 として、本 VD では決めず CP が決める。
- 判定方法：文書検査（ST-TC-655-13-1。7 を含む）と 3a の実機確認（AC13 は ST-TC-655-13-2、AC16 は ST-TC-655-13-3）。

### ST-TD-655-14 lint と単体テスト（Issue AC17）
- 1b依存：なし
- 合格条件：最終 commit で次の3つがすべて終了コード0。
  - `python3 -m maintainability_lint check`
  - `python3 -m issue_envelope check --repo .`
  - `python3 -m unittest tests.unit.test_codex_source_snapshot tests.unit.test_codex_compiled_cache tests.unit.test_codex_artifact_binding tests.unit.test_readonly_workspace tests.unit.test_phase_dispatch_binding tests.unit.test_legacy_pr_rereview tests.unit.test_issue_start_gate`、`python3 -m unittest discover -s tests/codex_worktree_exec -t .`、`python3 -m unittest discover -s tests/issue_start -t .`、および本 Issue で追加・変更したその他のテストモジュール
- 加えて、`python3 -m unittest discover -s tests -t .` は終了コードを条件にせず、失敗した test id の集合を base `2fe2cd57131048d04196867018c1c7d014794a5f` で同じコマンドを実行したときの集合と比べ、新しい失敗が0件であることで判定する。
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
- 1b依存：なし
- 合格条件：
  1. `.github/workflows/tests.yml` の `unittest` job に、`run` が（前後の空白を除いて）`python3 -m unittest discover -s tests/codex_worktree_exec -t .` に一致する step と、`python3 -m unittest discover -s tests/issue_start -t .` に一致する step が、それぞれちょうど1つある（先例：snapshot `2fe2cd5` の `.github/workflows/tests.yml:64-65` の `tests/issue_envelope`）。
  2. その2つの step と `unittest` job に `if:` と `continue-on-error:` が無い。workflow の `on:` に `pull_request` が残っている（snapshot の同ファイル L38-40）。
  3. PR の最終 head commit に対する `tests` workflow の run で、`unittest` job の conclusion が `success` である。2つの step のログそれぞれに `Ran N tests` があり、N は1以上で、同じ commit で同じコマンドをローカルで実行したときの N と一致する。結果行は `OK` で、`skipped`・`expected failures` を含まない。
- 判定時点：merge 前（PR の最終 head commit）。merge 後の ST-TR には run の URL、head commit、各 step の N を記録する。
- 判定方法：差分検査と CI 結果の確認（ST-TC-655-16-1）。
