# ST-TD-655 — 工程入力検査の未追跡分類見直し（システムテスト設計・受入基準）

- 作成：ac-designer（Claude Code (AI)）／phase: verification_design／VD ルート：`verification_design/VD-655.toml`
- Issue：#655／run_id：`run-655-20261018-01`／target_key：`issue-655-vd-r2`
- 入力 snapshot：`5e38863322b4c207f35c8e998647bda89c3c966c`／入力 digest（trusted caller 値）：`4c365745373ab7d3cee6190973d3682446b2fb5431ebae31588ae8f95b4eebd9`
- 参照した調査報告：主文脈作業領域の `tmp/phase-inputs/655/investigation-report.md`（InvestigationReport、sha256 `2aab1bc46597cfa7f77bcd08df9b969c85362ed55d06a46532bed5e1bc64f7cc`）。これは issue-investigator の報告を主文脈が転記した md で、`issue_envelope` の artifact ID を持たない。ac-designer は InvestigationReport の producer ではないため envelope を代わりに作れず、VD の `input_refs`（artifact ID 参照）には載せない。照合は上記 sha256 で行う。
- 対応する TC：[ST-TC-655](ST-TC-655.md)。IT は [codex_worktree_exec IT-TD](IT-TD-655.md)・[issue_start IT-TD](../../../issue_start/verify/designs/IT-TD-655.md)

## 1. 前提（オーナー決定・覆さない既存契約）

- オーナー決定（2026-10-18。一次記録は Issue #655 本文の Scope 1「オーナー決定済み」と推奨節）：別 runtime cache は 3A（無視）を採らない。3B（拒否維持＋診断＋明示 prune）と 3D（発生源の隔離）を併用する。F-655-01〜03 は本 Issue で処置する。
- オーナー決定（2026-10-18。一次記録は本 dispatch の trusted binding `tmp/phase-inputs/655/vd2-binding.json` の `investigation_reason`）：ST/IT-TC のうち自動テストの実コード化は、工程 2a（test_design）で test-writer が `tests/<tool>/` に Red の実テストとして行う。feedback ledger への記録は #537 で扱う。
- 覆さない既存契約：`docs/methods/codex-workspace-binding.md`「read-only工程のprimary → linked準備」の (a) ignore 設定を許可根拠にしない（L278）、(b) 別 runtime・source 不一致の cache は拒否する（L306-307）、(c) 検査は read-only で cache を自動削除・書換えしない（L308）。

## 2. 分類（本 VD の語彙）

名前の規則（R-PYC）：ファイル名が正規表現 `^[A-Za-z_][A-Za-z0-9_]*\.[a-z][a-z0-9]*-[0-9]+(\.opt-[12])?\.pyc$` に完全一致すること。`<stem>` は最初の `.` の前、`<tag>` は2番目の要素（例 `cpython-312`）。現行 tag は実行中の `sys.implementation.cache_tag`。

