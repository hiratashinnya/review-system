"""分割前の verb の出力、パーサ、ファイル副作用を静的 golden で固定する。"""
import __future__
import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, owner_cli, paths, reviewer_cli
from tests.unit.karte_support import finding, report_text, verb_parsers

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures/karte/cli_verbs_golden.json"
REPORT = report_text(("new", finding("a.py::f", "入力を検査しない")))
REPORT_TWO = report_text(("new", finding("a.py::f", "入力を検査しない")),
                         ("new", finding("b.py::g", "境界を検査しない")))
DIFF = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1,2 @@ def f():\n+x\n"
APPEND = ["append", "--issue", "7", "--finding-ids", "F-7-01", "--root-cause", "cause",
          "--change-kind", "logic", "--targets", "a.py::f"]
CLOSE = ["close-attempt", "--issue", "7", "--outcome", "fixed", "--diff-file", "tmp/diff"]
EXTRA = (reviewer_cli.register, owner_cli.register)


def compact(text):
    return "".join(text.split())


def normalize_usage(text):
    text = compact(text)
    prefix, marker, choices = text.partition("(choosefrom")
    return prefix + marker + choices.replace("'", "") if marker else text


def snapshot(root):
    directory = root / "tmp/_karte"
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()} if directory.exists() else {}


def invoke(root, argv, stdin="", extra=()):
    before = snapshot(root)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            args = cli.build_parser(extra).parse_args(argv)
            args.repo_root = str(root)
            with mock.patch("sys.stdin", io.StringIO(stdin)):
                code = args.func(args)
        except SystemExit as exc:
            code = exc.code
    after = snapshot(root)
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    return {"exit_code": code, "stdout": out.getvalue().replace(str(root), "<ROOT>"),
            "stderr": err.getvalue().replace(str(root), "<ROOT>"),
            "before": before, "after": after, "changed": changed,
            "directory_exists": (root / "tmp/_karte").exists()}


def action_value(value):
    if callable(value):
        return {"callable": value.__name__}
    if value is argparse.SUPPRESS:
        return "==SUPPRESS=="
    return value


def parser_contract(extra):
    parser = cli.build_parser(extra)
    parsers = {"<top>": parser, **verb_parsers(parser)}
    result = {"order": list(verb_parsers(parser)), "parsers": {}}
    for name, item in parsers.items():
        actions = []
        for a in item._actions:
            choices = list(a.choices) if a.choices is not None else None
            actions.append({"dest": a.dest, "options": a.option_strings, "required": a.required,
                            "choices": choices, "nargs": a.nargs, "default": action_value(a.default)})
        result["parsers"][name] = {"help_compact_sha256": hashlib.sha256(compact(item.format_help()).encode()).hexdigest(),
                                   "actions": actions}
    return result


def cli_names():
    result = {}
    for name, value in vars(cli).items():
        if name.startswith("__"):
            continue
        if isinstance(value, types.ModuleType):
            kind = "module"
        elif isinstance(value, type):
            kind = "type"
        elif callable(value):
            kind = "function"
        elif isinstance(value, type(__future__.annotations)):
            kind = "feature"
        else:
            kind = "constant"
        result[name] = {"kind": kind, **({"value": value} if kind == "constant" else {})}
    return result


