# Dispatch の handoff 完了判定

Issue #371 の先行リファクタリングで `subagent_hooks.py` から判定を抽出した。
対象ロール、返り値、回収・保留・異常の区別は従来のままである。
以下は元の実装説明を保存したもので、実体は `handoff_completion.py` にある。

**この dispatch 自身が書く** handoff のファイル名にだけ一致する正規表現。

    ``<agent_type>--issue-<N>[<境界><suffix>].yaml`` で、``issue-<N>`` の直後は ``-`` か
    ``.`` に限る（``issue-3541`` を ``issue-354`` と取り違えないための境界検査）。規則は
    ``gitgate/worktree.py`` の ``HANDOFF_FILENAME_RE`` および各 agent 契約の
    「``handoff_path`` の検査」条件4・5 と同一だが、**フックは ``gitgate`` を import しない**
    （起動するだけ）という境界を保つためここで独立に組み立てる。

    ``agent_type`` を名前に含めるのが要点である。入れ子委譲を行う dispatch では、委譲先
    （``verification-author`` / ``reconciliation`` 等）の handoff が**同じ**
    ``tmp/_handoff/`` に溜まる。所有者を見ずに数だけ数えると、他人の成果物1件を自分のものと
    誤認したり、2件以上で ``ambiguous`` に落ちて回収不能になったりする（Issue #423 の実測）。

dispatch の worktree から**自分の**回収対象 handoff を1つに決める。

    返り値は ``(relative_path | None, how)``。``how`` は evidence 用の識別子。

    現行の ``ISSUE_START_BINDING_V1`` marker には ``handoff_path`` が無く、台帳の
    ``handoff_path`` は ``None`` のまま起票される。そのため ``collect-worktree --entry <id>``
    だけでは回収元が決まらず ``COLLECT_HANDOFF_UNKNOWN`` で必ず落ちる。ここで**実在する
    ファイルを列挙して**決めることで、marker を触らずに回収を成立させる。

    判定は次のいずれかになる（推測しない）:

    * :func:`own_handoff_pattern` に一致するファイルが**ちょうど1件** → そのパス
      （``how="unique"``）。これが唯一の「終了した」signal である。
    * 一致が**0件** → ``(None, "empty")``。``tmp/_handoff`` 自体が無い場合も、他人
      （委譲先エージェント）の handoff だけがある場合も同じ扱いで、**「終了」とは言えない**。
      呼び出し側は解放も ``stale`` 化もせず ``running`` のまま保留する（Issue #423）。
    * 一致が**2件以上** → ``(None, "ambiguous")``。どれが今回の成果物か決められないので
      **解放しない**（呼び出し側が ``stale`` へ落として主文脈の判断へ回す）。
    * ``tmp/_handoff`` が symlink、または存在するがディレクトリではない（regular file 等）
      → ``(None, "unreadable")``。**これは「無い」ではなく「列挙できない」**——symlink は
      構成要素を辿らないと本当に空か分からず、regular file は中身を列挙できない（F-354-07）。
      保留（``empty``）と違い「観測できていない」異常なので ``stale`` へ落とす。
    * 台帳の ``issue`` が整数として読めない → ``(None, "unidentifiable")``。自分の handoff を
      名指しできない＝同じく異常なので ``stale`` へ落とす。
