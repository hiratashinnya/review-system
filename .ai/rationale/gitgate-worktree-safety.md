# gitgate worktree 操作の設計根拠（#757）

元 `gitgate/worktree.py` のトップレベル説明を、責務分割しても失われないよう移設したもの。動作上の規則の変更ではない。

worktree の回収・解放 verb（Issue #354・PR-2／Issue #502）。

本モジュールが実装する4 verb:

``worktree-release``
    linked worktree を**冪等に**解放（削除）する（FR-W5）。台帳の状態が「解放してよい」と
    言っているときだけ削除する。``running``（live な dispatch が所有）と ``stopped``
    （停止済みだが未回収）は ``--force-*`` でも上書きできない。
    **実体の削除経路はここだけ**——``abandoned``（``worktree-forget`` 済み）で実体が残って
    いる場合も、台帳を進めずに実体だけ削除する（F-354-02）。
    **worktree 実体の削除に成功し、かつ ``cleanup_branch_ref=True``（既定）のときは、台帳の
    ``branch_name`` に対応するローカルブランチ ref の削除を試みる**（``git branch -D``・
    Issue #426。F-426-01 で安全化）。``cleanup_branch_ref=False`` を渡す呼び出し元
    （``issue-start-gate`` の毎 dispatch 経路・Issue #464 F-464-06）ではこの削除を丸ごと
    スキップする——``git fetch`` を伴うため、毎 dispatch のホットパスにネットワーク I/O を
    持ち込まない。フル掃除は ``SessionStart`` フックが別途 ``cleanup_branch_ref=True`` で
    行う。放置すると、
    その ref が ``gitgate adopt-branch`` の stage 4（同名ローカル ref の存在検査）に
    引っかかり、次の ``issue-fixer`` の adopt が ``BRANCH_ADOPT_LOCAL_EXISTS`` で失敗する。
    ただし ``git branch -D`` は force delete でありローカルにしか無いコミットを reflog ごと
    黙って破棄しうるため、削除の前に fresh fetch した ``refs/remotes/origin/<branch>`` に
    対してローカル ref の tip が祖先であることを確認し、確認できない場合は削除せずスキップ
    する（:func:`_cleanup_branch_ref`）。この判定は**フェイルオープン**——削除・スキップの
    どちらの結果でも worktree 実体の削除という主契約は成立済みなので ``worktree_release()``
    全体を失敗させない。成否・スキップ理由は必ず ``_note()`` で台帳に記録する。他 worktree
    が checked out 中のブランチを誤って消さない安全網は ``git branch -D`` 自身の拒否に委ねる
    （``git worktree remove`` の成功が保証するのは「この worktree がもう branch_name を
    掴んでいない」ことだけで、別の worktree の不在までは含意しない）。削除されずに stray ref
    が残った場合の安全網は ``adopt_branch()`` 側の tip 一致検査（``BRANCH_ADOPT_LOCAL_EXISTS``
    への fail-close、無害なら reclaim。詳細は ``gitgate/adopt.py`` のモジュール docstring）。

``collect-worktree``
    **回収 → 検証 → 解放を1操作に畳む**（候補D・FR-W2）。段構造で、前段が失敗したら後段を
    実行しない——特に「handoff を回収できていないのに worktree を消す」ことが起こらない。
    これは検査で守るのではなく、呼び出し順序そのもので守る。
    **回収は済んだが最後の ``git worktree remove`` が worktree ロックで失敗した場合**
    （停止途中のエージェントがまだ掴んでいる・Issue #464）は、成果物が ``collected_to`` へ
    退避済みで失われていないので例外を投げず、台帳を ``release_pending`` にして削除だけを
    ``issue-start-gate`` の次回実行へ遅らせる（``ISSUE_START_WORKTREE_RESIDUE`` で次
    dispatch を止めない）。

``worktree-forget``
    回収不能な ``stale`` エントリを ``abandoned`` へ逃がす。**worktree は消さない**
    （消すのは ``worktree-release``。責務を混ぜない。``abandoned`` にした後で
    ``worktree-release <path>`` を呼べば、台帳を ``released`` へ進めずに実体だけ消える）。
    **エントリも消さない**——
    `.claude/rules/01-principles.md`「PR8「消さない」の適用範囲」区分1（決定履歴の保全）に
    従い、``reason`` 付きで状態遷移だけを記録する。