def cases():
    results = {}
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        (root / "tmp").mkdir()
        (root / "tmp/diff").write_text(DIFF, encoding="utf-8")
        (root / "tmp/empty").write_text("", encoding="utf-8")
        (root / "tmp/bad-utf8").write_bytes(b"\xff")
        (root / "tmp/report").write_text(REPORT, encoding="utf-8")

        def run(name, args, stdin="", extra=()):
            results[name] = invoke(root, args, stdin, extra)

        run("missing_verb", [])
        run("unknown_verb", ["missing"])
        run("missing_from", ["ingest-review", "--issue", "7", "--round", "1"])
        run("invalid_choice", APPEND[:-3] + ["invalid", "--targets", "a.py::f"])
        run("missing_append_required", ["append"])
        run("issue_invalid_prepare", ["ingest-review", "--issue", "bad", "--round", "1", "--from", "-"] , REPORT)
        run("empty_stdin_prepare", ["ingest-review", "--issue", "7", "--round", "1", "--from", "-"])
        run("unknown_path", ["ingest-review", "--issue", "7", "--round", "1", "--from", "tmp/missing"])
        run("utf8_invalid", ["ingest-review", "--issue", "7", "--round", "1", "--from", "tmp/bad-utf8"])
        run("validation_locked", ["ingest-review", "--issue", "7", "--round", "1", "--from", "-"], "### new\nharm: real\n")
        run("not_found", ["render", "--issue", "7"])
        run("ingest_file", ["ingest-review", "--issue", "7", "--round", "1", "--from", "tmp/report"])
        run("ingest_same_round", ["ingest-review", "--issue", "7", "--round", "1", "--from", "-"], REPORT)
        run("ingest_missing_previous", ["ingest-review", "--issue", "7", "--round", "2", "--from", "-"], "### new\n")
        run("render", ["render", "--issue", "7"])
        run("render_json_unsupported", ["render", "--issue", "7", "--json"])
        run("status", ["status", "--issue", "7"])
        run("status_json", ["status", "--issue", "7", "--json"])
        run("check_no_attempt", ["check", "--issue", "7", "--round", "1"])
        run("close_no_attempt", CLOSE)
        run("append_unknown", [*APPEND[:4], "F-7-99", *APPEND[5:]])
        run("append_bad_slug", [*APPEND[:6], "BAD SLUG", *APPEND[7:]])
        run("append_round_non_numeric", [*APPEND, "--round", "abc"])
        run("append_explicit_round", [*APPEND, "--round", "1"])
        run("check_unclosed", ["check", "--issue", "7", "--round", "1"])
        run("close_invalid_base", ["close-attempt", "--issue", "7", "--outcome", "fixed", "--base=-bad"])
        run("close_empty_diff", [*CLOSE[:-1], "tmp/empty"])
        run("close_explicit", [*CLOSE, "--attempt", "1"])
        run("close_already_closed", [*CLOSE, "--attempt", "1"])
        run("check_ok", ["check", "--issue", "7", "--round", "1"])
        run("append_pointer_round", APPEND)
        run("close_implicit", CLOSE)
        run("append_saturated", APPEND)
        run("decide", ["decide", "--issue", "7", "--finding", "F-7-01", "--disposition", "deferred", "--deferred-to", "#42"], extra=EXTRA)
        run("check_disposition", ["check", "--issue", "7", "--round", "1"])
        run("activate", ["activate", "--issue", "7"], extra=EXTRA)
        run("ingest_reviewer", ["ingest-reviewer", "--from", "tmp/missing"], extra=EXTRA)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        (root / "tmp").mkdir()
        (root / "tmp/diff").write_text(DIFF.replace("a.py", "other.py"), encoding="utf-8")
        invoke(root, ["ingest-review", "--issue", "7", "--round", "1", "--from", "-"], REPORT_TWO)
        results["ingest_missing_previous"] = invoke(
            root, ["ingest-review", "--issue", "7", "--round", "2", "--from", "-"],
            report_text(("F-7-01", finding("a.py::f", "入力を検査しない"))))
        (root / "tmp/_karte/active.json").unlink()
        results["append_implicit_without_pointer"] = invoke(root, APPEND)
        results["check_undiagnosed"] = invoke(root, ["check", "--issue", "7", "--round", "1"])
        results["append_second_open"] = invoke(root, [*APPEND[:6], "other-cause", *APPEND[7:]])
        results["close_multiple_open"] = invoke(root, CLOSE)
        results["close_target_mismatch"] = invoke(root, [*CLOSE, "--attempt", "1"])
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        (root / "tmp").mkdir()
        results["ingest_stdin"] = invoke(root, ["ingest-review", "--issue", "7", "--round", "1", "--from", "-"], REPORT)
        (root / "tmp/_karte/issue-7.md").write_text("invalid ledger\n", encoding="utf-8")
        results["format_error"] = invoke(root, ["render", "--issue", "7"])
        with mock.patch.object(paths, "read_text", side_effect=OSError("storage failure")):
            results["os_error"] = invoke(root, ["render", "--issue", "7"])
    return results


class TestKarteCliVerbsCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_verb_outputs_and_file_effects(self):
        actual = cases()
        self.assertEqual(set(self.golden["cases"]), set(actual))
        for name, result in actual.items():
            with self.subTest(case=name):
                expected = self.golden["cases"][name].copy()
                result = result.copy()
                if expected["stderr"].startswith("usage:") and result["stderr"].startswith("usage:"):
                    expected["stderr"] = normalize_usage(expected["stderr"])
                    result["stderr"] = normalize_usage(result["stderr"])
                self.assertEqual(expected, result)

    def test_compact_preserves_content_and_order(self):
        usage = "usage: tool --first VALUE --second OTHER"
        self.assertEqual(compact(usage), compact("usage: tool --first\n  VALUE --sec\n  ond OTHER"))
        self.assertNotEqual(compact(usage), compact("usage: tool --second OTHER --first VALUE"))
        self.assertNotEqual(compact(usage), compact("usage: tool --first VALUE --second DIFFERENT"))

    def test_scenarios_exercise_the_named_contracts(self):
        c = self.golden["cases"]
        for name in ("issue_invalid_prepare", "empty_stdin_prepare", "missing_from"):
            self.assertFalse(c[name]["directory_exists"], name)
        self.assertEqual([".writer.lock"], c["validation_locked"]["changed"])
        for name in ("validation_locked", "ingest_missing_previous", "append_unknown", "append_bad_slug",
                     "append_saturated", "close_empty_diff", "empty_stdin_prepare", "missing_from"):
            self.assertEqual({k: v for k, v in c[name]["before"].items() if k != ".writer.lock"},
                             {k: v for k, v in c[name]["after"].items() if k != ".writer.lock"}, name)
        self.assertIn("再掲されていない", c["ingest_missing_previous"]["stderr"])
        self.assertIn("飽和した", c["close_implicit"]["stdout"])
        self.assertIn("重ならない", c["close_target_mismatch"]["stdout"])
        self.assertIn("disposition", c["check_disposition"]["stdout"])
        self.assertEqual(3, c["append_saturated"]["exit_code"])

    def test_parser_contracts(self):
        self.assertEqual(self.golden["parser_basic"], parser_contract(()))
        self.assertEqual(self.golden["parser_extended"], parser_contract(EXTRA))

    def test_original_cli_names_remain_resolvable_with_the_same_kind(self):
        actual = cli_names()
        for name, info in self.golden["names"].items():
            with self.subTest(name=name):
                self.assertTrue(hasattr(cli, name))
                self.assertEqual(info, actual[name])
