"""欠陥混入率（派生 Issue/PR）の機械計測（Issue #488）。

指標の定義は :mod:`defect_metrics.model` にコード定数として固定してある。散文の
定義に依存させないこと自体が本パッケージの目的（Issue #368 の再現不能の再発防止）。

使い方は ``defect_metrics/README.md``、運用（外部 cron・publish）は
``docs/methods/defect-metrics-external-cron-ops.md`` を正本とする。
標準ライブラリのみに依存する。
"""

from .model import (  # noqa: F401
    BASELINE_DERIVED_PER_PR,
    BASELINE_WINDOW,
    DERIVATION_HORIZON,
    SCHEMA_VERSION,
    IssueRecord,
    PullRequestRecord,
    Window,
)

__all__ = [
    "BASELINE_DERIVED_PER_PR",
    "BASELINE_WINDOW",
    "DERIVATION_HORIZON",
    "SCHEMA_VERSION",
    "IssueRecord",
    "PullRequestRecord",
    "Window",
]
