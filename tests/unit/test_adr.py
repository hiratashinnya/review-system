"""Issue #540: ADR のスキーマ・CLI・GitHub境界・hook・索引の回帰検証。"""
import copy
import datetime
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch
from adr.model import normalize
from adr.store import load, write
from adr.cli import main
from adr.github import stale, create_issue, issue_body
from adr.hook import notification
from adr.check import check
from adr.schema import ADR_SPEC
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.schema_types import DocSpec, Field, TableSpec
from feedback_ledger.tomlwrite import LINE, STRLIST
from harness_trace import adapt_document, build_index
from dsv2.query import deps, dependents, orphans


def draft(topic="器を共有する"):
    return dict(schema="harness-adr/v1.0", id="ADR-20261016-" + topic, topic=topic,
                decided_at=datetime.date(2026, 10, 16), phase="implementation", recorded_by="Codex",
                affected_assets=["adr"], supersedes="", owner_decision_refs=[],
                source=[dict(issue=540, pr=0)], context=dict(problem="判断を残す\n", constraints=""),
                decision=dict(chosen="道具ごとに分離\n", rationale="責務を守る\n",
                              tracking_status="pending", tracking_issue=0, no_tracking_reason=""),
                alternatives=[dict(option="共有台帳\n", rejection_reason="目的が混ざる\n")],
                consequences=dict(positive="追跡できる\n", negative="", followups=""))


class AdrTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "adr").mkdir()
        self.root = self.repo / "tool" / "adr"

    def cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main([*args, "--root", str(self.root), "--repo", str(self.repo)])
        return code, output.getvalue(), errors.getvalue()

    def test_required_fields_and_tracking_states(self):
        self.assertEqual(normalize(draft())["decision"]["tracking_status"], "pending")
        for mutate in (
            lambda d: d.update(alternatives=[]),
            lambda d: d["decision"].pop("tracking_status"),
            lambda d: d["decision"].update(tracking_status="filed"),
            lambda d: d["decision"].update(tracking_status="not_needed"),
            lambda d: d["decision"].update(tracking_status="pending", tracking_issue=9),
            lambda d: d.update(topic="あ" * 31),
            lambda d: d.update(owner_decision_refs=["FBK-invalid"]),
        ):
            data = draft()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                normalize(data)
        for status, issue, reason in (("filed", 540, ""), ("not_needed", 0, "自己完結\n")):
            data = draft()
            data["decision"].update(tracking_status=status, tracking_issue=issue,
                                    no_tracking_reason=reason)
            normalize(data)

    def test_multiple_roots_and_overwrite_collision(self):
        for root in (self.root, self.repo / "another" / "adr"):
            write(root, draft())
            self.assertEqual(load(root)[0][0], draft())
        with self.assertRaises(ValueError):
            write(self.root, draft())
        data = draft("A")
        write(self.root, data)
        with self.assertRaises(ValueError):
            write(self.root, draft("a"))
        write(self.root, draft(".と&と𠮷"))

    def test_new_entry_todo_hook_and_file_issue(self):
        from feedback_ledger.tomlwrite import dumps
        path = self.repo / "draft.toml"
        path.write_text(dumps(ADR_SPEC, draft()))
        code, output, _ = self.cli("new-entry", "--draft", str(path))
        self.assertEqual(code, 0)
        self.assertIn("systemMessage", output)
        code, output, _ = self.cli("todo")
        self.assertEqual(len(json.loads(output)), 1)
        payload = dict(tool_name="Bash", cwd=str(self.repo), tool_input={
            "command": f"python3 -m adr new-entry --root '{self.root}' --draft '{path}'"})
        self.assertIn("systemMessage", notification(payload))
        self.assertEqual(notification(dict(tool_name="Bash", tool_input={"command": "echo hi"})), {})
        code, output, _ = self.cli("file-issue", "--id", draft()["id"])
        self.assertEqual(code, 0)
        self.assertIn("alternatives", output)
        with patch("adr.cli_write.create_issue", return_value=(777, "https://github.com/a/b/issues/777")):
            code, output, error = self.cli("file-issue", "--id", draft()["id"], "--create")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(load(self.root)[0][0]["decision"]["tracking_issue"], 777)
        self.assertEqual(json.loads(self.cli("todo")[1]), [])
        self.assertEqual(self.cli("file-issue", "--id", draft()["id"], "--create")[0], 1)

    def test_references_canonical_render_and_immutability(self):
        def git(*args):
            return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, check=True)
        git("init", "-q")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "test")
        path = write(self.root, draft())
        git("add", ".")
        git("commit", "-qm", "initial")
        git("branch", "base")
        self.assertEqual(check(self.root, self.repo, base="base"), [])
        data = draft("置換する")
        data["supersedes"] = draft()["id"]
        write(self.root, data)
        view = json.loads(self.cli("render")[1])
        self.assertEqual({d["id"]: d["derived_status"] for d in view}[draft()["id"]], "superseded")
        path.write_text(path.read_text() + "\n")
        errors = check(self.root, self.repo, base="base")
        self.assertTrue(any("L7" in error for error in errors))
        data = draft()
        data["decision"].update(tracking_status="filed", tracking_issue=777)
        write(self.root, data, replace=True)
        self.assertEqual(check(self.root, self.repo, base="base"), [])
        data["decision"]["chosen"] = "変更\n"
        write(self.root, data, replace=True)
        self.assertTrue(any("L6" in error for error in check(self.root, self.repo, base="base")))
        data = draft("未実在")
        data["owner_decision_refs"] = ["FBK-20261016-不存在"]
        write(self.root, data)
        self.assertTrue(any("L3" in error for error in check(self.root, self.repo, base="base")))

    def test_symlinks_and_missing_base(self):
        write(self.root, draft())
        with self.assertWarns(UserWarning):
            self.assertEqual(check(self.root, self.repo), [])
        self.assertTrue(check(self.root, self.repo, require_base=True))
        target = self.repo / "linked"
        target.symlink_to(self.root)
        with self.assertRaises(ValueError):
            load(target)

    def test_github_boundaries_and_stale(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            if "create" in argv:
                body = Path(argv[argv.index("--body-file") + 1]).read_text()
                self.assertIn("ADR-20261016", body)
                return subprocess.CompletedProcess(argv, 0, "https://github.com/a/b/issues/22\n", "")
            return subprocess.CompletedProcess(argv, 0, json.dumps(dict(
                state="OPEN", updatedAt="2026-10-01T00:00:00Z", url="https://example.test")), "")
        self.assertEqual(create_issue(draft(), self.repo, runner)[0], 22)
        data = draft()
        data["decision"].update(tracking_status="filed", tracking_issue=22)
        rows = stale([(data, "")], self.repo, 14, runner=runner,
                     now=datetime.datetime(2026, 10, 16, tzinfo=datetime.timezone.utc))
        self.assertEqual(rows[0]["tracking_issue"], 22)
        self.assertEqual(stale([(draft(), "")], self.repo, 14, runner=runner), [])
        with self.assertRaises(ValueError):
            stale([], self.repo, -1)
        self.assertNotIn("owner_verbatim", issue_body(draft()))

    def test_adapter_uses_arbitrary_ref_declarations(self):
        docs = [(ADR_SPEC, draft(), "adr.toml"),
                (LEDGER_SPEC, dict(id="FBK-20261016-決定", supersedes="", source=[]), "ledger.toml")]
        for kind in ("ChangePlan", "VerificationDesign"):
            spec = DocSpec(kind, "envelope/v1", "", None, (
                TableSpec("", (Field("different_name", STRLIST, ref="adr"),)),
                TableSpec("nested", (Field("another_name", LINE, ref="ledger"),), True),))
            data = dict(id=kind + "-1", different_name=[draft()["id"]],
                        nested=[dict(another_name="FBK-20261016-決定")])
            docs.append((spec, data, kind + ".json"))
        meta = build_index(docs)
        self.assertTrue(deps(meta, "ChangePlan-1")[0]["exists"])
        self.assertEqual(len(dependents(meta, draft()["id"])), 2)
        self.assertEqual(orphans(meta), [])
        self.assertEqual(adapt_document(ADR_SPEC, draft(), "adr")["edges"], [])
        with self.assertRaises(ValueError):
            build_index([docs[0], docs[0]])

    def test_persistent_envelope_input(self):
        from adr.index import index
        write(self.root, draft())
        filename = self.repo / "plan.json"
        filename.write_text(json.dumps({"doc_spec": {"kind": "ChangePlan", "schema": "plan/v1",
            "tables": [{"name": "", "fields": [{"name": "decisions", "kind": STRLIST,
                                                         "ref": "adr"}]}]},
            "document": {"id": "CP-540", "decisions": [draft()["id"]]}}))
        meta = index(self.root, self.repo, [filename])
        self.assertTrue(deps(meta, "CP-540")[0]["exists"])
        self.assertEqual(dependents(meta, draft()["id"])[0]["from"], "CP-540")


if __name__ == "__main__":
    unittest.main()
