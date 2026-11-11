"""カルテ書式の公開互換入口。

追記規律: Findings は ingest-review のみ更新し、Attempt/Result は追記のみ。
改ざん防止の機械的裏付けと既知の限界:
permissions.deny の Edit(/tmp/_karte/**) と worktree isolation の二層で保護する。
Bash 経由の変更は止まらず、sandbox ではない。
全文は .ai/rationale/karte-module-split.md の「K-02 実装で移設した docstring（#747）」。
"""

from __future__ import annotations

from .block_fields import (
    optional_enum as _optional_enum,
    require_enum as _require_enum,
    require_int_list as _require_int_list,
    require_nonempty as _require_nonempty,
)
from .block_parser import Block, parse_blocks
from .disposition import (
    DISPOSITION_ALL_KEYS,
    DISPOSITION_REQUIRED_KEYS,
    Disposition,
    parse_disposition,
)
from .field_validators import (
    validate_change_kind,
    validate_finding_ids,
    validate_slug,
    validate_targets,
)
from .finding_id import format_finding_id, parse_finding_id
from .format_error import KarteFormatError
from .harm_detail_lint import (
    DISPOSITION_TERMS,
    HARM_DETAIL_FORBIDDEN_TERMS,
    PROCESS_TERMS,
    check_harm_detail,
    find_harm_detail_terms,
    normalize_for_term_match,
)
from .int_args import matched_int, require_ascii_int
from .review_block import DISTINCT_FROM_KEY
from .review_finding import ReviewFinding
from .review_report import parse_review
from .value_codec import check_list, check_scalar, format_value, normalize_locus, parse_value
from .vocabulary import (
    ATTEMPT_TITLE_RE,
    CHANGE_KINDS,
    CLEARING_DISPOSITIONS,
    CLEARING_HARM,
    DEFAULT_SCOPE,
    DEFERRED_TO_RE,
    DISPOSITIONS,
    DOC_HEADER_RE,
    FINDING_ID_RE,
    FINDING_STATUSES,
    FORBIDDEN_LIST_ITEM_CHARS,
    FORBIDDEN_VALUE_CHARS,
    HARM_LEVELS,
    KEY_RE,
    NEW_FINDING_TITLES,
    OUTCOMES,
    RESULT_TITLE_RE,
    SCOPES,
    SECTION_ATTEMPTS,
    SECTION_FINDINGS,
    SEVERITIES,
    SLUG_RE,
    FORMAT_VERSION,
)

from .attempt_record import Attempt, Result
from .block_records import _attempt_from_block, _finding_from_block, _result_from_block
from .finding_record import Finding
from .finding_dedup import DUPLICATE_SIMILARITY_THRESHOLD, SHINGLE_SIZE, _jaccard, is_same_finding, normalize_text, shingles
from .karte_parse import parse
from .karte_record import Karte, new_karte
from .karte_render import _emit, dumps, render_attempt, render_finding, render_result
