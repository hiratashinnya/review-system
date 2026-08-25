"""`.ai/guidance/` から PF 常駐入口を生成し、drift を検査する。

Claude は公式 ``@`` import で共通原稿を直接読むため、この生成対象には含めない。
pre-commit 向け検査は working tree を参照せず staged index だけを読み、自動生成も
自動 stage も行わない。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SOURCE = ".ai/guidance/common.md"
PRINCIPLES_SOURCE = ".ai/skills/spec-principles/SKILL.md"
TARGETS: Mapping[str, str] = {
    "AGENTS.md": ".ai/guidance/platforms/codex.md",
    ".github/copilot-instructions.md": ".ai/guidance/platforms/copilot.md",
}
PRINCIPLES_MARKER_RE = re.compile(
    rb"<!--\s*principles-source:\s*\.ai/skills/spec-principles/SKILL\.md;\s*"
    rb"sha256:\s*([0-9a-f]{64})\s*-->"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _body(data: bytes) -> bytes:
    """原稿間の結合を決定的にするため、末尾改行をちょうど1つにする。"""

    return data.rstrip(b"\n") + b"\n"


def _principles_marker(principles: bytes) -> bytes:
    return (
        f"<!-- principles-source: {PRINCIPLES_SOURCE}; "
        f"sha256: {_sha256(principles)} -->"
    ).encode("utf-8")


def _source_dependency_errors(*, load: Callable[[str], bytes]) -> list[str]:
    """共通 guidance の意味保存写しが spec-principles 正本に追従しているか返す。"""

    try:
        common = load(COMMON_SOURCE)
        principles = load(PRINCIPLES_SOURCE)
    except (OSError, RuntimeError) as exc:
        return [f"原稿依存を読めません: {exc}"]

    expected = _sha256(principles)
    match = PRINCIPLES_MARKER_RE.search(common)
    if match is None:
        return [
            f"{COMMON_SOURCE} に {PRINCIPLES_SOURCE} の principles-source marker がありません"
        ]
    recorded = match.group(1).decode("ascii")
    if recorded != expected:
        return [
            f"{COMMON_SOURCE} の principles-source hash が {PRINCIPLES_SOURCE} と一致しません: "
            f"記録 {recorded} / 現在 {expected}"
        ]
    return []


def rendered_bytes(
    target: str,
    *,
    load: Callable[[str], bytes],
) -> bytes:
    """``target`` の完全な生成結果を返す。I/O は ``load`` へ分離する。"""

    try:
        platform_source = TARGETS[target]
    except KeyError as exc:  # pragma: no cover - 呼び出し側のプログラミングエラー
        raise ValueError(f"生成対象ではありません: {target}") from exc
    common = load(COMMON_SOURCE)
    principles = load(PRINCIPLES_SOURCE)
    platform = load(platform_source)
    marker = (
        "<!-- generated-by: python3 -m guidance_sync render; edit-source-only -->\n"
        f"<!-- common-source: {COMMON_SOURCE}; sha256: {_sha256(common)} -->\n"
        f"{_principles_marker(principles).decode('utf-8')}\n"
        f"<!-- platform-source: {platform_source}; sha256: {_sha256(platform)} -->\n\n"
    ).encode("utf-8")
    return marker + _body(common) + b"\n" + _body(platform)


def _filesystem_loader(root: Path) -> Callable[[str], bytes]:
    return lambda relative: (root / relative).read_bytes()


def render(root: Path = REPO_ROOT) -> list[str]:
    """生成物を明示的に更新し、変更した相対パスを返す。"""

    load = _filesystem_loader(root)
    changed: list[str] = []
    for target in TARGETS:
        expected = rendered_bytes(target, load=load)
        path = root / target
        current = path.read_bytes() if path.is_file() else None
        if current != expected:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
            changed.append(target)
    return changed


def check(root: Path = REPO_ROOT) -> list[str]:
    """working tree の生成物 drift を返す。空なら整合している。"""

    load = _filesystem_loader(root)
    errors = _source_dependency_errors(load=load)
    for target in TARGETS:
        path = root / target
        if not path.is_file():
            errors.append(f"生成物がありません: {target}")
            continue
        if path.read_bytes() != rendered_bytes(target, load=load):
            errors.append(
                f"生成物が原稿と一致しません: {target} "
                "（python3 -m guidance_sync render を実行してください）"
            )
    return errors


def _run_git(
    argv: Sequence[str],
    *,
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess],
    text: bool,
) -> subprocess.CompletedProcess:
    return runner(
        list(argv),
        cwd=str(root),
        capture_output=True,
        text=text,
        shell=False,
        check=False,
    )


def _staged_paths(
    root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess],
) -> set[str]:
    completed = _run_git(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD", "-z"],
        root=root,
        runner=runner,
        text=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"staged path の取得に失敗しました: {detail}")
    return {
        item.decode("utf-8")
        for item in (completed.stdout or b"").split(b"\0")
        if item
    }


def _index_loader(
    root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess],
) -> Callable[[str], bytes]:
    def load(relative: str) -> bytes:
        completed = _run_git(
            ["git", "show", f":{relative}"],
            root=root,
            runner=runner,
            text=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"index の {relative} を読めません: {detail}")
        return completed.stdout or b""

    return load


def staged_check(
    root: Path = REPO_ROOT,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[str]:
    """staged index 内の原稿と生成物だけを比較する。

    原稿が stage された場合は依存する生成物も stage 済みであることを要求する。
    生成物だけが stage された場合も index 上の原稿との一致を検査する。
    """

    try:
        staged = _staged_paths(root, runner=runner)
    except RuntimeError as exc:
        return [str(exc)]

    required_targets: set[str] = set()
    require_common = PRINCIPLES_SOURCE in staged
    if COMMON_SOURCE in staged:
        required_targets.update(TARGETS)
    if require_common:
        required_targets.update(TARGETS)
    for target, platform_source in TARGETS.items():
        if platform_source in staged or target in staged:
            required_targets.add(target)
    if not required_targets:
        return []

    errors: list[str] = []
    load = _index_loader(root, runner=runner)
    if require_common and COMMON_SOURCE not in staged:
        errors.append(
            f"{PRINCIPLES_SOURCE} の変更に対応する意味保存写しが stage されていません: "
            f"{COMMON_SOURCE}"
        )
    errors.extend(_source_dependency_errors(load=load))
    for target in sorted(required_targets):
        if target not in staged:
            errors.append(
                f"原稿の変更に対応する生成物が stage されていません: {target}"
            )
            continue
        try:
            actual = load(target)
            expected = rendered_bytes(target, load=load)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        if actual != expected:
            errors.append(
                f"staged index の生成物が staged 原稿と一致しません: {target} "
                "（render 後に生成物を明示的に stage してください）"
            )
    return errors


def _print_errors(errors: Iterable[str]) -> None:
    for error in errors:
        print(f"guidance-sync: ERROR: {error}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("render", "check", "staged-check"))
    args = parser.parse_args(argv)

    if args.command == "render":
        changed = render()
        if changed:
            for target in changed:
                print(f"guidance-sync: rendered {target}")
        else:
            print("guidance-sync: generated files are already current")
        return 0

    errors = check() if args.command == "check" else staged_check()
    if errors:
        _print_errors(errors)
        return 1
    print(f"guidance-sync: {args.command} OK")
    return 0
