"""必読資料の限定読込と Codex gate の契約。"""

import json
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agy_delegate.reference import REFERENCES, read_reference, reference_context
from tests.unit.test_codex_agent_command_gate import payload, run_gate

ROOT = Path(__file__).resolve().parents[2]
COMMAND = "python3 -m agy_delegate.reference"


class ReferenceTests(unittest.TestCase):
    def test_real_references_are_readable(self):
        for name in REFERENCES:
            with self.subTest(name=name):
                self.assertTrue(read_reference(ROOT, name))

    def test_unknown_and_symlinked_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                read_reference(root, ".env")
            name = REFERENCES[0]
            path = root / name
            path.parent.mkdir(parents=True)
            path.symlink_to(ROOT / name)
            with self.assertRaises(OSError):
                read_reference(root, name)
            path.unlink()
            path.parent.rmdir()
            path.parent.symlink_to((ROOT / name).parent, target_is_directory=True)
            with self.assertRaises(OSError):
                read_reference(root, name)

    def test_hook_injects_full_references_only_for_delegate(self):
        hook = ROOT / ".codex/hooks/agy-reference-context.py"
        def invoke(role):
            return subprocess.run([sys.executable, str(hook)], cwd=ROOT,
                                  input=json.dumps({"agent_type": role}),
                                  text=True, capture_output=True, check=True).stdout
        result = invoke("agy-delegate")
        for name in REFERENCES:
            self.assertIn(read_reference(ROOT, name), result)
        self.assertTrue(result.endswith("AGY_REFERENCE_CONTEXT_COMPLETE\n"))
        self.assertEqual(invoke("other"), "")

    def test_missing_or_oversized_context_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(OSError):
                reference_context(root)
            for name in REFERENCES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x" * 22000)
            with self.assertRaisesRegex(ValueError, "65536"):
                reference_context(root)

    def test_hook_failure_instructs_stop_without_completion_marker(self):
        spec = importlib.util.spec_from_file_location(
            "agy_reference_hook", ROOT / ".codex/hooks/agy-reference-context.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out = io.StringIO()
        with patch.object(module.sys, "stdin", io.StringIO('{"agent_type":"agy-delegate"}')):
            with patch.object(module, "reference_context", side_effect=OSError("unavailable")):
                with redirect_stdout(out):
                    self.assertEqual(module.main(), 0)
        self.assertIn("停止", out.getvalue())
        self.assertNotIn("AGY_REFERENCE_CONTEXT_COMPLETE", out.getvalue())

    def test_gate_rejects_reference_command(self):
        def check(command, workdir=None):
            body = payload("agy-delegate", command, tool_name="exec_command")
            if workdir is not None:
                body["tool_input"]["workdir"] = workdir
            return run_gate(body, cwd=ROOT)

        for command in (COMMAND, COMMAND + " extra", COMMAND + "; true", "cat .env",
                        "python3 -m agy_delegate.reference --help", "python3 -c pass"):
            with self.subTest(command=command):
                self.assertIsNotNone(check(command))
        self.assertIsNotNone(check(COMMAND, "/tmp"))


if __name__ == "__main__":
    unittest.main()
