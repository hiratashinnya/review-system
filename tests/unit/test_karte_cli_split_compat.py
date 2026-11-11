"""分割前の render/status の出力を golden と比較する。

再記録は分割前に限り ``python3 -m tests.unit.test_karte_cli_split_compat --record-golden``。
通常の unittest 実行は golden を書き換えない。
"""

import argparse
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from karte import cli, model, similarity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures/karte/cli_render_status_golden.json"
ISSUE = "307"


def finding(number, **overrides):
    fields = dict(
        id=f"F-307-{number:02d}", harm_detail="入力が正しく処理されない",
        locus=["a.py::f", "b.py::g"], summary=f"指摘 {number}", evidence="確認した根拠",
        expected="期待する結果", recheck="再確認する", rounds=[1],
    )
    return model.Finding(**(fields | overrides))


def attempt(number, kind="logic", target="a.py::f"):
    return model.Attempt(number, number, ["F-307-01"], "same-cause", kind, [target], "診断")


def cases():
    empty = model.new_karte(307)
    clean = model.new_karte(307)
    clean.findings = [
        finding(1, disposition="deferred", deferred_to="#42"),
        finding(2, disposition="waived", waived_by="owner", waived_reason="合意済み"),
        finding(3, status="resolved", rounds=[1, 2], resolved_round=3),
    ]
    harmful = model.new_karte(307)
    harmful.findings = [finding(1), finding(2, scope="out", disposition="fix-here", locus=[])]
    no_harm = model.new_karte(307)
    no_harm.findings = [
        finding(1, harm="none", disposition="deferred", deferred_to="#42", locus=[]),
        finding(2, disposition="waived", waived_by="owner", waived_reason="合意済み"),
    ]
    two_rounds = model.new_karte(307)
    two_rounds.findings = [finding(1, rounds=[1, 2])]
    stalled = model.new_karte(307)
    stalled.findings = [finding(1, rounds=[1, 2, 3])]
    open_attempt = model.new_karte(307)
    open_attempt.findings = [finding(1)]
    open_attempt.attempts = [attempt(1)]
    pair = model.new_karte(307)
    pair.findings = [finding(1)]
    pair.attempts = [attempt(1, target="a.py::f"), attempt(2, target="b.py::g")]
    pair.results = [
        model.Result(1, ["F-307-01"], ["a.py", "a.py::f"], "partial", "一部"),
        model.Result(1, ["F-307-01"], ["c.py"], "regressed", "別の結果"),
    ]
    chain = model.new_karte(307)
    chain.findings = [finding(1)]
    chain.attempts = [
        attempt(1, target="a.py::f"), attempt(2, target="b.py::g"),
        attempt(3, kind="interface", target="b.py::g"),
    ]
    return {
        "empty-clean": (empty, False),
        "clean-deferred-waived-resolved": (clean, False),
        "harmful-in-out-fix-here": (harmful, False),
        "no-harm-disposition": (no_harm, False),
        "two-rounds": (two_rounds, False),
        "three-rounds-stalled": (stalled, False),
        "unclosed-attempt": (open_attempt, False),
        "pair-saturated-multiple-results": (pair, False),
        "nontransitive-chain": (chain, False),
        "pointer-completion": (harmful, True),
    }


def error_cases():
    return {
        "not-found": (ISSUE, None, None),
        "invalid-issue-text": ("abc", None, None),
        "invalid-issue-non-ascii": ("１２", None, None),
        "missing-pointer": (None, None, None),
        "broken-pointer": (None, "{broken", None),
        "broken-karte": (ISSUE, None, "not a karte\n"),
    }


def key_orders(value):
    if isinstance(value, dict):
        return {"keys": list(value), "children": [key_orders(v) for v in value.values()]}
    if isinstance(value, list):
        return [key_orders(v) for v in value]
    return None