| 記号 | 対象 | Issue 観測 |
|---|---|---|
| C0 | 未承認の通常 source と緩和対象外の compiled file：tmp 外の未追跡 `.py`・TC・設定、tmp 内の `.py`、`__pycache__` 配下の `.pyo`、R-PYC に一致しない `.pyc`、`__pycache__` 外の `.pyc`、下記 C1〜C8 のどれにも当たらない未追跡ファイル（base で既に許可されている例外＝`tmp/` 配下6拡張子の通常ファイル・既存2 lock・登録済みの別 linked worktree は除く） | 負例（必ず拒否） |
| C1 | 外部製品の runtime lock：`.claude/scheduled_tasks.lock`（repo ルート直下の `.claude/` のみ） | #1 |
| C2 | 孤児 cache：親が `__pycache__` で名前が R-PYC に一致し、対応 source が作業面にも HEAD にも存在しない | #2 |
| C3 | 別 runtime cache：親が `__pycache__` で名前が R-PYC に一致し、`<tag>` が現行 tag と異なり、対応 source は HEAD と一致して作業面に存在する | #3 |
| C4 | 計測ツール副産物：`.coverage`、`.coverage.*`、`htmlcov/**`（いずれも repo ルート直下） | #4 |
| C5 | 外部ツール領域：`.serena/**`（repo ルート直下） | #5 |
| C6 | 現行 runtime の stale cache：親が `__pycache__` で名前が R-PYC に一致し、`<tag>` が現行 tag、source も HEAD と一致するが、code bytes が現行 source の compile 結果と異なる | #6 |
| C7 | harness 自身の生成物：C7a `tmp/_karte/.writer.lock`、C7b `tmp/_adr-notify/<sha256>.root`、C7c `tmp/pr-diffs/pr-<N>-<hex>.diff`、C7d `tmp/_feedback/*.toml`、C7e ADR root 直下の `.write.lock`／`.file-issue.lock`。ADR root は repo 直下の1階層のディレクトリ `<tool>` に対する `<tool>/adr/`（`.ai/agents/creation-stage-contract.md:42` の配置。snapshot で実在するのは `issue_envelope/adr/`・`issue_start/adr/`） | #7 |
| C8 | tmp 内の許可拡張子外の残置（`.sh`・`.out` 等。`.py` は C0） | #8 |

`tmp/` 配下で C7 に当たるファイルは C8 ではなく C7 とする。R-PYC に一致する `__pycache__` 配下の `.pyc` で C2・C3・C6 のどれにも当たらないもの（source が HEAD のみ・未追跡・作業面で改変など）は、IT-TD-655-CWE-03 の CP 対応表が定める拒否分類に入る。

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
  - `source_changes` に path と正しい sha256 を渡しても、上の未追跡ファイルは拒否される。
- 閾値：拒否されないケース0件。
- 判定方法：自動テスト（ST-TC-655-04-1・04-2）。

### ST-TD-655-05 負例：現行 runtime cache の source 一致検証を維持（Issue AC5）
- 1b依存：なし
- 合格条件：
  1. `tests/unit/test_codex_compiled_cache.py` の既存の拒否ケース（source の HEAD 不一致、旧 version の cache、header 不正、未対応 tag）が、同じ入力で引き続き拒否される。拒否メッセージの文字列を変える場合も、拒否であることを確かめる assertion は削らない。
  2. C2 の判定（2A を採る場合）が、次の場合に適用されず拒否のまま残る：source が HEAD にあり作業面だけで削除されている、source が作業面にあり未追跡、source が作業面で改変されている、source の位置にディレクトリがある。
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
  4. CP が、実証の範囲が import 経路であることと、`python3 <cache path>` のような直接 path 実行を検査の脅威範囲外とする判断（または範囲内とする対策）を記録している。
- 判定方法：自動テスト（ST-TC-655-07-1・07-2）と実証ログの文書検査（ST-TC-655-07-3）。

### ST-TD-655-08 不変条件・read-only 性・契約文書（Issue AC8・F-655-02）
- 1b依存：なし（版判断の結論は CP）
- 合格条件：
  1. snapshot `5e38863322b4c207f35c8e998647bda89c3c966c` との差分が、`.codex/config.toml`、`codex_worktree_exec/profile_pin.py`、`codex_worktree_exec/project_trust.py`、`codex_worktree_exec/worktree_binding.py` で0行である（D1 profile pin・read-only profile・project trust・D5）。
  2. C0〜C8 をすべて置いた fixture で検査を呼ぶ前後で、`.git` を除く作業面の全ファイルの（相対 path、種別、size、sha256、mode、`mtime_ns`）の集合と、`git status --porcelain=v1 -z --ignored` の出力が一致する。検査が通る場合と拒否する場合の両方で確かめる。
  3. `docs/methods/codex-workspace-binding.md` の「未追跡通常source…」段落（snapshot 時点の L296〜313）が新しい分類と方式を現在形で記述し、旧記述に訂正を追記する形になっていない。同文書末尾の「本是正は同一PR内の2.0遷移の補完であり…」の文が残っていない。
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

