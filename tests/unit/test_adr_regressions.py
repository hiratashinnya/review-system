"""ADRの全索引参照・資産preflight・書込通知の回帰。"""
import io
import json
import tempfile
import unittest
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from adr.check import check
from adr.cli import main
from adr.hook import notification
from adr.notice_roots import register_root
from adr.schema import ADR_SPEC
from adr.store import write
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.tomlwrite import dumps
from tests.unit.test_adr import draft
from tests.unit.test_feedback_ledger import ledger_data


class AdrRegressionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.root = self.repo / "tool" / "adr"
        (self.repo / "adr").mkdir()

    def test_check_all_index_sources_and_arbitrary_ref_fields(self):
        ledger = ledger_data(supersedes="FBK-20261016-不存在")
        path = self.repo / ".ai/feedback" / LEDGER_SPEC.subdir / (ledger["id"] + ".toml")
        path.parent.mkdir(parents=True)
        path.write_text(dumps(LEDGER_SPEC, ledger))
        envelopes = []
        for kind in ("ChangePlan", "VerificationDesign"):
            envelope = self.repo / (kind + ".json")
            envelope.write_text(json.dumps({"doc_spec": {"kind": kind, "schema": "plan/v1",
                "tables": [{"name": "", "fields": [{"name": "arbitrary", "kind": "strlist",
                                                         "ref": "adr"}]}]},
                "document": {"id": kind + "-540", "arbitrary": ["ADR-20261016-不存在"]}}))
            envelopes.append(envelope)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            errors = check(self.root, self.repo, envelopes=envelopes)
        self.assertEqual(len(errors), 3)
        for source in (str(path), *(str(envelope) for envelope in envelopes)):
            self.assertTrue(any(source in error and "L3" in error for error in errors))

    def test_new_entry_preflight_rejects_missing_and_external_assets(self):
        for asset in ("missing", "..", str(self.repo.parent)):
            data = draft()
            data["affected_assets"] = [asset]
            source = self.repo / "draft.toml"
            source.write_text(dumps(ADR_SPEC, data))
            with self.subTest(asset=asset), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = main(["new-entry", "--root", str(self.root), "--repo", str(self.repo),
                             "--draft", str(source)])
            self.assertEqual(code, 1)
            self.assertFalse((self.root / (data["id"] + ".toml")).exists())
        data["affected_assets"] = ["adr", "draft.toml"]
        source.write_text(dumps(ADR_SPEC, data))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["new-entry", "--root", str(self.root), "--repo", str(self.repo),
                                   "--draft", str(source)]), 0)

    def test_hook_resolves_cd_separators_and_all_tool_routes(self):
        write(self.root, draft())
        with redirect_stdout(io.StringIO()):
            register_root(self.root, self.repo)
        for command in ("cd tool && python3 -m adr new-entry --root adr --draft x",
                        "cd tool;python3 -m adr file-issue --root=adr --id x;echo done",
                        "cd tool\npython3 -m adr new-entry --root=adr --draft x"):
            routes = (("Bash", {"command": command}),
                      ("mcp__plugin_context-mode_context-mode__ctx_execute", {"code": command}),
                      ("mcp__plugin_context-mode_context-mode__ctx_batch_execute",
                       {"commands": [{"command": command}]}))
            for tool, inputs in routes:
                with self.subTest(tool=tool, command=command):
                    result = notification(dict(tool_name=tool, cwd=str(self.repo), tool_input=inputs))
                    self.assertIn(draft()["id"], result["systemMessage"])
