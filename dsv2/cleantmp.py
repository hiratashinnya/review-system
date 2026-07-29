"""tmp 著作ミラーの安全削除（``dsv2 clean-tmp``）。

reconciliation（書込エージェント）の Step 3-3「本コーパスへの書込完了後に
``tmp/<sprint>/<parent-id>/`` を削除する」を、**規律（プローズ）ではなく機械的なガード**として
実行するための決定論ツール。Write/Edit ではディレクトリを消せず、素の ``rm -rf`` を許すと
パス解決を誤ったときに ``tmp/_handoff/`` やリポジトリ本体まで消しうるため、
「消してよい形のパスか」を検査してからしか削除しない専用コマンドを用意する（fail-close）。

ガード（すべて満たさなければ削除しない）:
  1. 実体解決（symlink 追跡）後のパスが ``<repo-root>/tmp/`` 配下にある。
  2. ``tmp/`` からの相対が **ちょうど2階層**（``<sprint>/<parent-id>``）である。
     ``tmp`` 自身・``tmp/<sprint>`` 単独・``tmp/<sprint>/<parent-id>/nodes`` は拒否する。
  3. 相対パスの構成要素に ``_handoff`` を含まない（ハンドオフ置き場は掃除対象外＝
     CLAUDE.md「戻り値のハンドオフ規約」）。
  4. 引数そのものが symlink でない（実体を差し替えた削除誘導の防止）。
  5. 対象が実在するディレクトリである。

TOCTOU 対策（defense-in-depth）: 上記1〜5は ``plan_clean`` 実行時点のスナップショットに
過ぎず、``plan_clean`` から ``apply_clean`` までの間に symlink 差し替え等でパスの実体が
変わる余地がある（plan-time check と削除実行の間の window）。そのため ``apply_clean`` は
``shutil.rmtree`` 直前に同じガードを対象パス・``tmp_root`` の双方について再実行し、
plan 作成後に実体が変化していれば削除せず :class:`CleanTmpError` を送出する
（``_reverify_before_delete``）。

依存仕様:
  * DD-22（著作→検証→書込の3段分離・writer だけが破壊的操作を行う）
  * CLAUDE.md「戻り値のハンドオフ規約」（``tmp/_handoff/`` は tmp 掃除の対象外）
  * ``.claude/agents/reconciliation.md`` Step 3-3（掃除対象＝``tmp/<sprint>/<parent-id>/``）
  ※ 上記2つは out-of-graph（版なし）のため補助ナビ。掃除対象レイアウトの一次アンカーは
    著作エージェント共通契約（``.claude/agents/doc-system-v2-authoring.md``）の tmp ミラー規定。
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

TMP_DIRNAME = "tmp"
HANDOFF_DIRNAME = "_handoff"
TARGET_DEPTH = 2  # tmp/<sprint>/<parent-id>


class CleanTmpError(Exception):
    """ガード違反（削除してはならない形のパス）。"""


class CleanTmpNotFound(CleanTmpError):
    """対象が実在しない（未削除・掃除不要のケースを含む）。"""


@dataclass(frozen=True)
class CleanPlan:
    """削除計画（dry-run 表示と apply の入力）。"""

    target: Path       # 実体解決済みの削除対象（tmp/<sprint>/<parent-id>）
    rel: str           # repo-root からの相対表記（表示用）
    files: int         # 配下のファイル数
    dirs: int          # 配下のディレクトリ数（target 自身を含まない）
    repo_root: Path    # 実体解決済みの repo-root（apply 直前の TOCTOU 再検査に使う）


def _tmp_root(repo_root: str | Path) -> Path:
    root = Path(repo_root).resolve()
    tmp = root / TMP_DIRNAME
    if not tmp.is_dir():
        raise CleanTmpError(f"tmp ディレクトリが無い: {tmp}")
    return tmp.resolve()


def plan_clean(target: str | Path, repo_root: str | Path) -> CleanPlan:
    """``target`` が掃除してよい tmp 著作ミラーかを検査し、削除計画を返す。

    ガードに1つでも掛かれば :class:`CleanTmpError`（実在しないだけなら
    :class:`CleanTmpNotFound`）を送出し、**削除は一切行わない**（fail-close）。
    """
    resolved_repo_root = Path(repo_root).resolve()
    tmp_root = _tmp_root(resolved_repo_root)
    given = Path(target)

    if given.is_symlink():
        raise CleanTmpError(f"symlink は削除対象にしない: {given}")

    resolved = given.resolve()
    try:
        rel = resolved.relative_to(tmp_root)
    except ValueError:
        raise CleanTmpError(
            f"tmp/ の外を指している: {resolved}（許可範囲は {tmp_root}/<sprint>/<parent-id>）"
        ) from None

    parts = rel.parts
    if HANDOFF_DIRNAME in parts:
        raise CleanTmpError(
            f"ハンドオフ置き場は掃除対象外: {resolved}"
            f"（'{HANDOFF_DIRNAME}' を含むパスは削除しない）"
        )
    if len(parts) != TARGET_DEPTH:
        raise CleanTmpError(
            f"削除対象は tmp/<sprint>/<parent-id> のちょうど {TARGET_DEPTH} 階層のみ: "
            f"{resolved}（相対 {'/'.join(parts) or '.'} ＝ {len(parts)} 階層）"
        )
    if not resolved.exists():
        raise CleanTmpNotFound(f"対象が存在しない（掃除不要）: {resolved}")
    if not resolved.is_dir():
        raise CleanTmpError(f"ディレクトリではない: {resolved}")

    files = sum(1 for p in resolved.rglob("*") if p.is_file() or p.is_symlink())
    dirs = sum(1 for p in resolved.rglob("*") if p.is_dir() and not p.is_symlink())
    return CleanPlan(
        target=resolved,
        rel=str(Path(TMP_DIRNAME) / rel),
        files=files,
        dirs=dirs,
        repo_root=resolved_repo_root,
    )


def _reverify_before_delete(plan: CleanPlan) -> None:
    """``shutil.rmtree`` 直前の再検査（TOCTOU 対策・defense-in-depth）。

    ``plan_clean`` から ``apply_clean`` までの間に symlink 差し替え等でパスの実体が
    変わっていないかを、plan-time と同じガード（tmp/ 配下・階層・非 handoff・非 symlink・
    ディレクトリ実在）で削除実行の直前に再確認する。1つでも崩れていれば削除せず
    :class:`CleanTmpError` を送出する（fail-close）。
    """
    target = plan.target

    # 1. 対象そのものが symlink に差し替わっていないか（symlink 追跡前に検知する必要が
    #    あるため、resolve() より先に lstat 相当の is_symlink() で確認する）。
    if target.is_symlink():
        raise CleanTmpError(f"削除直前の再検査で symlink 化を検知（TOCTOU 疑い）: {target}")

    # 2. tmp_root 自体を作り直す（tmp_root 側が symlink 差し替えされていた場合も検知する）。
    tmp_root = _tmp_root(plan.repo_root)

    # 3. plan 作成時点の実体解決済みパスと、いま再解決した結果が一致するか。
    #    途中の構成要素（tmp/<sprint> 等）が symlink に差し替えられていれば、ここで
    #    再解決結果が変化して検知できる。
    resolved = target.resolve()
    if resolved != target:
        raise CleanTmpError(
            f"削除直前の再検査でパスの実体が変化した（TOCTOU 疑い）: {target} → {resolved}"
        )

    # 4. tmp/ 配下・階層・非 handoff・ディレクトリ実在を plan-time と同じ基準で再確認する。
    try:
        rel = resolved.relative_to(tmp_root)
    except ValueError:
        raise CleanTmpError(
            f"削除直前の再検査で tmp/ の外を指すようになった: {resolved}"
        ) from None
    parts = rel.parts
    if HANDOFF_DIRNAME in parts:
        raise CleanTmpError(f"削除直前の再検査でハンドオフ配下に変化した: {resolved}")
    if len(parts) != TARGET_DEPTH:
        raise CleanTmpError(
            f"削除直前の再検査で階層が変化した: {resolved}（{len(parts)} 階層）"
        )
    if not resolved.is_dir():
        raise CleanTmpError(f"削除直前の再検査でディレクトリでなくなっている: {resolved}")


def apply_clean(plan: CleanPlan) -> None:
    """検査済み計画に従ってディレクトリを削除する（計画を経ずに呼ばない）。

    ``shutil.rmtree`` 直前に :func:`_reverify_before_delete` で再検査する
    （plan 作成〜適用の間の TOCTOU window に対する defense-in-depth）。
    """
    _reverify_before_delete(plan)
    shutil.rmtree(plan.target)