def invoke(root, verb, issue):
    output, error = io.StringIO(), io.StringIO()
    args = argparse.Namespace(repo_root=str(root), issue=issue, json=verb == "status-json")
    func = cli.cmd_render if verb == "render" else cli.cmd_status
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
        code = func(args)
    # 一時ルートの絶対パスだけを置換し、相対パスとメッセージはそのまま残す。
    stdout = output.getvalue().replace(str(root), "<REPO_ROOT>")
    stderr = error.getvalue().replace(str(root), "<REPO_ROOT>")
    result = {"exit_code": code, "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest()}
    if code:
        result["stderr"] = stderr
    else:
        if stderr:
            raise AssertionError(f"成功時の stderr が空でない: {stderr}")
        if verb == "status-json":
            payload = json.loads(stdout)
            result["json"] = payload
            result["json_key_order"] = key_orders(payload)
    return result, stdout


def prepare(root, text=None, pointer=None):
    directory = root / "tmp/_karte"
    directory.mkdir(parents=True)
    if text is not None:
        (directory / "issue-307.md").write_text(text, encoding="utf-8")
    if pointer is not None:
        (directory / "active.json").write_text(pointer, encoding="utf-8")


def build_outcomes():
    outcomes = {}
    for name, (karte, use_pointer) in cases().items():
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            pointer = '{"issue": 307, "round": 3}' if use_pointer else None
            prepare(root, model.dumps(karte), pointer)
            outcomes[name] = {
                verb: invoke(root, verb, None if use_pointer else ISSUE)[0]
                for verb in ("render", "status", "status-json")
            }
    for name, (issue, pointer, text) in error_cases().items():
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prepare(root, text, pointer)
            outcomes[name] = {
                verb: invoke(root, verb, issue)[0]
                for verb in ("render", "status", "status-json")
            }
    return outcomes


class TestCliSplitCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        cls.current = build_outcomes()

    def test_every_recorded_outcome_is_reproduced(self):
        self.assertEqual(set(self.current), set(self.golden))
        for case in self.golden:
            for verb in ("render", "status", "status-json"):
                with self.subTest(case=case, verb=verb):
                    self.assertEqual(self.current[case][verb], self.golden[case][verb])

    def test_render_directive_and_nontransitive_similarity(self):
        for name, expected in (("unclosed-attempt", False), ("pair-saturated-multiple-results", True)):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                prepare(root, model.dumps(cases()[name][0]))
                result, output = invoke(root, "render", ISSUE)
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual("DIRECTIVE: アプローチ転換" in output, expected)
        attempts = cases()["nontransitive-chain"][0].attempts
        views = [similarity.AttemptView(a.number, a.root_cause, a.change_kind, tuple(a.targets))
                 for a in attempts]
        self.assertIsNotNone(similarity.compare(views[0], views[1]))
        self.assertIsNotNone(similarity.compare(views[1], views[2]))
        self.assertIsNone(similarity.compare(views[0], views[2]))

    def test_scenarios_have_the_intended_behavior(self):
        def payload(name):
            return self.current[name]["status-json"]["json"]

        self.assertEqual(payload("empty-clean")["verdict"], "clean")
        self.assertEqual(payload("clean-deferred-waived-resolved")["verdict"], "clean")
        self.assertEqual(payload("harmful-in-out-fix-here")["verdict"], "harmful-open")
        self.assertEqual(payload("no-harm-disposition")["verdict"], "no-harm-only")
        self.assertEqual(payload("two-rounds")["stalled_findings"], [])
        self.assertEqual(payload("three-rounds-stalled")["stalled_findings"], ["F-307-01"])
        self.assertTrue(payload("three-rounds-stalled")["escalate"])
        self.assertEqual(payload("pair-saturated-multiple-results")["saturated_groups"], [[1, 2]])
        self.assertEqual(payload("nontransitive-chain")["saturated_groups"], [[1, 2], [1, 2, 3], [2, 3]])
        for name in error_cases():
            for verb in ("render", "status", "status-json"):
                with self.subTest(case=name, verb=verb):
                    result = self.current[name][verb]
                    self.assertEqual(result["exit_code"], 2 if name == "not-found" else 4)
                    self.assertTrue(result["stderr"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--record-golden"]:
        GOLDEN.write_text(json.dumps(build_outcomes(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        unittest.main()
