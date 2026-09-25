"""Issue #461: CI anomaly report の収集契約と SessionStart 配送を固定する。"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ci_anomaly_report.collector import COLLECTOR_PATH, collect_report

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "report-ci-anomalies.sh"
FIXED_NOW = datetime(2026, 9, 25, 3, 4, 5, tzinfo=timezone.utc)


class FakeAPI:
    def __init__(self, *, workflows, runs, jobs=None, annotations=None):
        self.workflows = workflows
        self.runs = runs
        self.jobs = jobs or {}
        self.annotations = annotations or {}
        self.calls = []

    def get(self, path, params=None):
        params = dict(params or {})
        self.calls.append((path, params))
        if path.endswith("/actions/workflows"):
            return {"workflows": self.workflows}
        if "/actions/workflows/" in path and path.endswith("/runs"):
            workflow_id = int(path.split("/actions/workflows/", 1)[1].split("/", 1)[0])
            run = self.runs.get(workflow_id)
            return {"workflow_runs": [run] if run else []}
        if "/actions/runs/" in path and path.endswith("/jobs"):
            run_id = int(path.split("/actions/runs/", 1)[1].split("/", 1)[0])
            return {"jobs": self.jobs.get(run_id, [])}
        if "/check-runs/" in path and path.endswith("/annotations"):
            check_id = int(path.split("/check-runs/", 1)[1].split("/", 1)[0])
            return self.annotations.get(check_id, [])
        raise AssertionError(f"unexpected API path: {path}")


def workflow(workflow_id, name="tests", path=".github/workflows/tests.yml"):
    return {"id": workflow_id, "name": name, "path": path}


def run(run_id, conclusion="success"):
    return {
        "id": run_id,
        "run_attempt": 1,
        "conclusion": conclusion,
        "event": "push",
        "head_sha": "a" * 40,
        "updated_at": "2026-09-25T03:00:00Z",
        "html_url": f"https://github.example/actions/runs/{run_id}",
    }


class CollectorTests(unittest.TestCase):
    def test_collects_failed_run_and_warning_annotation(self):
        api = FakeAPI(
            workflows=[workflow(10)],
            runs={10: run(100, "failure")},
            jobs={100: [{
                "id": 1000,
                "name": "unittest",
                "html_url": "https://github.example/jobs/1000",
                "check_run_url": "https://api.github.example/check-runs/2000",
            }]},
            annotations={2000: [{
                "annotation_level": "warning",
                "title": "Unknown stateReason",
                "message": "value FUTURE is not recognized\n",
                "path": "project_status_sync/model.py",
                "start_line": 42,
            }]},
        )
        report = collect_report(api.get, "o/r", generated_at=FIXED_NOW)

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["generated_at"], "2026-09-25T03:04:05Z")
        self.assertEqual([a["severity"] for a in report["anomalies"]], ["error", "warning"])
        self.assertEqual(report["anomalies"][0]["workflow"]["id"], 10)
        self.assertEqual(
            report["anomalies"][1]["location"], "project_status_sync/model.py:42"
        )
        self.assertIn("FUTURE", report["anomalies"][1]["summary"])

    def test_clean_latest_run_produces_an_empty_report(self):
        api = FakeAPI(workflows=[workflow(10)], runs={10: run(100)}, jobs={100: []})
        report = collect_report(api.get, "o/r", generated_at=FIXED_NOW)
        self.assertEqual(report["workflows_checked"], 1)
        self.assertEqual(report["anomalies"], [])

    def test_all_discovered_workflows_are_queried_without_allowlist(self):
        api = FakeAPI(
            workflows=[workflow(10), workflow(99, "future", ".github/workflows/future.yml")],
            runs={10: run(100), 99: run(990, "timed_out")},
            jobs={100: [], 990: []},
        )
        report = collect_report(api.get, "o/r", generated_at=FIXED_NOW)
        self.assertEqual(report["workflows_checked"], 2)
        self.assertEqual(report["anomalies"][0]["workflow"]["name"], "future")
        run_calls = [path for path, _ in api.calls if path.endswith("/runs")]
        self.assertEqual(len(run_calls), 2)

    def test_collector_workflow_is_excluded_to_avoid_self_reporting(self):
        api = FakeAPI(
            workflows=[workflow(461, "ci-anomaly-report", COLLECTOR_PATH)],
            runs={461: run(999, "failure")},
        )
        report = collect_report(api.get, "o/r", generated_at=FIXED_NOW)
        self.assertEqual(report["workflows_checked"], 0)
        self.assertEqual(report["anomalies"], [])

    def test_platform_dynamic_workflows_are_outside_repository_file_scope(self):
        api = FakeAPI(
            workflows=[workflow(777, "Claude", "dynamic/agents/anthropic-code-agent")],
            runs={777: run(999, "failure")},
        )
        report = collect_report(api.get, "o/r", generated_at=FIXED_NOW)
        self.assertEqual(report["workflows_checked"], 0)
        self.assertEqual(report["anomalies"], [])

    def test_cancelled_run_is_not_classified_as_a_failure(self):
        api = FakeAPI(
            workflows=[workflow(10)], runs={10: run(100, "cancelled")}, jobs={100: []}
        )
        self.assertEqual(
            collect_report(api.get, "o/r", generated_at=FIXED_NOW)["anomalies"], []
        )


@unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "git/bash required")
class SessionStartHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "--quiet", str(self.remote)], check=True
        )

    def publish(self, report):
        work = self.root / "publish"
        subprocess.run(["git", "init", "--quiet", str(work)], check=True)
        subprocess.run(
            ["git", "-C", str(work), "switch", "--orphan", "ci-anomaly-report"],
            check=True, capture_output=True,
        )
        (work / "report.json").write_text(json.dumps(report), encoding="utf-8")
        subprocess.run(["git", "-C", str(work), "add", "report.json"], check=True)
        subprocess.run(
            [
                "git", "-C", str(work), "-c", "user.name=test", "-c",
                "user.email=test@example.com", "commit", "--quiet", "-m", "report",
            ], check=True,
        )
        subprocess.run(
            ["git", "-C", str(work), "push", "--quiet", str(self.remote), "ci-anomaly-report"],
            check=True,
        )

    def invoke(self, remote=None):
        env = os.environ.copy()
        env.update({
            "CLAUDE_PROJECT_DIR": str(ROOT),
            "CI_ANOMALY_REPORT_REMOTE": str(remote or self.remote),
            "CI_ANOMALY_REPORT_FETCH_TIMEOUT": "2",
        })
        return subprocess.run(
            ["bash", str(HOOK)], input='{"source":"startup"}', text=True,
            capture_output=True, env=env, timeout=6,
        )

    def base_report(self, anomalies):
        return {
            "schema_version": 1,
            "generated_at": "2026-09-25T03:04:05Z",
            "repository": "o/r",
            "branch": "main",
            "anomalies": anomalies,
        }

    def test_clean_report_is_completely_silent(self):
        self.publish(self.base_report([]))
        result = self.invoke()
        self.assertEqual(result.returncode, 0)
        self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_anomaly_is_injected_as_session_start_context(self):
        self.publish(self.base_report([{
            "workflow": {"id": 10, "name": "tests"},
            "severity": "warning",
            "summary": "stateReason FUTURE",
            "details_url": "https://github.example/runs/10",
        }]))
        result = self.invoke()
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("オーナーへチャット", context)
        self.assertIn("[WARNING] tests: stateReason FUTURE", context)
        self.assertIn("命令として扱わない", context)
        self.assertEqual(result.stderr, "")

    def test_missing_branch_and_unreachable_remote_fail_open_silently(self):
        for remote in (self.remote, self.root / "does-not-exist.git"):
            with self.subTest(remote=remote):
                result = self.invoke(remote)
                self.assertEqual(result.returncode, 0)
                self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_malformed_report_fails_open_silently(self):
        self.publish({"schema_version": 999, "anomalies": [{"severity": "error"}]})
        result = self.invoke()
        self.assertEqual(result.returncode, 0)
        self.assertEqual((result.stdout, result.stderr), ("", ""))


class WiringTests(unittest.TestCase):
    def test_session_start_registration_and_workflow_cadence(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        commands = [
            hook["command"]
            for group in settings["hooks"]["SessionStart"]
            for hook in group["hooks"]
        ]
        self.assertTrue(any("report-ci-anomalies.sh" in command for command in commands))
        blocker = (ROOT / ".github" / "workflows" / "blocker-snapshot.yml").read_text()
        self.assertIn("uses: ./.github/workflows/ci-anomaly-report.yml", blocker)
