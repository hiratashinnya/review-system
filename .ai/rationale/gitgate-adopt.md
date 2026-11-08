# gitgate adopt-branch: safety rationale (#760)

This rationale was originally the public `gitgate/adopt.py` module docstring. It is preserved here to accompany the smaller responsibility-based modules.

``adopt-branch``: 既存ブランチを worktree 側で checkout する（Issue #354・PR-2・FR-W10）。

**なぜ ``new-branch`` と別 verb なのか**
------------------------------------
``branch_source.policy`` の :func:`verify_branch_source` / :func:`create_branch` は
「**新規**ブランチをどこから生やすか」を fresh evidence へ束縛する流れで、分岐点が
「default branch の先端」か「same-repository の OPEN PR の head」かの二分岐になっている。
``adopt-branch`` が解くのは別の問題——**既に存在するブランチ**（前ラウンドの
``issue-implementer`` が push 済みのもの）を、新しく切り出した worktree の中で
「本当に自分が想定している OID か」を確かめてから checkout することである。
分岐点の二分岐は無く、代わりに「remote の先端が期待 OID と一致するか」「（任意で）その OID が
指定 PR の head として open か」「ローカルに同名ブランチが無いか」を見る。

したがって本モジュールは ``policy.py`` のフローをコピー流用せず、**必要な部分だけを薄く
再実装**する。``repository`` と ``branch`` は検証規則を二重定義すると「片方だけ緩い」という
ズレが生まれるため、``branch_source`` の公開 validator（:func:`validate_repository` /
:func:`validate_branch_ref`）を共有する。read-only の GitHub client
（:class:`GitHubBranchClient`）もそのまま再利用する。

**OID だけは意図的に共有しない**。``branch_source`` 側は 40hex/64hex（SHA-1/SHA-256）の
どちらも受けるが、``adopt-branch`` は「その worktree が掴む commit を一意に固定する」ことが
目的なので ``_ADOPT_OID``（40hex ちょうど）で**より厳しく**判定する。ここで共有側の緩い規則に
揃えると adopt の目的が達成できないため、二重定義ではなく**意図的な非共有**である
（Issue #354 F-354-05）。

fail-close
----------
引数検証・remote 検証・PR 検証・ローカル衝突検査の**いずれか1つでも欠ければ git を実行しない**
（``git switch`` に到達するのは全段を通過したときだけ）。API へ到達できない場合も
``API_UNREACHABLE`` で fail-close する（「確認できなかった」を「問題なし」に潰さない）。

stage 4（ローカル同名ブランチの検査）の defense-in-depth（Issue #426）
------------------------------------------------------------------
``gitgate/worktree.py`` の ``worktree_release()`` は解放時に対応するローカルブランチ ref を
削除するが（``_cleanup_branch_ref``）、その削除はフェイルオープンであり、また
``worktree_release()`` を経由しない経路（旧版の実体・手動操作等）で残った stray ref も
ありうる。そのため stage 4 は「ローカル同名 ref があれば即 ``BRANCH_ADOPT_LOCAL_EXISTS``」
ではなく、まず**無害な残留 ref か本当の衝突かを判定**する：

1. ローカル ref の tip が ``refs/remotes/origin/<branch>`` の tip（stage 2 で検証済みの
   ``observed`` を再利用・再取得しない）と一致するか。
2. ``git worktree list --porcelain`` を見て、そのブランチが**いずれかの worktree**（main を
   含む・安全側）に checked out されていないか。

**両方を満たすときだけ**「無害な残留 ref」と判定し、``git branch -D`` で削除してから段5へ
進む（先行 worktree が既に消えている前提が壊れていないことを、削除の直前に確認している）。
**どちらか一方でも満たさなければ**（tip が食い違う＝別コミットを指すローカル作業／
``git worktree list`` が到達不能や異常終了＝判定不能／他 worktree が checked out 済み）
**既存どおり ``BRANCH_ADOPT_LOCAL_EXISTS`` で fail-close する**——未知のローカル作業を
黙って破棄しない。判定不能は「無害」ではなく「衝突」側に倒す（fail-close の一貫性）。
reclaim の ``git branch -D`` 自体が失敗した場合も同じ理由で fail-close する。

