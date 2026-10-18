# ST-TD-655 — 工程入力検査の未追跡分類見直し（システムテスト設計・受入基準）

- 作成：ac-designer（Claude Code (AI)）／phase: verification_design／VD ルート：`verification_design/VD-655.toml`
- Issue：#655／run_id：`run-655-20261018-01`／target_key：`issue-655-vd`
- 入力 snapshot：`ec711e74ffe4f71f3936f4b5726e57412d88384d`／入力 digest（trusted caller 値）：`4c365745373ab7d3cee6190973d3682446b2fb5431ebae31588ae8f95b4eebd9`
- 参照した調査報告：主文脈作業領域の InvestigationReport（sha256 `2aab1bc4…f7cc`。commit 済み artifact ではないため VD の `input_refs` には載せない）
- 対応する TC：[ST-TC-655](ST-TC-655.md)。IT は [codex_worktree_exec IT-TD](IT-TD-655.md)・[issue_start IT-TD](../../../issue_start/verify/designs/IT-TD-655.md)

## 1. 前提（オーナー決定・覆さない既存契約）

- オーナー決定（2026-10-18、Issue 本文に記録）：別 runtime cache は 3A（無視）を採らない。3B（拒否維持＋診断＋明示 prune）と 3D（発生源の隔離）を併用する。F-655-01〜03 は本 Issue で処置する（fix-here）。
- 覆さない既存契約：`docs/methods/codex-workspace-binding.md`「read-only工程のprimary → linked準備」の (a) ignore 設定を許可根拠にしない、(b) 別 runtime・source 不一致の cache は拒否する、(c) 検査は read-only で cache を自動削除・書換えしない。

## 2. 分類（本 VD の語彙）

| 記号 | 対象 | Issue 観測 |
|---|---|---|
| C0 | 未承認の通常 source：tmp 外の未追跡 `.py`・TC・設定、tmp 内の `.py` | 負例（必ず拒否） |
| C1 | 外部製品の runtime lock：`.claude/scheduled_tasks.lock` | #1 |
| C2 | 孤児 cache：`__pycache__/<stem>.<tag>[.opt-N].pyc` で、対応 source が作業面にも HEAD にも存在しない | #2 |
| C3 | 別 runtime cache：対応 source は HEAD と一致して存在するが、tag が現行 runtime と異なる | #3 |
| C4 | 計測ツール副産物：`.coverage`、`.coverage.*`、`htmlcov/**` | #4 |
| C5 | 外部ツール領域：`.serena/**` | #5 |
| C6 | 現行 runtime の stale cache：tag は現行で source も HEAD と一致するが、code bytes が現行 source の compile 結果と異なる | #6 |
| C7 | harness 自身の生成物：C7a `tmp/_karte/.writer.lock`、C7b `tmp/_adr-notify/<sha256>.root`、C7c `tmp/pr-diffs/pr-<N>-<hex>.diff`、C7d `tmp/_feedback/*.toml`、C7e ADR root の `.write.lock`／`.file-issue.lock` | #7 |
| C8 | tmp 内の許可拡張子外の残置（`.sh`・`.out` 等。`.py` は C0） | #8 |

## 3. 1b（ChangePlan）で確定するパラメータ

次の値は本 VD では決めない。CP が値を確定し、各 AC はその値で判定する。CP に値が無い場合は、その AC を判定不能として不合格にする。

| 記号 | 内容 | 制約（本 VD が固定する範囲） |
|---|---|---|
| P1 | C1〜C8 の各分類（C7 は C7a〜C7e ごと）の方式 | 方式は「許可（exact path）」「自動検出して無視」「拒否＋単一の回復手順」「発生源の隔離」のいずれか、または組合せ。C0 は常に拒否。C3 と C6 は拒否（オーナー決定・Out of scope） |
| P2 | C2 の方式（2A 自動検出して無視／2B 回復手順） | 2A を採る場合は ST-TD-655-07 を満たすこと |
| P3 | C7 の扱い（生成元で作業面外へ移す／exact path 許可に追加） | 許可に追加する場合は ST-TD-655-06 を満たすこと |
| P4 | 集約診断の出力形式（stderr 1行を維持するか、契約を改めるか） | どちらでも ST-TD-655-03・12 の必須要素を含むこと |
| P5 | 分類ごとの代表例の最大件数 N | N は1以上の整数定数 |
| P6 | 回復手順のコマンド（prune 等）の名前・引数 | 1回の起動で完了すること。対象は ST-TD-655-15 の範囲に限る |
| P7 | 診断の分類識別子の語彙 | 分類ごとに一意で、正規表現 `^[A-Za-z0-9_.:-]+$` に一致する固定文字列 |
| P8 | `readonly_workspace` 準備経路の失敗識別子 | 正規表現 `^ISSUE_START_[A-Z0-9_]+$` に一致する固定文字列 |

