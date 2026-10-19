"""UT-TC: 実在Red成果物とtarget配置のfail-close回帰。"""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from issue_envelope.check import check
from issue_envelope.store import write
from .fixtures import artifact


class ArtifactPathTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)

    def prepare(self, root):
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "test@example.invalid")
        self.git(root, "config", "user.name", "Envelope Test")
        data = artifact("TestDesign")
        code = "import unittest\nclass Red(unittest.TestCase):\n def test_missing(self):\n  self.assertTrue(False, 'implementation missing')\n"
        for name, content in ((data["ut_td"][0], "# UT-TD\n実装前Red\n"),
                              (data["ut_tc"][0], code)):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        evidence = data["red_evidence"][0]
        result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests/tool"],
                                cwd=root, capture_output=True)
        self.assertEqual(result.returncode, 1)
        log = root / evidence["log"]
        log.parent.mkdir(parents=True)
        log.write_bytes(result.stdout + result.stderr)
        evidence.update(command="python3 -m unittest discover -s tests/tool", exit_code=1)
        for key in ("tc", "log"):
            evidence[key + "_sha256"] = hashlib.sha256((root / evidence[key]).read_bytes()).hexdigest()
        return data

    def test_committed_red_passes_and_missing_uncommitted_modified_fail(self):
        for mutation in ("valid", "missing_td", "missing_tc", "uncommitted", "modified", "empty_log", "missing_log", "bad_hash"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                data = self.prepare(root)
                if mutation == "empty_log":
                    (root / data["red_evidence"][0]["log"]).write_text("")
                if mutation == "bad_hash":
                    data["red_evidence"][0]["tc_sha256"] = "0" * 64
                write(root / "test_design/TD-371.toml", data)
                self.git(root, "add", ".")
                self.git(root, "commit", "-qm", "Red artifacts")
                name = data["ut_tc"][0]
                if mutation == "uncommitted":
                    self.git(root, "rm", "--cached", name)
                    self.git(root, "commit", "-qm", "Remove tracked TC")
                if mutation.startswith("missing_"):
                    name = {"missing_td": data["ut_td"][0], "missing_tc": name,
                            "missing_log": data["red_evidence"][0]["log"]}[mutation]
                    (root / name).unlink()
                if mutation == "modified":
                    (root / name).write_text("changed")
                errors = check(root)
                self.assertEqual(bool(errors), mutation != "valid", errors)

    def test_leaf_scope_matches_exact_target_for_cp_and_vd(self):
        for kind, prefix, directory in (("ChangePlan", "CP", "change_plan"),
                                         ("VerificationDesign", "VD", "verification_design")):
            data = artifact(kind, f"{prefix}-371-leaf", f"{prefix}-371")
            data["scope"] = ["tool", "group/nested"]
            for target in ("tool", "group/nested", "unrelated", "group", "tool/deeper"):
                with tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    parent = artifact(kind, children=[data["id"]])
                    parent["scope"] = data["scope"]
                    write(root / directory / f"{prefix}-371.toml", parent)
                    path = root / target / directory / f"{prefix}-371.toml"
                    write(path, data)
                    errors = check(root)
                    self.assertEqual(any("scope配下" in error for error in errors),
                                     target not in data["scope"], errors)

    def test_missing_red_table_is_rejected(self):
        data = artifact("TestDesign")
        data["red_evidence"] = []
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            write(Path(folder) / "test_design/TD-371.toml", data)

    def test_unsafe_path_refs_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.prepare(root)
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "Assets")
            (root / "linked").symlink_to(root / data["ut_tc"][0])
            from issue_envelope.path_binding import path_errors
            for name in ("../outside", str(root / data["ut_tc"][0]), "linked"):
                data["ut_td"] = [name]
                self.assertTrue(path_errors(root, data), name)
