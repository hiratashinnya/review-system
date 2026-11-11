"""review handoff の共通 envelope（#371）。実体は標準ライブラリだけで動く :mod:`karte.review_envelope`。"""
from karte.review_envelope import (  # noqa: F401
    ARTIFACT_TYPE, BOUND, PHASES, PRODUCER, SCHEMA, SCHEMA_VERSION,
    expected_of, normalize, validate_review_envelope,
)
