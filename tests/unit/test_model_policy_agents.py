"""正本参照・停止 template・失敗後の runtime 無効化を検査する。"""

import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from model_policy import __main__ as cli
from model_policy.agents import invalidate_agents, prepare_agents
from model_policy.checks import check
from model_policy.policy import ROOT, load_policy
from model_policy.tracked_runtime import check_tracked_runtime


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.policy = load_policy()
        for directory in (".github/agents", ".agents/skills/bloom-model-tier",
                          ".github/skills/bloom-model-tier"):
            shutil.copytree(ROOT / directory, self.root / directory)
        (self.root / ".ai").mkdir()
        shutil.copy(ROOT / ".ai/Individually-managed-lists.md", self.root / ".ai")
        self.agent = self.root / ".github/agents/spec-author.agent.md"

    def test_reference_drift_and_quoted_reserved_yaml_keys_fail_closed(self):
        self.assertEqual(check(self.root, self.policy), [])
        original = self.agent.read_text()
        for extra in ('"disable-model-invocation": false', "'model': different-major",
                      "disable-model-invocation: false", "<<: *unsafe", "? model"):
            self.agent.write_text(original.replace("---\n", "---\n" + extra + "\n", 1))
            with self.subTest(extra=extra):
                self.assertTrue(check(self.root, self.policy))
        self.agent.write_text(original)
        reference = self.root / ".agents/skills/bloom-model-tier/SKILL.md"
        reference.write_text("正本参照を削除")
        self.assertTrue(check(self.root, self.policy))

    def test_prepare_preserves_template_and_is_idempotent_then_invalidates(self):
        original = self.agent.read_text()
        resolved = {tier: "synthetic-" + tier for tier in self.policy["platforms"]["copilot"]["tiers"]}
        outputs = prepare_agents(self.policy, resolved, self.root)
        runtime = self.agent.with_name("runtime-spec-author.agent.md")
        prepared = runtime.read_text()
        self.assertIn("model: " + resolved[self.policy["copilot_agents"]["spec-author"]], prepared)
        self.assertIn("disable-model-invocation: false", prepared)
        self.assertNotIn("停止状態の template", prepared)
        self.assertIn("解決済み runtime", prepared)
        self.assertIn("../../.ai/agents/spec-author.md", prepared)
        self.assertEqual(outputs["spec-author"]["agent"], "runtime-spec-author")
        prepare_agents(self.policy, resolved, self.root)
        self.assertEqual(runtime.read_text(), prepared)
        self.assertEqual(self.agent.read_text(), original)
        invalidate_agents(self.root)
        self.assertIn("disable-model-invocation: true", runtime.read_text())
        self.assertIn("user-invocable: false", runtime.read_text())
        self.assertIn("この runtime は停止済み", runtime.read_text())

    def test_preparation_failure_invalidates_previous_runtime(self):
        resolved = {tier: "synthetic-" + tier for tier in self.policy["platforms"]["copilot"]["tiers"]}
        prepare_agents(self.policy, resolved, self.root)
        with patch.object(cli, "invalidate_agents", side_effect=lambda: invalidate_agents(self.root)), \
                patch.object(cli, "load_policy", side_effect=ValueError("broken policy")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["prepare-copilot"]), 1)
        runtime = self.agent.with_name("runtime-spec-author.agent.md")
        self.assertIn("disable-model-invocation: true", runtime.read_text())
        self.assertIn("user-invocable: false", runtime.read_text())

    def test_invalid_arguments_stop_previous_runtime_before_parser_exits(self):
        resolved = {tier: "synthetic-" + tier for tier in self.policy["platforms"]["copilot"]["tiers"]}
        prepare_agents(self.policy, resolved, self.root)
        with patch.object(cli, "invalidate_agents", side_effect=lambda: invalidate_agents(self.root)), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(["prepare-copilot", "--surface", "web"])
        runtime = self.agent.with_name("runtime-spec-author.agent.md")
        self.assertIn("disable-model-invocation: true", runtime.read_text())

    def test_unwritable_runtime_returns_stop(self):
        with patch.object(cli, "invalidate_agents", side_effect=OSError("read-only")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["prepare-copilot"]), 1)
        self.assertIn("STOP", output.getvalue())

    def test_runtime_git_tracking_and_git_failure_stop(self):
        check_tracked_runtime(self.root, lambda *a, **k: SimpleNamespace(stdout=""))
        with self.assertRaises(ValueError):
            check_tracked_runtime(self.root, lambda *a, **k: SimpleNamespace(stdout="runtime.agent.md\n"))
        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(128, "git")
        with self.assertRaises(subprocess.CalledProcessError):
            check_tracked_runtime(self.root, fail)
