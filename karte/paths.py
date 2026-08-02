"""カルテ置き場（``tmp/_karte/``）のパス解決とガード（fail-close）。

カルテは AI エージェントが書き換えるループ状態であり、パスの一部（issue 番号・レポート
ファイルの指定）は上流のプロンプト由来＝**信頼できない入力**として扱う。素直に
``open(path)`` すると ``..`` traversal や symlink 経由でリポジトリ外・リポジトリ本体の
ファイルを読み書きしうるため、「触ってよい形のパスか」を検査してからしか触らない
（``dsv2/cleantmp.py`` と同じ様式）。

ガード（すべて満たさなければ触らない）:
  1. 入力パスに ``..`` 構成要素を含まない（正規化前に拒否する。``root/link/../x`` のように
     正規化が symlink を飛ばしてしまう既知の穴を塞ぐため、**正規化より先**に見る）。
  2. 正規化後のパスが実体解決済み repo-root の配下にある。
  3. repo-root から対象までの各構成要素が symlink でない（symlink 越しの誘導を拒否）。
  4. 実体解決（``resolve()``）後もなお repo-root 配下にある（相対 symlink 等の取りこぼし対策）。
  5. カルテ本体は ``<repo-root>/tmp/_karte/issue-<N>.md`` ちょうどの形のみ。
     ``<N>`` は 1 以上の十進整数（前置ゼロ・符号・空白を認めない）。

「まだ無い」と「触ってはならない」は別物として送出する（:class:`KarteMissing` ⊂
:class:`KartePathError`）。前者は ``ingest-review`` 前の正常な初期状態なので、CLI は
EXIT_NOT_FOUND に落として運用側に「まず取り込め」と伝える。まとめて EXIT_ERROR にすると
未作成とガード違反の区別がつかない。

依存仕様: :mod:`karte` の docstring（Issue #307）／``dsv2/cleantmp.py`` docstring（ガード様式）。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

TMP_DIRNAME = "tmp"
KARTE_DIRNAME = "_karte"
ACTIVE_FILENAME = "active.json"

ISSUE_RE = re.compile(r"^[1-9][0-9]*$")
KARTE_FILENAME_FMT = "issue-{issue}.md"


class KartePathError(Exception):
    """ガード違反（触ってはならない形のパス）。読み書きは一切行われない。"""


class KarteMissing(KartePathError):
    """置き場（``tmp/`` ／ ``tmp/_karte/``）がまだ**存在しない**（未検出）。

    「触ってはならない形」（symlink・repo 外・traversal）とは区別する。前者は運用上の
    正常な初期状態（まだ ``ingest-review`` していない）で、呼び出し側は EXIT_NOT_FOUND に
    落としたい。:class:`KartePathError` の派生なので、ガード違反として一括で捕まえる
    既存の経路（``except KartePathError``）の fail-close はそのまま効く。
    """


def validate_issue(value) -> int:
    """issue 番号を検証して int で返す。パス構築の唯一の可変部分なので厳格に絞る。"""
    text = str(value)
    if not ISSUE_RE.match(text):
        raise KartePathError(
            f"issue 番号は 1 以上の十進整数のみ（前置ゼロ・符号・空白を認めない）: {value!r}"
        )
    return int(text)


def _resolved_root(repo_root) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise KartePathError(f"repo-root がディレクトリでない: {root}")
    return root


def main_worktree_root(candidate) -> Path:
    """``candidate`` から main worktree の root を決定論的に導出する（K-01）。

    ``karte`` パッケージ自体が linked worktree（``git worktree add``）にチェックアウト
    されて実行されうる（``issue-implementer`` は isolated worktree で走る前提）。
    ``Path(__file__)`` 由来の候補パスをそのまま repo-root にすると、worktree ごとに
    ``tmp/_karte/`` が分裂し、レビューアの ``ingest-review`` と是正側の ``append`` が
    別々の台帳を見てしまう。

    判定は ``candidate/.git`` の種別で行う:
      * **ディレクトリ**なら通常のリポジトリ（main worktree そのもの）＝ ``candidate`` を返す。
      * **ファイル**なら linked worktree の目印。中身は ``gitdir: <path>`` で、共有 git
        ディレクトリ配下の worktree 別サブディレクトリを指す。``<gitdir>/commondir``
        （実在すれば）が共有 ``.git`` ディレクトリへの相対パスを持つので、それを解決して
        その親を main worktree root とする。``commondir`` が無い簡易環境では、標準レイアウト
        ``<main>/.git/worktrees/<name>`` の ``.git`` セグメントから同じ結果を導出する。
      * ``.git`` が無い（git 管理下でない裸ディレクトリ等）場合は ``candidate`` をそのまま返す
        （git 未使用のテスト環境まで拒否すると既存呼び出しを壊すため）。

    ここで返す値は「どこを repo-root として扱うか」の**候補**にすぎない。実際の読み書きは
    引き続き ``_resolved_root`` / ``resolve_within_repo`` のガード1〜5を必ず通る
    （ここでガードを迂回しない）。
    """
    root = Path(candidate).resolve()
    git_path = root / ".git"
    if git_path.is_dir():
        return root
    if not git_path.is_file():
        return root

    text = git_path.read_text(encoding="utf-8", errors="replace").strip()
    prefix = "gitdir:"
    if not text.startswith(prefix):
        raise KartePathError(
            f".git ファイルの形式が不正（'gitdir:' で始まらない）: {git_path}"
        )
    gitdir = Path(text[len(prefix):].strip())
    if not gitdir.is_absolute():
        gitdir = root / gitdir
    gitdir = gitdir.resolve()

    commondir_file = gitdir / "commondir"
    if commondir_file.is_file():
        common_rel = commondir_file.read_text(encoding="utf-8", errors="replace").strip()
        common_dir = (gitdir / common_rel).resolve()
        return common_dir.parent

    # `commondir` が無い簡易環境向けフォールバック：標準レイアウト
    # `<main>/.git/worktrees/<name>` の `.git` セグメントから導出する。
    parts = gitdir.parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == ".git":
            return Path(*parts[: index + 1]).parent
    raise KartePathError(
        f"gitdir から main worktree の root を導出できない（commondir も無い）: {gitdir}"
    )


def resolve_within_repo(path, repo_root) -> Path:
    """``path`` が repo-root 配下の安全なパスかを検査し、正規化済みパスを返す。

    実在チェックは行わない（存在しないパスの「書き先」検査にも使うため）。
    ガード 1〜4 のいずれかに掛かれば :class:`KartePathError`（fail-close）。
    """
    root = _resolved_root(repo_root)
    given = Path(path)

    # ガード1: `..` は正規化より先に拒否する（正規化は symlink を無視して畳んでしまう）。
    if ".." in given.parts:
        raise KartePathError(
            f"'..' を含むパスは受け付けない（traversal 拒否）: {given}"
        )
    if not given.is_absolute():
        given = root / given

    # `.` と重複スラッシュのみを畳む（`..` は上で排除済みなので symlink を飛ばさない）。
    lexical = Path(os.path.normpath(str(given)))

    # ガード2: repo-root 配下か。
    try:
        rel = lexical.relative_to(root)
    except ValueError:
        raise KartePathError(
            f"repo-root の外を指している: {lexical}（repo-root={root}）"
        ) from None

    # ガード3: repo-root から対象までの各構成要素が symlink でないか。
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise KartePathError(
                f"パス構成要素が symlink: {cursor}（symlink 経由の読み書きは拒否）"
            )

    # ガード4: 実体解決後もなお repo-root 配下か（存在する範囲での再確認）。
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise KartePathError(
            f"実体解決の結果 repo-root の外を指した: {lexical} → {resolved}"
        ) from None
    return lexical


def karte_dir(repo_root, *, create: bool = False) -> Path:
    """``<repo-root>/tmp/_karte`` を返す（``create`` で不在時に作成）。"""
    root = _resolved_root(repo_root)
    tmp = root / TMP_DIRNAME
    if tmp.is_symlink():
        raise KartePathError(
            f"tmp ディレクトリ自体が symlink: {tmp}（repo 外へ誘導されうるため拒否）"
        )
    if not tmp.exists():
        if not create:
            raise KarteMissing(f"tmp ディレクトリが無い: {tmp}")
        tmp.mkdir(parents=True)
    if not tmp.is_dir():
        raise KartePathError(f"tmp がディレクトリでない: {tmp}")

    target = tmp / KARTE_DIRNAME
    if target.is_symlink():
        raise KartePathError(
            f"カルテ置き場が symlink: {target}（symlink 越しの書込は拒否）"
        )
    if not target.exists():
        if not create:
            raise KarteMissing(f"カルテ置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise KartePathError(f"カルテ置き場がディレクトリでない: {target}")
    return target


def karte_path(issue, repo_root, *, create_dir: bool = False) -> Path:
    """``<repo-root>/tmp/_karte/issue-<N>.md`` を返す（ガード5）。"""
    number = validate_issue(issue)
    directory = karte_dir(repo_root, create=create_dir)
    path = directory / KARTE_FILENAME_FMT.format(issue=number)
    checked = resolve_within_repo(path, repo_root)
    if checked.parent != directory.resolve():
        raise KartePathError(f"カルテ置き場の直下ではない: {checked}")
    if checked.is_symlink():
        raise KartePathError(f"カルテ本体が symlink: {checked}")
    return checked


def active_path(repo_root, *, create_dir: bool = False) -> Path:
    """進行ポインタ ``tmp/_karte/active.json`` を返す。

    ``agent_id`` を結合キーにしない（方針転換で新しいコンテキストへ引き継ぐと途切れるため）。
    """
    directory = karte_dir(repo_root, create=create_dir)
    path = directory / ACTIVE_FILENAME
    if path.is_symlink():
        raise KartePathError(f"進行ポインタが symlink: {path}")
    return path


def read_text(path: Path) -> str:
    if path.is_symlink():
        raise KartePathError(f"読み込み直前の再検査で symlink を検知: {path}")
    if not path.is_file():
        raise KartePathError(f"通常ファイルではない: {path}")
    return path.read_text(encoding="utf-8")


def write_text_atomic(path: Path, text: str) -> None:
    """同一ディレクトリ内の一時ファイル経由で原子的に置き換える。

    書込直前に symlink 化していないかを再検査する（TOCTOU 対策・``dsv2/cleantmp.py`` の
    ``_reverify_before_delete`` と同じ defense-in-depth）。
    """
    if path.is_symlink():
        raise KartePathError(f"書込直前の再検査で symlink を検知（TOCTOU 疑い）: {path}")
    if path.exists() and not path.is_file():
        raise KartePathError(f"書込先が通常ファイルではない: {path}")
    tmp_path = path.with_name(path.name + ".tmp")
    if tmp_path.is_symlink():
        raise KartePathError(f"一時ファイル名が symlink として存在する: {tmp_path}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def append_text(path: Path, text: str) -> None:
    """既存ブロックを書き換えずに末尾へ追記する（Attempt/Result は追記のみ）。"""
    if path.is_symlink():
        raise KartePathError(f"追記直前の再検査で symlink を検知（TOCTOU 疑い）: {path}")
    if not path.is_file():
        raise KartePathError(f"追記先が通常ファイルではない: {path}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