## 4. 受入基準（ST-TD）

「1b依存」欄の「なし」は CP の決定によらず判定できる AC、「P*」はそのパラメータで判定基準が確定する AC を表す。

### ST-TD-655-01 方式と理由の記録（Issue AC1・Scope 1）
- 1b依存：P1・P2・P3
- 合格条件（すべて満たす）：
  1. CP または CP が参照する ADR に、C1〜C8（C7 は C7a〜C7e ごと）の13行それぞれについて、方式（P1 の語彙）、選定理由（空でない）、不採用案ごとの却下理由（空でない）が記録されている。
  2. 3A の不採用がオーナー決定（2026-10-18）として記録され、1B（`--exclude-standard` 等で ignore を一律除外）が契約 (a) 違反として却下されている。
  3. 方式に「拒否＋単一の回復手順」を含む分類では、回復コマンド（P6）が記録されている。
- 判定方法：文書検査（ST-TC-655-01-1）。

### ST-TD-655-02 分類ごとの回帰テスト（Issue AC2）
- 1b依存：P1
- 合格条件：一時 git リポジトリの fixture で C1〜C8 を1分類ずつ置き、各分類で P1 の方式どおりの結果になる。
  - 許可・無視・隔離の分類：`verify_untracked_sources` と `verify_source_snapshot` が例外を送出しない。
  - 拒否＋回復手順の分類：診断に、その分類の識別子、置いた件数と一致する件数、代表例1件以上、回復手順が含まれる。続けて回復コマンドを1回だけ起動すると、検査が例外を送出しない。
- 判定方法：自動テスト（ST-TC-655-02-1〜02-8）。

### ST-TD-655-03 違反の分類別集約（Issue AC3）
- 1b依存：なし（出力形式は P4）
- 合格条件：拒否される分類を3種類以上（C0 を含む）、各分類に2件以上置いた fixture で、検査を1回だけ呼ぶ。
  1. 例外は1回だけ送出される。
  2. 診断に、置いた全分類の識別子があり、分類ごとの件数が置いた件数と完全に一致する。
  3. ファイル名を変えて `git ls-files` の列挙順を入れ替えても（例：C0 の違反が最初になる名前と最後になる名前）、2 の結果は変わらない。
- 閾値：分類の欠落0件、件数誤差0件。
- 判定方法：自動テスト（ST-TC-655-03-1・03-2）。

### ST-TD-655-04 負例：未承認 source の拒否維持（Issue AC4）
- 1b依存：なし
- 合格条件：次の各ファイルを1件ずつ未追跡で置いたとき、`.gitignore`・`.git/info/exclude`・`core.excludesFile` のどれにも載せない場合、どれか1つに載せた場合、3つ全部に載せた場合のすべてで、検査が拒否し、そのファイルが診断の件数に数えられる。`.py`・`.toml`・lock の各ファイルは C0 として数えられる。`.pyc` の2件は C0 または CP の対応表（IT-TD-655-CWE-03）が定める拒否分類として数えられる。
  - `source.py`（ルート）、`pkg/module.py`、`tests/unit/test_extra.py`、`tool/config.toml`、`tmp/injected.py`
  - 許可・無視の名前に似せたもの：`sub/.claude/scheduled_tasks.lock`（別ディレクトリの同名）、`__pycache__` 配下の `.py`、`__pycache__/module.pyc`（tag の無い名前）、`__pycache__` 外の `module.pyc`
  - `source_changes` に path と正しい sha256 を渡しても、上の未追跡ファイルは拒否される。
- 閾値：拒否されないケース0件。
- 判定方法：自動テスト（ST-TC-655-04-1・04-2）。

### ST-TD-655-05 負例：現行 runtime cache の source 一致検証を維持（Issue AC5）
- 1b依存：なし
- 合格条件：
  1. `tests/unit/test_codex_compiled_cache.py` の既存の拒否ケース（source の HEAD 不一致、旧 version の cache、header 不正、未対応 tag）が、同じ入力で引き続き拒否される。拒否メッセージの文字列を変える場合も、拒否であることを確かめる assertion は削らない。
  2. C2 の判定（2A を採る場合）が、次の場合に適用されず拒否のまま残る：source が HEAD にあり作業面だけで削除されている、source が作業面にあり未追跡、source が作業面で改変されている、source の位置にディレクトリがある。
  3. 現行 tag の cache で、source が HEAD と一致するが code bytes が異なるもの（C6）は、回復手順の実行前は拒否される。