失敗文言に「誰が掴んでいるか」を載せる（Issue #502）
--------------------------------------------------
``BRANCH_ADOPT_LOCAL_EXISTS`` は**復旧手順へ直結する**必要がある。旧実装はブランチ名しか
返さず、主文脈が ``tmp/_worktree/ledger.json`` と ``.git/worktrees/`` を手で突き合わせる
羽目になっていた（Issue #502 の実測）。:func:`describe_local_ref_conflict` が掴んでいる主体を
区別して文言に載せる:

* **primary checkout（メインワークツリー）** — `pr-reviewer` 等が差分確認のためブランチを
  切り替えたまま戻していない場合（Issue #502 観測2）。``gitgate`` の worktree verb では
  解消できないので、``git switch <既定ブランチ>`` へ誘導する。
* **agent worktree** — 異常終了で残った dispatch の worktree（同観測1）。台帳エントリ
  （``entry_id`` と ``status``）を引けたら併記し、``collect-worktree --entry`` へ誘導する。
* **その他の linked worktree** — 台帳の管理外。パスを出して手当てを促す。
* **tip 不一致** — そもそも掴んでいる主体の問題ではなく、正体不明のローカル作業がある。
  ``git worktree list`` を呼ばずに local/origin の OID を出して止める（既存の
  短絡判定を維持する＝呼ぶ意味が無い）。

台帳の参照は**best-effort**（診断のためだけ）で、引けなくても判定（fail-close）は変わらない。

reason code:
  * ``BRANCH_ARGUMENT_INVALID`` / ``BRANCH_NAME_INVALID`` / ``BRANCH_REPOSITORY_INVALID``
  * ``BRANCH_ADOPT_OID_INVALID`` / ``BRANCH_ADOPT_PR_INVALID``（引数スキーマ）
  * ``BRANCH_ADOPT_REMOTE_MISSING``（``origin/<branch>`` が解決できない）
  * ``BRANCH_ADOPT_OID_MISMATCH``（remote 先端が期待 OID と違う）
  * ``BRANCH_ADOPT_PR_NOT_OPEN`` / ``BRANCH_ADOPT_PR_HEAD_MISMATCH``（PR 再検証）
  * ``API_UNREACHABLE`` / ``API_UNAVAILABLE``（``GitHubBranchClient`` 由来）
  * ``BRANCH_ADOPT_LOCAL_EXISTS``（ローカルに同名ブランチが既にある）
  * ``BRANCH_ADOPT_ALREADY_CHECKED_OUT``（別 worktree が同じブランチを掴んでいる）

依存仕様:
  * ``branch_source/policy.py`` の :class:`BranchSourceError` / :class:`GitHubBranchClient` /
    公開 leaf validator（``validate_repository`` / ``validate_branch_ref``。同一 PR で公開名を
    追加。OID validator は上記のとおり共有しないので公開もしていない）。
  * 起票先区分は `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
    **汎用開発ハーネス**（Issue 運用パイプライン）。out-of-graph のため版なし。

## G-04 decomposition

- `adopt_models` / `adopt_parse`: immutable schema and strict OID/argument parsing.
- `adopt_git` / `adopt_remote` / `adopt_pr`: bounded fetch, fresh remote identity, optional PR identity.
- `adopt_holders` / `adopt_diagnostics` / `adopt_local`: checked-out holder classification, actionable errors, guarded stray-ref reclaim.
- `adopt_checkout`: exact OID checkout and upstream binding.
- `adopt.py`: stable public imports and stage ordering.

All gates fail closed before checkout; no additional CLI verbs or permissions are added.
