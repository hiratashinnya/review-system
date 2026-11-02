"""必読資料の限定読込と Codex gate の契約。"""

import tempfile
import unittest
from pathlib import Path

from agy_delegate.reference import REFERENCES, read_reference
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

    def test_gate_allows_only_exact_reference_command_at_root(self):
        def check(command, workdir=None):
            body = payload("agy-delegate", command, tool_name="exec_command")
            if workdir is not None:
                body["tool_input"]["workdir"] = workdir
            return run_gate(body, cwd=ROOT)

        self.assertIsNone(check(COMMAND))
        for command in (COMMAND + " extra", COMMAND + "; true", "cat .env",
                        "python3 -m agy_delegate.reference --help", "python3 -c pass"):
            with self.subTest(command=command):
                self.assertIsNotNone(check(command))
        self.assertIsNotNone(check(COMMAND, "/tmp"))


if __name__ == "__main__":
    unittest.main()
