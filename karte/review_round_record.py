"""Review round receipt: report digest and accepted AC snapshot provenance."""
from dataclasses import dataclass
import re

from .ac_repository import normalize, normalize_host
from .errors import KarteUsageError
from .format_error import KarteFormatError
from .int_args import matched_int

TITLE_RE = re.compile(r"^Review Round ([1-9][0-9]*)\Z")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}\Z")
AC_KEYS = {"ac_source", "ac_host", "ac_repository"}


@dataclass(frozen=True)
class ReviewRound:
    number: int
    digest: str
    source: str = ""
    ac_source: str = ""
    ac_host: str = ""
    ac_repository: str = ""


def _check(record, issue):
    if (type(record.number) is not int or record.number < 1
            or not isinstance(record.digest, str) or DIGEST_RE.fullmatch(record.digest) is None):
        raise KarteFormatError("Review Round番号またはdigestが不正")
    expected = f"tmp/_karte/issue-{issue}-review-round-{record.number}.md"
    if not isinstance(record.source, str) or record.source not in ("", expected):
        raise KarteFormatError("Review Round原本参照が不正")
    if record.ac_source:
        prefix = f"tmp/_karte/issue-{issue}-ac-round-{record.number}-"
        if (not record.source or not isinstance(record.ac_source, str)
                or re.fullmatch(re.escape(prefix) + r"[0-9a-f]{64}\.md", record.ac_source) is None):
            raise KarteFormatError("受理AC原本参照が不正")
    elif record.ac_host or record.ac_repository:
        raise KarteFormatError("受理AC原本が無いのにoriginが存在する")
    if bool(record.ac_host) != bool(record.ac_repository):
        raise KarteFormatError("受理AC originのhost/repositoryが不完全")
    if record.ac_host:
        try:
            if (normalize_host(record.ac_host) != record.ac_host
                    or normalize(record.ac_repository) != record.ac_repository):
                raise KarteFormatError("受理AC originの表記が不正")
        except KarteUsageError as exc:
            raise KarteFormatError("受理AC originが不正") from exc


def from_block(block, issue: int) -> ReviewRound:
    matched = TITLE_RE.fullmatch(block.title)
    if matched is None:
        raise KarteFormatError(f"{block.lineno} 行目: Review Round見出しが不正")
    keys = set(block.fields)
    if keys not in ({"digest"}, {"digest", "source"}, {"digest", "source", "ac_source"},
                    {"digest", "source", "ac_source", "ac_host", "ac_repository"}):
        raise KarteFormatError(f"{block.lineno} 行目: Review Roundの未知キーまたはAC束縛の欠落")
    number = matched_int(matched.group(1), KarteFormatError, "Review Round 番号")
    rec = ReviewRound(number, block.fields["digest"], block.fields.get("source", ""),
                      *(block.fields.get(key, "") for key in ("ac_source", "ac_host", "ac_repository")))
    _check(rec, issue)
    if "ac_source" in keys and not rec.ac_source:
        raise KarteFormatError("Review RoundのAC原本参照が空")
    if "ac_host" in keys and not (rec.ac_host and rec.ac_repository):
        raise KarteFormatError("Review Roundのorigin束縛が空")
    return rec


def render_round(record: ReviewRound) -> str:
    if record.source:
        match = re.fullmatch(r"tmp/_karte/issue-([1-9][0-9]*)-review-round-"
                             + str(record.number) + r"\.md", record.source)
        if match is None:
            raise KarteFormatError("Review Round原本参照が不正")
        issue = match.group(1)
    else:
        issue = 1
    _check(record, issue)
    lines = [f"### Review Round {record.number}", f"digest: {record.digest}"]
    if record.source:
        lines.append(f"source: {record.source}")
    if record.ac_source:
        lines.append(f"ac_source: {record.ac_source}")
    if record.ac_host:
        lines.extend((f"ac_host: {record.ac_host}", f"ac_repository: {record.ac_repository}"))
    return "\n".join(lines) + "\n"
