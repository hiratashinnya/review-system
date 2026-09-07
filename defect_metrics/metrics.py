"""窓ごとの指標算出（Issue #488）。

分母・分子の定義は :mod:`defect_metrics.model` の docstring に固定してある。
本モジュールはその定義を実行するだけで、閾値判定は :mod:`defect_metrics.threshold`
が担う（機械判定と運用ルールを混ぜない＝PR2）。

参照の記法を2つとも同一視する（Issue #493・オーナー確定＝案 (a)）
------------------------------------------------------------------
``#487`` と ``https://github.com/OWNER/REPO/pull/487`` は、人間にとって同じ意味であり
画面上の見え方も変わらない。**この記法差はツールからは見えない**ため、``#N`` だけを拾う実装は
主指標の正しさを「起票者が ``#N`` 記法で書き続ける」という**どこにも記録されていない前提**へ
乗せることになる。前提が崩れれば（起票者の習慣の変化・Issue テンプレートの導入・別ツールによる
自動起票など）主指標は静かに下振れし、しかもその下振れは「欠陥混入が減った」ように見える。
Issue #488 が定義をコードへ固定して塞いだのと同じ穴が、定義の所在から記法への依存へ移動して
残っていた形である。

そこで :data:`ISSUE_REFERENCE_RE`（``#N``）と :data:`URL_REFERENCE_RE`（完全 URL）の両方を拾い、
:func:`referenced_numbers` が**PR 番号へ正規化した集合**として返す。集合なので同一 PR を両記法で
書いた本文が二重計上されることはない。URL は**計測対象リポジトリのものだけ**を採る
——``#N`` 側が ``org/repo#N`` を除外している以上、URL 側だけ他リポジトリを拾うと他リポジトリの
PR 番号が自リポジトリの PR 番号として誤ヒットするため。この判定に使う ``OWNER/REPO`` を
:func:`is_derived` / :func:`compute_window_metrics` が引数で受け取る。

却下案（消さない）＝(b) 現状維持して前提を明記するだけ（記録するが検出しないので PR4 違反）、
(c) ``#N`` のみ／URL のみ／両方の内訳を ``report.json`` へ出す（内訳は指標の正しさには不要で
スキーマを広げるコストに見合わない・オーナー判断）。詳細は ``defect_metrics/README.md`` §2.1。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re

from .model import (
    DERIVATION_HORIZON,
    RATIO_DIGITS,
    IssueRecord,
    PullRequestRecord,
    Window,
)

# Issue/PR 本文中の `#N` 参照。
#   - 直前が英数・``_``・``/``・``#``・``&`` の場合は参照とみなさない
#     （``abc#12``／``org/repo#12`` のような他リポジトリ参照、``##`` 見出し、
#     ``&#187;`` のような HTML entity を除外する）。
#   - 直後が英数・``_`` の場合も除外する（``#1abc`` は Issue 番号ではない）。
# 本文以外（タイトル・コメント）は見ない。Issue #488 が「本文が参照する `#N`」と
# 定義しているため、参照元を本文に固定する。
ISSUE_REFERENCE_RE = re.compile(r"(?<![0-9A-Za-z_/#&])#(\d{1,7})(?![0-9A-Za-z_])")

# 同じ参照の完全 URL 形式（Issue #493 で採用した案 (a)）。
#   ``https://github.com/OWNER/REPO/pull/487`` は人間にとって ``#487`` と同じ意味であり、
#   画面上の見え方も変わらない。記法の違いはツールからは見えないので、``#N`` だけを拾うと
#   指標の正しさが「起票者が ``#N`` で書き続ける」という**どこにも記録されていない前提**に
#   乗る（Issue #493「目的・背景」）。両記法を同じ参照として正規化してその前提を外す。
#   - ``owner``/``repo`` を捕獲するのは**計測対象リポジトリのものだけを採る**ため。
#     ``#N`` 側が ``org/repo#12`` を除外している以上、URL 側だけ他リポジトリを拾うと
#     他リポジトリの PR 番号が自リポジトリの PR 番号として誤ヒットする。
#   - ``/issues/N`` も受ける。``#N`` は Issue と PR を区別しない記法であり、GitHub は
#     PR への ``/issues/N`` URL を ``/pull/N`` へ転送する。派生判定は merged PR の辞書を
#     引くだけなので、PR でない番号は :func:`is_derived` 側で自然に落ちる。
#   - 直後が数字なら除外する（番号の途中で切らない）。``/pull/487/files`` や
#     ``/pull/487#issuecomment-1`` のような続きは番号の後ろに来るので影響しない。
URL_REFERENCE_RE = re.compile(
    r"https?://(?:www\.)?github\.com/"
    r"([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)/"
    r"(?:pull|issues)/(\d{1,7})(?!\d)",
    re.IGNORECASE,
)


def normalise_repository(repository: str) -> str:
    """``OWNER/REPO`` を小文字化して返す（GitHub の owner/repo は大小を区別しない）。

    形式が読めないときは ``ValueError`` で止める。黙って「URL 参照なし」に倒すと、
    主指標が静かに ``#N`` 記法だけの旧定義へ戻り、しかもそれが観測できない
    （Issue #493 が問題にした失敗そのものの再現）。
    """
    text = (repository or "").strip().strip("/")
    parts = text.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"repository は OWNER/REPO 形式でなければならない: {repository!r}")
    return text.lower()


def referenced_numbers(body: str | None, repository: str) -> set[int]:
    """本文が参照する PR/Issue 番号の集合。

    ``#N`` 記法と ``https://github.com/OWNER/REPO/pull/N`` 形式の完全 URL を**同一の参照**
    として扱い、**番号へ正規化した集合**で返す（Issue #493 オーナー確定・案 (a)）。集合なので
    同じ PR を両記法で書いた本文が二重計上されることはない。

    ``repository`` は計測対象の ``OWNER/REPO``。URL 形式はこれと一致するものだけを採る
    （他リポジトリの URL は ``org/repo#12`` と同じく参照とみなさない）。
    """
    owner_repo = normalise_repository(repository)
    if not body:
        return set()
    numbers = {int(m.group(1)) for m in ISSUE_REFERENCE_RE.finditer(body)}
    for match in URL_REFERENCE_RE.finditer(body):
        if f"{match.group(1)}/{match.group(2)}".lower() == owner_repo:
            numbers.add(int(match.group(3)))
    return numbers


def _ratio(numerator: int, denominator: int) -> float | None:
    """分母0のとき ``None``（0除算を 0 や inf に潰さず「算出不能」として持ち上げる）。"""
    if denominator == 0:
        return None
    return numerator / denominator


def _rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, RATIO_DIGITS)


@dataclass(frozen=True)
class WindowMetrics:
    """1つの窓に対する指標一式。比率は丸め前の厳密値で保持する。"""

    window: Window
    merged_prs: int
    created_issues: int
    derived_issues: int
    closed_issues: int
    derived_issue_numbers: tuple[int, ...] = ()

    @property
    def issues_per_pr(self) -> float | None:
        """副指標＝窓内作成の全 Issue / 窓内 merged PR。"""
        return _ratio(self.created_issues, self.merged_prs)

    @property
    def derived_per_pr(self) -> float | None:
        """主指標＝窓内作成の派生 Issue / 窓内 merged PR。"""
        return _ratio(self.derived_issues, self.merged_prs)

    @property
    def derived_per_pr_exact(self) -> Fraction | None:
        """主指標の厳密値（有理数）。

        float だと ``0.2 * 1.5 == 0.30000000000000004`` のような表現誤差で「ちょうど
        1.5 倍」の境界判定が裏返るため、直近4週との比較（:mod:`defect_metrics.threshold`）は
        この有理数で行う。
        """
        if self.merged_prs == 0:
            return None
        return Fraction(self.derived_issues, self.merged_prs)

    @property
    def derived_per_pr_rounded(self) -> float | None:
        """主指標を表示精度（小数2桁）へ丸めた値。

        基線 0.68 との比較にはこちらを使う——基線定数自体が実測 15/22 = 0.6818… を
        2桁で記録した値であり、厳密値どうしで比べると**基線の窓そのものが「基線超過」に
        なってしまう**（0.6818… > 0.68）。同じ精度で比較して初めて「基線と同じなら異常でない」
        が成立する。
        """
        return _rounded(self.derived_per_pr)

    @property
    def open_issue_net_change(self) -> int:
        """open Issue 純増（窓内作成 − 窓内 close）。"""
        return self.created_issues - self.closed_issues

    def as_dict(self) -> dict[str, object]:
        return {
            "window": self.window.as_dict(),
            "denominator": {"merged_prs": self.merged_prs},
            "primary": {
                "definition": (
                    "窓内に作成された Issue のうち、本文が参照する PR "
                    "（#N 記法と同一リポジトリの完全 URL を同一の参照として数える）に "
                    "「起票時刻から遡って72時間以内に merge された PR」を"
                    "1つ以上含むもの（派生 Issue）"
                ),
                "derived_issues": self.derived_issues,
                "derived_per_pr": _rounded(self.derived_per_pr),
                "derived_issue_numbers": list(self.derived_issue_numbers),
            },
            "secondary": {
                "definition": "窓内に作成された全 Issue 数（起票粒度の変化に汚染される副指標）",
                "created_issues": self.created_issues,
                "issues_per_pr": _rounded(self.issues_per_pr),
            },
            "open_issue_net_change": {
                "created": self.created_issues,
                "closed": self.closed_issues,
                "net": self.open_issue_net_change,
            },
        }


def is_derived(
    issue: IssueRecord,
    merged_by_number: dict[int, PullRequestRecord],
    repository: str,
) -> bool:
    """``issue`` が派生 Issue か（:mod:`defect_metrics.model` の定義どおり）。

    参照先 PR は**窓の内外を問わない**。窓の先頭直前に merge された PR に由来する
    起票を落とさないため（分子は「窓内に作成された Issue」で絞り、参照先の merge
    時刻は起票時刻からの相対距離だけで判定する）。

    ``repository`` は :func:`referenced_numbers` の URL 形式判定に使う計測対象
    ``OWNER/REPO``（Issue #493）。
    """
    for number in referenced_numbers(issue.body, repository):
        pull = merged_by_number.get(number)
        if pull is None:
            continue
        delta = issue.created_at - pull.merged_at
        # merge が起票より後の PR（後から採番された PR への言及）は原因になりえない。
        if delta.total_seconds() < 0:
            continue
        if delta <= DERIVATION_HORIZON:
            return True
    return False


def compute_window_metrics(
    window: Window,
    issues: list[IssueRecord],
    pulls: list[PullRequestRecord],
    repository: str,
) -> WindowMetrics:
    """``window`` に対する指標を算出する。

    ``issues`` / ``pulls`` は窓で絞り込む前の全件を渡す（絞り込みは本関数が行う）。
    ``repository`` は計測対象の ``OWNER/REPO``（URL 形式の参照を自リポジトリのものだけに
    絞るために使う・Issue #493）。
    """
    merged_by_number = {p.number: p for p in pulls}
    merged_prs = sum(1 for p in pulls if window.contains(p.merged_at))
    created = [i for i in issues if window.contains(i.created_at)]
    closed_issues = sum(1 for i in issues if window.contains(i.closed_at))
    derived = [i for i in created if is_derived(i, merged_by_number, repository)]
    return WindowMetrics(
        window=window,
        merged_prs=merged_prs,
        created_issues=len(created),
        derived_issues=len(derived),
        closed_issues=closed_issues,
        derived_issue_numbers=tuple(sorted(i.number for i in derived)),
    )