### ST-TD-655-13 coverage 実行で作業面に残さない（Issue AC13・Scope 5）
- 1b依存：なし
- 合格条件：
  1. `.ai/skills/coverage-html/SKILL.md` の手順の3コマンドそれぞれで、次の出力先が作業面外に指定されている。
     - `coverage run`：coverage data file と bytecode の出力先
     - `coverage html`：coverage data file と HTML 出力先
     - `coverage report`：coverage data file
  2. 指定として認めるのは次だけである。(i) そのコマンド行の環境変数代入またはオプション（data file は `COVERAGE_FILE=` または `--data-file`、HTML は `-d`／`--directory`、bytecode は `PYTHONPYCACHEPREFIX=` または `PYTHONDONTWRITEBYTECODE=1`）。(ii) data file と HTML 出力先に限り、追跡済み `.coveragerc` の `[run] data_file` と `[html] directory`。別のコードブロックや手順外の `export`、利用者のシェル設定・環境での指定は認めない。
  3. 作業面外とは、指定値が `/` または環境変数参照（`$HOME`、`${TMPDIR:-/tmp}` 等）で始まり、相対 path・`./`・`../` で始まらないことをいう。`PYTHONDONTWRITEBYTECODE=1` は bytecode を書かない指定として合格とする。
  4. `python3 -m asset_parity check` が `MISSING` を出さない。
  5. 3a で手順どおりに実行した後、`git ls-files --others` の実行前との差分に、`.coverage`、`.coverage.*`、`htmlcov/` 配下、現行と異なる tag の `.pyc` が1件も無い。
- 判定方法：文書検査（ST-TC-655-13-1）と 3a の実機確認（ST-TC-655-13-2）。

### ST-TD-655-14 lint と単体テスト（Issue AC14）
- 1b依存：なし
- 合格条件：最終 commit で次の3つがすべて終了コード0。
  - `python3 -m maintainability_lint check`
  - `python3 -m issue_envelope check --repo .`
  - `python3 -m unittest tests.unit.test_codex_source_snapshot tests.unit.test_codex_compiled_cache tests.unit.test_codex_artifact_binding tests.unit.test_readonly_workspace tests.unit.test_phase_dispatch_binding tests.unit.test_legacy_pr_rereview tests.unit.test_issue_start_gate`、および本 Issue で追加・変更したテストモジュール
- 加えて、`python3 -m unittest discover -s tests -t .` は終了コードを条件にせず、失敗した test id の集合を base `5e38863322b4c207f35c8e998647bda89c3c966c` で同じコマンドを実行したときの集合と比べ、新しい失敗が0件であることで判定する。
- 判定方法：コマンド実行（ST-TC-655-14-1）。

### ST-TD-655-15 回復コマンド（prune）の安全性（Scope 1 の 3B・契約 (c)）
- 1b依存：P6（コマンド名・引数）
- 合格条件：
  1. 回復コマンドは検査とは別のコマンドで、検査の呼出し経路（4経路）から呼ばれない。
  2. 削除する対象は、指定した作業面の中で、親ディレクトリ名が `__pycache__`、拡張子が `.pyc`、git で未追跡、regular file、path の全要素が symlink でない、のすべてを満たすファイルだけである。次は削除しない（実行前後で bytes と存在が一致）：追跡済みの `.pyc`、`__pycache__` 外の `.pyc`、`__pycache__` 内の `.py` などの他の拡張子、symlink とその参照先、作業面の中に置かれた別の登録済み linked worktree の中身、作業面の外のファイル。
  3. 2回続けて起動すると、2回目は削除0件で終了コード0。
  4. 両 PF の `agent-command-gate.sh` が、gated ロール（`issue-implementer`・`issue-fixer`・`pr-reviewer`・工程6ロール）による回復コマンドの起動を拒否する。
- 判定方法：自動テスト（ST-TC-655-15-1・15-2）。
