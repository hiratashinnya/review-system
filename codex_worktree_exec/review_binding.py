"""承認済み binding から pr-reviewer の review envelope（期待値）を作る（Issue #375）。"""

import json
from pathlib import Path

from karte import review_envelope

from .errors import CodexExecError

PHASE_BY_INPUT = {"TestDesign": "test_design", "ChangePlan": "implementation"}


def review_envelope_of(cwd: Path, binding_file) -> dict:
    """binding の ``expected``（trusted dispatcher が用意）と検証済み ``artifact_digest`` から作る。

    run_id・target_key・snapshot_oid・issue は binding の期待値、input_digest はレビュー対象 artifact の
    検証済み digest、phase は入力 artifact の種別から決める。Codex の出力からは何も補わない。
    主文脈は同じ値を ``karte activate`` へ渡し、``ingest-reviewer`` が両者の一致を確認する。
    """
    try:
        if binding_file is None:
            raise ValueError("binding が無い")
        binding = json.loads((cwd / binding_file).read_text(encoding="utf-8"))
        expected = binding["expected"]
        return review_envelope.expected_of(
            issue=expected["issue"], phase=PHASE_BY_INPUT[expected["artifact_type"]],
            run_id=expected["run_id"], target_key=expected["target_key"],
            input_digest=binding["artifact_digest"], snapshot_oid=expected["snapshot_oid"],
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CodexExecError(
            "CODEX_REVIEW_INGEST_FAILED", f"review envelope を binding から作れない: {error}"
        ) from None
