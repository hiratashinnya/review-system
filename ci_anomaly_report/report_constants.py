"""CI anomaly report schema constants."""

SCHEMA_VERSION = 1
COLLECTOR_PATH = ".github/workflows/ci-anomaly-report.yml"
FAILURE_CONCLUSIONS = {
    "action_required",
    "failure",
    "stale",
    "startup_failure",
    "timed_out",
}