``worktree-sweep-abandoned``
    **異常終了（レートリミット／セッション上限による強制停止）で ``running`` のまま取り残された
    エントリを回収・解放する**（Issue #502・観測1）。``SubagentStop`` フックが発火しない終了経路
    では台帳が ``running`` に留まり、worktree も対象ブランチを掴んだまま残るため、次の
    ``adopt-branch`` が ``BRANCH_ADOPT_LOCAL_EXISTS`` で必ず失敗して是正ループが止まる。

    **``running`` は「入れ子委譲待ちの正当な保留」でもある**（Issue #423）ため、状態だけでは
    異常終了と区別できない。区別に使うのは**呼び出し地点そのもの**である——
    :func:`sweep_abandoned_running` は「live な dispatch が1つも無いことを呼び出し元が観測した」
    という申告（``no_live_dispatch=True`` ／ CLI では ``--no-live-dispatch``）が無ければ**何も
    しない**。この申告を出せる地点は現状ひとつだけで、``.claude/hooks/resume-watcher.sh`` が
    レートリミット解除を確認し、かつ対象ペインが**アイドル**（``pane_guard`` が WORKING を
    返さない）と観測した復帰イベントである。オーナー指示
    （2026-09-08）どおり**復帰の契機は既存のレートリミット復帰イベントに相乗りし、検知経路を
    二重化しない**。

    **この申告の観測範囲は watcher に渡された単一 tmux ペインに限られる**（F-502-02）。
    ``pane_guard`` は引数で渡された ``$PANE`` しか見ないのに対し、台帳はリポジトリ全体で
    共有される。したがって別ペイン・別セッションで live な dispatch が動いていても
    ``no_live_dispatch`` は真になりうる——この申告は「**そのペインからは**サブエージェントが
    実行中でない」以上のことを主張しない。

    **クロスペインの保護を担うのは git の ``locked`` だけである**：
    ``git worktree list --porcelain`` が ``locked`` を報告する worktree を掃引対象から外す
    （ハーネスが live な agent worktree をロックする構成であれば、これが #423 の入れ子委譲中
    エントリを別ペインからも守る）。**ハーネスがロックしない構成ではこの保護は成立しない**ので、
    その環境では掃引そのものを止める（``CLAUDE_RL_SWEEP_WORKTREES=0``）。

    **成果物を失わない側に倒す**: 自分の handoff が1件あれば ``collect-worktree`` と同じ段
    （回収 → sha 検証）を通し、**その上で作業ツリーが clean であることを確認できたときだけ**
    解放する。handoff が無い場合は「捨ててよいと**積極的に確認**できた」ときだけ解放する
    （作業ツリーが clean かつ HEAD が ``origin/<branch>`` に含まれる）。確認
    できなければ解放せず ``stale`` へ落とし、既存の ``ISSUE_START_WORKTREE_RESIDUE`` deny
    （解消コマンド付き）へ合流させる。**clean 検査を handoff の有無で免除しない**
    （F-502-01）——実体の削除は ``git worktree remove --force`` であり、dirty/untracked を
    問答無用で消す。handoff が書けていることは「作業ツリーに未コミットの何かが残っていない」
    ことを含意しない。

本 PR のスコープ（重要）
----------------------
ここで実装するのは**実体だけ**で、gated ロール（``issue-implementer`` / ``issue-fixer`` /
``pr-reviewer``）への権限付与は行わない。``agent-command-gate.sh`` の
``GITGATE_VERBS_BY_ROLE`` は allowlist であり、**未登録の verb は既定 deny** される。
したがって実装が先行しても gated ロールの権限は1ミリも増えない（登録は PR-3/PR-4）。

削除経路を持つがゆえのガード
--------------------------
本モジュールは PR-1（``issue_start/worktree_ledger.py``）と違い**削除経路を持つ**ため、
「何を消してよいか」を構造で絞る。:func:`validate_worktree_path` を通過するのは
``.claude/worktrees/agent-<id>`` ちょうどの形だけで、絶対パス・``..``・サブディレクトリ・
symlink 構成要素・repo-root 外へ解決されるパスはすべて git を呼ぶ前に拒否する。
さらに ``git worktree list --porcelain`` に linked worktree として現れないパスは消さない
（git 管理外のディレクトリを ``git worktree remove`` の名の下に消さない）。

時刻の扱い（`.claude/rules/04-test-data.md` 遵守）
------------------------------------------------
``now`` は**必ず引数で注入する**。本モジュールは ``datetime.now()`` / ``time.time()`` を
一切呼ばない（wall clock を読むのは CLI 境界＝``gitgate/cli.py`` だけ）。TTL・経過時間による
判定も設けない——判定は状態（台帳の ``status``）と実在の突き合わせだけで行う。

依存仕様:
  * ``issue_start/worktree_ledger.py``（PR-1・状態遷移と台帳 I/O。``WORKTREE_PATH_RE`` /
    ``ENTRY_ID_RE`` は再定義せず import 再利用する）
  * ``.claude/agents/issue-implementer.md`` / ``issue-fixer.md`` の「``handoff_path`` の検査」
    （6条件。:func:`validate_handoff_relpath` が同一の規則を機械化したもの）
  ※ いずれも out-of-graph（版なし）。本モジュールは
    `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
    **汎用開発ハーネス**区分（Issue 運用パイプライン）に属する。

## G-02 collect/release 分割の境界（#758）

- `worktree.py` は既存の公開入口と sweep/forget を保持する。G-03 の sweep 機能や動作は変更しない。
- collect は対象と status を FS/Git 操作より先に検査し、handoff の読取り → 排他的作成 → sha256 読み戻し検証 → 台帳 collected 記録 → 解放の順を維持する。照合失敗時だけ未完成の回収先を消し、解放しない。
- `released`/`abandoned` は回収で終端 no-op、`running` は強制指定でも拒否する。`release_pending` は回収をやり直さず削除だけ再試行する。
- git worktree remove のロック由来失敗は、`collected_to` が記録された場合に限り `release_pending` として後続へ遅延する。それ以外の失敗は例外を維持する。
- ローカル branch ref は fresh fetch と ancestry 確認を経た場合だけ削除し、判定不能なら台帳に理由を残して fail-open。ネットワーク fetch を毎 dispatch 経路から外す `cleanup_branch_ref=False` 契約は維持する。
- `gitgate.worktree._write_collected` の実行時差替えを維持するため、facade が writer を回収パイプラインへ明示注入する。壁時計参照の追加はない。