- 閾値：既存拒否ケースの通過0件。
- 判定方法：自動テスト（ST-TC-655-05-1・05-2）。

### ST-TD-655-06 許可リスト追加の形（Issue AC6）
- 1b依存：P1・P3（許可を追加しない場合、本 AC は2のみを判定する）
- 合格条件：
  1. 追加した許可エントリはすべて、repo 相対の exact path 文字列であり、`*`・`?`・`[` を含まず、末尾が `/` でない。照合は完全一致で、prefix 一致・ディレクトリ一致をしない。
  2. 許可の照合は、regular file かつ path の全要素が symlink でない場合だけ成立する。
  3. 許可した各 path について、(a) その path が symlink、(b) その path の親ディレクトリが symlink、(c) 同じ basename を別ディレクトリに置いたもの、のいずれも拒否される。
- 判定方法：差分の文書検査と自動テスト（ST-TC-655-06-1）。

### ST-TD-655-07 孤児 cache の無視条件と実証（Issue AC7）
- 1b依存：P2（2B を採る場合は、CP に 2A 不採用の理由があり、C2 が ST-TD-655-02 の回復手順として判定されることで合格）
- 合格条件（2A を採る場合）：
  1. 次の4条件をすべて満たす cache だけが無視される。条件を1つだけ外した fixture では、すべて拒否される。
     (i) 親ディレクトリ名が厳密に `__pycache__`、(ii) ファイル名が `<stem>.<tag>.pyc` または `<stem>.<tag>.opt-<1|2>.pyc`、(iii) 対応 source が作業面に無く（`lexists` が偽）かつ HEAD にも無い、(iv) regular file で path の全要素が symlink でない。
  2. 実証記録が `codex_worktree_exec/verify/logs/` に commit されている。記録は現行 runtime（`python3`）で、timestamp・checked-hash・unchecked-hash の3種の cache それぞれについて、source を削除した後の `import` が `ModuleNotFoundError` になり、cache に埋めた副作用（marker ファイル作成）が実行されないことを示す。実行コマンド、Python の version と `sys.implementation.cache_tag`、終了コード、出力を含む。
  3. 無視した cache の source が後から HEAD に現れた fixture（別内容で commit）では、次の検査がその cache を通常の検証で拒否する。
  4. CP が、実証の範囲が import 経路であることと、`python3 <cache path>` のような直接 path 実行を検査の脅威範囲外とする判断（または範囲内とする対策）を記録している。
- 判定方法：自動テスト（ST-TC-655-07-1・07-2）と実証ログの文書検査（ST-TC-655-07-3）。

### ST-TD-655-08 不変条件・read-only 性・契約文書（Issue AC8・F-655-02）
- 1b依存：なし（版判断の結論は CP）
- 合格条件：
  1. `origin/main`（snapshot `ec711e7`）との差分が、`.codex/config.toml`、`codex_worktree_exec/profile_pin.py`、`codex_worktree_exec/project_trust.py`、`codex_worktree_exec/worktree_binding.py` で0行である（D1 profile pin・read-only profile・project trust・D5）。
  2. C0〜C8 をすべて置いた fixture で検査を呼ぶ前後で、`.git` を除く作業面の全ファイルの（相対 path、種別、size、sha256、mode、`mtime_ns`）の集合と、`git status --porcelain=v1 -z --ignored` の出力が一致する。検査が通る場合と拒否する場合の両方で確かめる。
  3. `docs/methods/codex-workspace-binding.md` の「未追跡通常source…」段落（snapshot 時点の L296〜313）が新しい分類と方式を現在形で記述し、旧記述に訂正を追記する形になっていない。同文書末尾の「本是正は同一PR内の2.0遷移の補完であり…」の文が残っていない。
  4. 版付き文書の bump 要否の判断が `.ai/guidance/common.md`「正本・実装規約」に従って記録されている。据え置く場合は理由が文書本文にある。bump する場合は、repo 内の `issue-start/<版>` リテラルがすべて同じ値である。
- 判定方法：差分検査・自動テスト・文書検査（ST-TC-655-08-1〜08-3）。

### ST-TD-655-09 削除 pull と別 runtime 実行の再現（Issue AC9）
- 1b依存：P1・P2・P6
- 合格条件：
  1. 削除 pull：source を2件 commit し、現行 runtime で import して cache を作る。別 clone で1件の削除を commit し、元の作業面で `git pull --ff-only` する。その後、検査が通る。または回復コマンドを1回起動した後に検査が通る。オーナー許可の手作業削除を手順に含まない。
  2. 別 runtime（模擬）：HEAD と一致する source の `__pycache__` に、現行と異なる tag の cache を3件以上置く。回復前は C3 として拒否され、診断に件数と回復コマンドが出る。回復コマンドを1回起動した後は検査が通る。
  3. 別 runtime（実機）：3a で、`uv run` で起動した現行と異なる version の Python が作業面の module を import した後に、2 と同じ結果になる。
