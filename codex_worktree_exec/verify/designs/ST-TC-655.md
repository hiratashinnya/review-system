# ST-TC-655 — 工程入力検査の未追跡分類見直し（システムテストケース）

- 作成：ac-designer（Claude Code (AI)）／VD ルート：`verification_design/VD-655.toml`／TD：[ST-TD-655](ST-TD-655.md)
- 分類記号 C0〜C8 と 1b パラメータ P1〜P8 は ST-TD-655 §2・§3 の定義を使う。
- 本書は試験ケースの仕様（前提・手順・期待結果・判定）である。自動テストの実コード化は CP の work unit で担当と配置（`tests/` 配下）を決める。「3a」と書いたケースは merge 後の ST-TR で主文脈が実行する。
- 共通 fixture（F0）：`tests/unit/codex_worktree_exec_support.make_repository` と同等の一時 git リポジトリ。`ordinary.py` を commit 済み。テストは実行中の Python（`python3`）だけを使い、別 runtime の導入を前提にしない。

| TC | TD | 形態 | 前提・手順 | 期待結果（合格条件） |
|---|---|---|---|---|
| ST-TC-655-01-1 | 01 | 文書 | CP と参照 ADR を読み、C1〜C8（C7a〜C7e）の13行を数える | 13行すべてに方式・理由・却下理由がある。3A がオーナー決定で不採用、1B が契約 (a) 違反で却下と書かれている。回復方式の行に P6 のコマンドがある |
| ST-TC-655-02-1 | 02 | 自動 | F0 に C1 の `.claude/scheduled_tasks.lock`（regular file）を置き、検査する | P1 の方式どおり（許可なら例外なし。拒否なら診断に C1 識別子・件数1・代表例・回復手順） |
| ST-TC-655-02-2 | 02 | 自動 | F0 に source の無い `pkg/__pycache__/gone.<現行tag>.pyc` と `pkg/__pycache__/gone.cpython-313.pyc` を置く | P2 が 2A なら例外なし。2B なら拒否され、診断に C2・件数2。回復コマンド1回の後は例外なし |
| ST-TC-655-02-3 | 02 | 自動 | F0 の `ordinary.py` に対し `__pycache__/ordinary.cpython-399.pyc` を3件の optimization（無し・opt-1・opt-2）で置く | 拒否され、診断に C3・件数3・回復手順。回復コマンド1回の後は例外なし |
| ST-TC-655-02-4 | 02 | 自動 | F0 に `.coverage`、`.coverage.host.1.2`、`htmlcov/index.html` を置く | P1 の方式どおり。拒否なら診断に C4・件数3 |
| ST-TC-655-02-5 | 02 | 自動 | F0 に `.serena/.gitignore`、`.serena/project.yml`、`.serena/memories/a.md` を置く | P1 の方式どおり。拒否なら診断に C5・件数3。ディレクトリ単位の許可で通していない（ST-TC-655-06-1 と併せて判定） |
| ST-TC-655-02-6 | 02 | 自動 | F0 の `ordinary.py` を compile した cache の code 部分を別内容の compile 結果に置き換える（tag は現行） | 拒否され、診断に C6・件数1・回復手順。回復コマンド1回の後は例外なし |
| ST-TC-655-02-7 | 02 | 自動 | F0 に C7a〜C7e の各生成物を、生成元と同じ path・中身で置く（C7c は 4096 byte 超の `.diff`） | P1・P3 の方式どおり。作業面外へ移す方式の生成物は、本ケースではなく ST-TC-655-10-1 で生成元の出力先を判定する |
| ST-TC-655-02-8 | 02 | 自動 | F0 に `tmp/run.sh`、`tmp/result.out` を置く | P1 の方式どおり。拒否なら診断に C8・件数2 |
| ST-TC-655-03-1 | 03 | 自動 | F0 に C0 を2件（`a_source.py`、`z_source.py`）、C3 を2件、C6 を2件、C8 を2件置き、検査を1回呼ぶ | 例外は1回。診断に C0・C3・C6・C8 の識別子があり、件数はそれぞれ2 |
| ST-TC-655-03-2 | 03 | 自動 | 03-1 のファイル名を変えて列挙順を逆にする（C0 を `0_source.py`／`~source.py` 等で先頭・末尾へ） | 03-1 と同じ分類集合・件数 |
| ST-TC-655-04-1 | 04 | 自動 | C0 の各ファイル（`source.py`、`pkg/module.py`、`tests/unit/test_extra.py`、`tool/config.toml`、`tmp/injected.py`、`sub/.claude/scheduled_tasks.lock`、`__pycache__/x.py`、`__pycache__/module.pyc`、`module.pyc`）を1件ずつ置く。ignore 設定なし／`.gitignore` のみ／`.git/info/exclude` のみ／`core.excludesFile` のみ／3つ全部、の5通りで検査する。`.gitignore` は commit してから使い、`core.excludesFile` の実体は作業面外に置く（ignore 設定のファイル自体を未追跡にしない） | 9ファイル×5通り＝45回すべてで拒否される。`.py`・`.toml`・lock の7ファイルは C0 として件数1。`__pycache__/module.pyc` と `module.pyc` は C0 または CP 対応表の拒否分類として件数1 |
| ST-TC-655-04-2 | 04 | 自動 | 04-1 の各ファイルについて、`source_changes` に path と正しい sha256 を渡して `verify_source_snapshot` を呼ぶ | すべて拒否 |
| ST-TC-655-05-1 | 05 | 自動 | `tests/unit/test_codex_compiled_cache.py` の既存ケースを変更後のコードで実行する | 既存の拒否ケースがすべて拒否のまま。拒否を確かめる assertion の数が base `ec711e7` から減っていない |
| ST-TC-655-05-2 | 05 | 自動 | F0 で `ordinary.py` の cache を作った後、(a) 作業面だけで `ordinary.py` を削除（HEAD には残る）、(b) 未追跡の `extra.py` を作って cache を作る、(c) `ordinary.py` を作業面で改変、(d) `ordinary.py` を削除して同名ディレクトリを作る、の4通り | 4通りすべてで拒否され、その cache が診断の件数に数えられている（C2 として無視されない）。(b) では未追跡 `extra.py` 自体の C0 とは別に、cache が数えられている |
| ST-TC-655-06-1 | 06 | 自動＋差分 | 差分で追加された許可エントリを列挙する。各エントリ `E` について、(a) `E` を symlink にする、(b) `E` の親ディレクトリを symlink にする、(c) `other/` 配下に同じ basename を置く、で検査する | エントリに `*`・`?`・`[` が無く末尾 `/` でない。(a)(b)(c) すべて拒否 |
| ST-TC-655-07-1 | 07 | 自動 | P2 が 2A のとき、無視条件 (i)〜(iv) を満たす cache を置いた基準 fixture と、1条件だけ外した5つの fixture（(i) 親が `cache`、(ii) 名前が `gone.pyc`、(iii-a) source を HEAD に commit して作業面からだけ削除、(iii-b) source を作業面に未追跡で置く、(iv) cache が symlink）で検査する | 基準 fixture は例外なし。5つの fixture はすべて拒否 |
| ST-TC-655-07-2 | 07 | 自動 | 07-1 の基準 fixture で、無視された cache の source を別内容で作成・commit してから検査する | 拒否（C6 または source 不一致として） |
| ST-TC-655-07-3 | 07 | 文書 | `codex_worktree_exec/verify/logs/` の実証記録を読む | timestamp・checked-hash・unchecked-hash の3種それぞれで、`ModuleNotFoundError` と marker 未作成が記録されている。コマンド、version、`cache_tag`、終了コード、出力がある。CP に直接 path 実行の扱いが記録されている |
| ST-TC-655-08-1 | 08 | 差分 | `git diff ec711e7 -- .codex/config.toml codex_worktree_exec/profile_pin.py codex_worktree_exec/project_trust.py codex_worktree_exec/worktree_binding.py` | 出力0行 |
| ST-TC-655-08-2 | 08 | 自動 | C0〜C8 をすべて置いた fixture と、許可・無視される分類だけを置いた fixture の2つで、検査前後の作業面の（相対 path、種別、size、sha256、mode、`mtime_ns`）と `git status --porcelain=v1 -z --ignored` を取る | 2つの fixture とも前後で完全一致 |
| ST-TC-655-08-3 | 08 | 文書 | `docs/methods/codex-workspace-binding.md` の該当段落と末尾を読み、`issue-start/` のリテラルを repo 全体から検索する | 段落が現行の分類と方式を現在形で記述し、「本是正は同一PR内の2.0遷移の補完であり」の文が無い。版判断と理由が文書本文にあり、`issue-start/<版>` のリテラルが1種類だけ |
| ST-TC-655-09-1 | 09 | 自動 | 一時 bare repo と2つの clone（A・B）を作る。A で `pkg/a.py`・`pkg/b.py` を commit・push し、A で両方を import して cache を作る。B で `pkg/a.py` を削除して commit・push し、A で `git pull --ff-only` する | 検査が例外なし。または回復コマンド1回の後に例外なし。手順に手作業の削除が無い |
| ST-TC-655-09-2 | 09 | 自動 | 09-1 の A で、HEAD と一致する `pkg/b.py` の `__pycache__` に現行と異なる tag の cache を3件置く | 回復前は拒否され、診断に C3・件数3・回復コマンド。回復コマンド1回の後に例外なし |
| ST-TC-655-09-3 | 09 | 3a | 主文脈が自分の linked worktree で `uv run --python 3.13 python -c "import codex_worktree_exec.source_snapshot"` 等により別 version の cache を作り、検査する。uv が使えなければ実行せず STOP して報告する | 09-2 と同じ結果。実行した Python の version と cache tag を ST-TR に記録する |
| ST-TC-655-10-1 | 10 | 自動 | 一時 repo で `karte append`、`adr new-entry`、ADR の `file-issue` 経路、`gitgate show-pr-diff` の保存経路（4096 byte 超の差分を与える。GitHub 呼出しは差し替える）、feedback 下書き保存を、それぞれ実コード経路で実行した後に検査する | 5経路すべてで検査が例外なし。または回復コマンド1回の後に例外なし。作業面外へ移す方式の生成元は、生成物の実 path が作業面の外 |
| ST-TC-655-11-1 | 11 | 自動 | 09-1 と同じ構成で、B が `pkg/b.py` の内容だけを変えて commit・push し、A で `git pull --ff-only` する（A は旧内容の cache を持つ） | 回復前は拒否され、診断に C6・件数1・回復コマンド。回復コマンド1回の後に例外なし |
| ST-TC-655-12-1 | 12 | 自動 | 03-1 の fixture で、`verify_artifact_binding`、`validate_phase_dispatch`、`readonly_workspace` の準備、`validate_pr_rereview` を呼ぶ | 4経路それぞれで、識別子（`CODEX_EXEC_BINDING_INVALID`／`ISSUE_START_PHASE_BINDING_INVALID`／P8／`ISSUE_START_PR_REREVIEW_INVALID`）と、C0・C3・C6・C8 の識別子と件数2を含む失敗が1回 |
| ST-TC-655-12-2 | 12 | 自動 | 03-1 の fixture を source 側に置いて `python3 -m issue_start.readonly_workspace` の `main` を呼ぶ | 終了コードが0以外。stderr に P8 があり、`Traceback` が無い |
| ST-TC-655-12-3 | 12 | 自動 | C3 を300件置いた fixture で検査する | 診断の C3 の件数が300。代表例は1件以上 N 件以下（P5）。診断の行数が P4 の契約と一致 |
| ST-TC-655-13-1 | 13 | 文書＋自動 | `.ai/skills/coverage-html/SKILL.md` の全 `uv run` 行を読み、`python3 -m asset_parity check` を実行する | すべての行で data file・HTML 出力先・bytecode 出力先が作業面外。`asset_parity` に `MISSING` が無い |
| ST-TC-655-13-2 | 13 | 3a | 主文脈が linked worktree で `git ls-files --others` を記録し、SKILL.md の手順を実行し、再度記録する | 差分に `.coverage`、`.coverage.*`、`htmlcov/` 配下、現行と異なる tag の `.pyc` が0件 |
| ST-TC-655-14-1 | 14 | コマンド | ST-TD-655-14 の4種のコマンドを最終 commit で実行する。`discover` は base `ec711e7` でも実行し、失敗した test id の集合を比べる | 4種すべて終了コード0（`discover` は新しい失敗0件） |
| ST-TC-655-15-1 | 15 | 自動 | 作業面に、削除対象の候補（未追跡 `pkg/__pycache__/a.cpython-399.pyc`）と、削除しない対象（追跡済み `tracked/__pycache__/t.cpython-399.pyc`、`pkg/legacy.pyc`、`pkg/__pycache__/note.py`、作業面外を指す symlink の `pkg/__pycache__/link.cpython-399.pyc`、作業面内の別の登録済み linked worktree 内の `pkg/__pycache__/w.cpython-399.pyc`）を置き、回復コマンドを2回起動する | 1回目で候補だけが消える。削除しない対象はすべて存在し bytes が一致、symlink の参照先も一致。2回目は削除0件・終了コード0 |
| ST-TC-655-15-2 | 15 | 自動 | 両 PF の `agent-command-gate.sh` に、gated ロール（`issue-implementer`・`issue-fixer`・`pr-reviewer`・工程6ロール）の agent_type で回復コマンドの Bash 起動を与える。検査の4経路のコードから回復コマンドへの呼出しが無いことも確かめる | 全ロールで deny。検査の4経路から回復コマンドを呼んでいない |
