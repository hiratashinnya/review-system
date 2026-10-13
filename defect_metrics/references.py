"""Parse issue-body references to pull requests."""

from __future__ import annotations
import re


ISSUE_REFERENCE_RE = re.compile(r"(?<![0-9A-Za-z_/#&])#(\d{1,7})(?![0-9A-Za-z_])")


QUALIFIED_REFERENCE_RE = re.compile(
    r"(?<![0-9A-Za-z_/#&])([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)#(\d{1,7})(?![0-9A-Za-z_])"
)


URL_REFERENCE_RE = re.compile(
    r"https?://(?:www\.)?github\.com/"
    r"([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)/"
    r"(?:pull|issues)/(\d{1,7})(?!\d)",
    re.IGNORECASE,
)


def normalise_repository(repository: str) -> str:
    """``OWNER/REPO`` を小文字化して返す（GitHub の owner/repo は大小を区別しない）。

    形式が読めないときは ``ValueError`` で止める。黙って「リポジトリ修飾付きの参照なし」に
    倒すと、主指標が静かに ``#N`` 記法だけの旧定義へ戻り、しかもそれが観測できない
    （Issue #493 が問題にした失敗そのものの再現）。この検証は
    :func:`defect_metrics.cli.main` が**窓内 Issue の有無に依らず入口で無条件に**呼ぶ
    ——``referenced_numbers`` からの呼び出しだけに頼ると、窓内に作成 Issue が1件も無い入力で
    不正な ``--repository`` が素通りし、宣言している fail-close がデータ依存になる。

    **リポジトリ改名時は旧 slug の参照が落ちる（既知の前提・オーナー判断 2026-09-08）。**
    照合は ``--repository`` の slug との完全一致で行うため、リポジトリを改名すると、
    改名前に書かれた ``OWNER/OLD-REPO#N`` および ``https://github.com/OWNER/OLD-REPO/pull/N``
    は（GitHub 側が旧 URL を新 URL へ転送していても）参照として数えられなくなり、
    派生 Issue 数だけが静かに下がる。基線窓にはこの2記法由来の派生が0件のため
    ``verify-baseline`` でも検知できない。**API で正準 slug を引いて改名に追随する案は
    本 PR の範囲外とする**——ネットワーク照会は「``--issues-json`` / ``--pulls-json`` だけで
    決定的に再現できる」という本ツールの性質（``README.md`` §4）を崩し、算出のたびに
    外部状態へ依存させることになるため、改名が実際に起きた時点で別途扱う。
    """
    text = (repository or "").strip().strip("/")
    parts = text.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"repository は OWNER/REPO 形式でなければならない: {repository!r}")
    return text.lower()


def _is_measured_repository(match: "re.Match[str]", owner_repo: str) -> bool:
    """``match`` の第1・第2捕獲群（owner / repo）が計測対象リポジトリを指すか。"""
    return f"{match.group(1)}/{match.group(2)}".lower() == owner_repo


def referenced_numbers(body: str | None, repository: str) -> set[int]:
    """本文が参照する PR/Issue 番号の集合。

    ``#N`` 記法・``OWNER/REPO#N`` 記法・``https://github.com/OWNER/REPO/pull/N`` 形式の
    完全 URL を**同一の参照**として扱い、**番号へ正規化した集合**で返す
    （Issue #493 オーナー確定・案 (a)）。集合なので、同じ PR を複数記法で書いた本文が
    二重計上されることはない。

    ``repository`` は計測対象の ``OWNER/REPO``。``OWNER/REPO#N`` と URL の2記法は
    これと一致するものだけを採る（他リポジトリを指すものは参照とみなさない
    ——他リポジトリの番号を自リポジトリの番号として誤ヒットさせないため）。
    """
    owner_repo = normalise_repository(repository)
    if not body:
        return set()
    numbers = {int(m.group(1)) for m in ISSUE_REFERENCE_RE.finditer(body)}
    for pattern in (QUALIFIED_REFERENCE_RE, URL_REFERENCE_RE):
        for match in pattern.finditer(body):
            if _is_measured_repository(match, owner_repo):
                numbers.add(int(match.group(3)))
    return numbers