- 判定方法：自動テスト（ST-TC-655-09-1・09-2）と 3a の実機確認（ST-TC-655-09-3）。

### ST-TD-655-10 harness 生成物で止まらない（Issue AC10・観測 #7・F-655-01）
- 1b依存：P3（判定する結果は P3 によらない）
- 合格条件：一時 repo で次の生成元の実コード経路を実行した後、検査が通る。または回復コマンドを1回起動した後に検査が通る。
  - `karte append`（`tmp/_karte/.writer.lock`）、`adr new-entry`（`tmp/_adr-notify/*.root` と ADR root の `.write.lock`）、ADR の `file-issue` 経路（`.file-issue.lock`）、`gitgate show-pr-diff` の差分ファイル保存経路（4096 byte を超える差分）、feedback 下書き保存（`tmp/_feedback/*.toml`）
  - P3 で作業面外へ移す生成元：生成物の実 path が作業面の外にある。
  - P3 で許可に追加する生成物：ST-TD-655-06 を満たす。
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
  3. 各分類の診断は、分類識別子（P7）、件数、代表例1件以上 N 件以下（P5）、回復手順（C0 は承認経路の案内。空にしない）を含む。1分類に300件を置いた fixture でも代表例は N 件以下で、件数は300と表示される。
  4. 診断の行数が、P4 で記録した契約と一致する（テストで固定する）。
- 判定方法：自動テスト（ST-TC-655-12-1〜12-3）。

### ST-TD-655-13 coverage 実行で作業面に残さない（Issue AC13・Scope 5）
- 1b依存：なし
- 合格条件：
  1. `.ai/skills/coverage-html/SKILL.md` の手順の `uv run` コマンドすべてで、coverage data file・HTML 出力先・bytecode の出力先が作業面外に指定されている（`COVERAGE_FILE` 等の data file 指定、`coverage html` の出力ディレクトリ指定、`PYTHONPYCACHEPREFIX` か `PYTHONDONTWRITEBYTECODE=1`）。
  2. `python3 -m asset_parity check` が `MISSING` を出さない。
  3. 3a で手順どおりに実行した後、`git ls-files --others` の実行前との差分に、`.coverage`、`.coverage.*`、`htmlcov/` 配下、現行と異なる tag の `.pyc` が1件も無い。
- 判定方法：文書検査（ST-TC-655-13-1）と 3a の実機確認（ST-TC-655-13-2）。

### ST-TD-655-14 lint と単体テスト（Issue AC14）
- 1b依存：なし
- 合格条件：最終 commit で次がすべて終了コード0。
  - `python3 -m maintainability_lint check`
  - `python3 -m issue_envelope check --repo .`
  - `python3 -m unittest tests.unit.test_codex_source_snapshot tests.unit.test_codex_compiled_cache tests.unit.test_codex_artifact_binding tests.unit.test_readonly_workspace tests.unit.test_phase_dispatch_binding tests.unit.test_legacy_pr_rereview tests.unit.test_issue_start_gate`、および本 Issue で追加・変更したテストモジュール
  - `python3 -m unittest discover -s tests -t .` の失敗集合が、base `ec711e7` で同じコマンドを実行したときの失敗集合の部分集合（新しい失敗0件）
- 判定方法：コマンド実行（ST-TC-655-14-1）。

### ST-TD-655-15 回復コマンド（prune）の安全性（Scope 1 の 3B・契約 (c)）
- 1b依存：P6（コマンド名・引数）
- 合格条件：
  1. 回復コマンドは検査とは別のコマンドで、検査の呼出し経路（4経路）から呼ばれない。
  2. 削除する対象は、指定した作業面の中で、親ディレクトリ名が `__pycache__`、拡張子が `.pyc`、git で未追跡、regular file、path の全要素が symlink でない、のすべてを満たすファイルだけである。次は削除しない（実行前後で bytes と存在が一致）：追跡済みの `.pyc`、`__pycache__` 外の `.pyc`、`__pycache__` 内の `.py` などの他の拡張子、symlink とその参照先、作業面の中に置かれた別の登録済み linked worktree の中身、作業面の外のファイル。
  3. 2回続けて起動すると、2回目は削除0件で終了コード0。
  4. 両 PF の `agent-command-gate.sh` が、gated ロール（`issue-implementer`・`issue-fixer`・`pr-reviewer`・工程6ロール）による回復コマンドの起動を拒否する。
- 判定方法：自動テスト（ST-TC-655-15-1・15-2）。
