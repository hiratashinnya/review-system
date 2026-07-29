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


def _tmp_root(repo_root: Path) -> Path:
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
    tmp_root = _tmp_root(repo_root)
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
    return CleanPlan(target=resolved, rel=str(Path(TMP_DIRNAME) / rel), files=files, dirs=dirs)


def apply_clean(plan: CleanPlan) -> None:
    """検査済み計画に従ってディレクトリを削除する（計画を経ずに呼ばない）。"""
    shutil.rmtree(plan.target)
