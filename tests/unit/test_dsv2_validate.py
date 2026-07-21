"""doc-system-v2 validate.py の型別メタデータ検査。"""

from __future__ import annotations

import contextlib
import io
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_validate():
    path = Path(__file__).resolve().parents[2] / "doc-system-v2" / "validate.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("_dsv2_validate", path)
    assert spec is not None and spec.loader is not None, (
        f"failed to build import spec for {path}"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = _load_validate()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


class TestValidateIdentifierMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()

    def test_src_python_qualname_exists(self):
        _write(self.repo / "pkg/mod.py", "class Service:\n    def run(self):\n        pass\n")
        y = self.root / "nodes/06-implementation/src/service-run.yaml"
        _write(y, 'title: "service run"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'source.file: "pkg/mod.py"\n'
                  'source.qualname: "Service.run"\n'
                  'source.kind: method\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertFalse([m for m in msgs if m.startswith("ERROR")], msgs)

    def test_src_missing_qualname_is_error(self):
        _write(self.repo / "pkg/mod.py", "def present():\n    pass\n")
        y = self.root / "nodes/06-implementation/src/missing.yaml"
        _write(y, 'title: "missing"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'source.file: "pkg/mod.py"\n'
                  'source.qualname: "absent"\n'
                  'source.kind: function\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("source.qualname" in m for m in msgs), msgs)

    def test_tc_requires_test_metadata_and_existing_file(self):
        y = self.root / "nodes/04-verification/tc/tc-a.yaml"
        _write(y, 'title: "tc a"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("test.file/test.qualname/test.kind 必須" in m for m in msgs), msgs)

        _write(self.repo / "tests/test_sample.py", "def test_ok():\n    pass\n")
        _write(y, 'title: "tc a"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'test.file: "tests/test_sample.py"\n'
                  'test.qualname: "test_ok"\n'
                  'test.kind: pytest\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertFalse([m for m in msgs if m.startswith("ERROR")], msgs)

    def test_source_file_absolute_path_outside_repo_is_rejected(self):
        # issue #184: source.file/test.file が ast.parse でリポジトリ外の任意ファイルを読めてしまう
        # 挙動を防ぐ。リポジトリ外の絶対パスは「存在しない」判定より先に境界違反として ERROR にする。
        outside = Path(self.tmp.name).parent / f"outside-{Path(self.tmp.name).name}.py"
        _write(outside, "def evil():\n    pass\n")
        self.addCleanup(outside.unlink, missing_ok=True)
        y = self.root / "nodes/06-implementation/src/escape.yaml"
        _write(y, 'title: "escape"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  f'source.file: "{outside}"\n'
                  'source.qualname: "evil"\n'
                  'source.kind: function\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("リポジトリ配下のパスのみ許可" in m for m in msgs), msgs)

    def test_source_file_dotdot_escape_outside_repo_is_rejected(self):
        y = self.root / "nodes/06-implementation/src/escape-relative.yaml"
        _write(y, 'title: "escape relative"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'source.file: "../../../../../../etc/passwd"\n'
                  'source.qualname: "x"\n'
                  'source.kind: function\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("リポジトリ配下のパスのみ許可" in m for m in msgs), msgs)


class TestValidateScheduledRequired(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "doc-system-v2"
        self.root.mkdir()

    def test_empty_scheduled_is_error(self):
        y = self.root / "nodes/02-what/spec/empty-scheduled.yaml"
        _write(y, 'title: "empty scheduled"\nversion: "0.1.0"\n'
                  "labels: []\n"
                  'scheduled: ""\n'
                  "edges: []\n")
        _write(y.with_suffix(".md"), "body\n")

        msgs = validate.validate_node(y, self.root)

        self.assertIn("ERROR: scheduled が空", msgs)


_EXACT_LINK_COUNTS_RULES = (
    "exact_link_counts:\n"
    "  - { node: td, direction: incoming, peer: tc, count: 1, activate_stage: verification, severity: error, reason: \"TDはちょうど1つのTC\" }\n"
    "  - { node: tc, direction: outgoing, peer: td, count: 1, activate_stage: verification, severity: error, reason: \"TCはちょうど1つのTD\" }\n"
)


class TestValidateExactLinkCounts(unittest.TestCase):
    """activate_stage: verification が発火済み（current_stage: verification）の場合の挙動。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()
        _write(self.repo / "tests/test_sample.py", "def test_a():\n    pass\n\ndef test_b():\n    pass\n")
        _write(
            self.root / "config.yml",
            'current_stage: "verification"\n'
            "stages: [requirements, analysis, design, implementation, verification]\n"
            + _EXACT_LINK_COUNTS_RULES,
        )

    def _write_td(self, name: str) -> None:
        y = self.root / f"nodes/04-verification/td/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _write_tc(self, name: str, qualname: str, edges: str) -> None:
        _write(
            self.root / f"nodes/04-verification/tc/{name}.yaml",
            f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
            'test.file: "tests/test_sample.py"\n'
            f'test.qualname: "{qualname}"\n'
            "test.kind: pytest\n"
            "edges:\n"
            f"{edges}",
        )

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_main_reports_exact_link_count_violation(self):
        self._write_td("td-a")
        self._write_tc("tc-a", "test_a", "  - to: td-a\n    ref_version: \"0.1\"\n")
        self._write_tc("tc-b", "test_b", "  - to: td-a\n    ref_version: \"0.1\"\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("[NG] exact_link_counts", stdout)
        self.assertIn("td-a (td) incoming tc expected=1 actual=2", stdout)

    def test_main_accepts_td_tc_one_to_one(self):
        self._write_td("td-a")
        self._write_tc("tc-a", "test_a", "  - to: td-a\n    ref_version: \"0.1\"\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("exact_link_counts", stdout)


class TestValidateExactLinkCountsStageGating(unittest.TestCase):
    """issue #184: activate_stage 未達（current_stage が verification に未到達）なら段階的著作の
    途中状態（TD/TCを1件ずつ試験的に著作＝片方のみ存在）を ERROR にしないことを確認する。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()

    def _write_config(self, extra: str) -> None:
        _write(self.root / "config.yml", extra + _EXACT_LINK_COUNTS_RULES)

    def _write_td_only(self, name: str) -> None:
        y = self.root / f"nodes/04-verification/td/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_stage_below_verification_skips_exact_link_counts(self):
        # current_stage=design はまだ verification に未到達 → TD 単独著作（TC 不在）でも
        # exact_link_counts はスキップされ、段階的著作をブロックしない。
        self._write_config(
            'current_stage: "design"\n'
            "stages: [requirements, analysis, design, implementation, verification]\n"
        )
        self._write_td_only("td-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("exact_link_counts", stdout)

    def test_stage_at_verification_still_enforces_exact_link_counts(self):
        # current_stage=verification に達していれば、同じ TD 単独状態は従来どおり ERROR。
        self._write_config(
            'current_stage: "verification"\n'
            "stages: [requirements, analysis, design, implementation, verification]\n"
        )
        self._write_td_only("td-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("[NG] exact_link_counts", stdout)
        self.assertIn("td-a (td) incoming tc expected=1 actual=0", stdout)

    def test_missing_current_stage_defaults_to_inactive(self):
        # current_stage/stages が config.yml に未宣言のときは安全側（不活性）に倒す。
        self._write_config("")
        self._write_td_only("td-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("exact_link_counts", stdout)


class TestFindOrphanMds(unittest.TestCase):
    """issue #183: .yaml 起点の走査（main）で不可視になっていた孤立 .md の検出。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "doc-system-v2"
        self.root.mkdir()

    def _write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
        return p

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_orphan_md_without_yaml_is_detected(self):
        self._write(
            "nodes/02-what/spec/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n',
        )
        self._write("nodes/02-what/spec/x.md", "body\n")
        orphan = self._write("nodes/02-what/spec/stray.md", "誰にも参照されない本文\n")

        errs = validate.find_orphan_mds(self.root)

        self.assertEqual(errs, [f"ERROR: サイドカー欠落: {orphan.relative_to(self.root)}"])

    def test_body_ref_referenced_md_is_not_orphan(self):
        self._write("nodes/04-verification/td/shared.md", "# shared\n")
        self._write(
            "nodes/04-verification/td/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
            'body_ref.file: "nodes/04-verification/td/shared.md"\n'
            "edges: []\n",
        )

        errs = validate.find_orphan_mds(self.root)

        self.assertEqual(errs, [])

    def test_main_reports_orphan_md_and_nonzero_exit(self):
        self._write(
            "nodes/02-what/spec/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n',
        )
        self._write("nodes/02-what/spec/x.md", "body\n")
        self._write("nodes/02-what/spec/stray.md", "誰にも参照されない本文\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("orphan .md（yaml サイドカー欠落）", stdout)
        self.assertIn("stray.md", stdout)

    def test_main_no_orphan_when_corpus_clean(self):
        self._write(
            "nodes/02-what/spec/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n',
        )
        self._write("nodes/02-what/spec/x.md", "body\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("orphan .md", stdout)


_STAGES_LINE = "stages: [requirements, analysis, design, implementation, verification]\n"


class TestParseInlineConfigBracket(unittest.TestCase):
    """Phase B (#163): _parse_inline_config_dict / _split_config_items の bracket list 対応。

    契約: target: [a, b] を Python list に解釈し、既存 scalar/int（exact_link_counts 形）は不変。
    """

    def test_split_config_items_respects_brackets(self):
        items = validate._split_config_items("node: src, target: [mod, dm], severity: error")
        self.assertEqual(items, ["node: src", "target: [mod, dm]", "severity: error"])

    def test_parse_inline_dict_with_bracket_list(self):
        raw = "{node: src, target: [mod, dm, port, orc], activate_stage: implementation, severity: error}"
        d = validate._parse_inline_config_dict(raw, Path("config.yml"), 1)
        self.assertEqual(d["target"], ["mod", "dm", "port", "orc"])
        self.assertEqual(d["node"], "src")
        self.assertEqual(d["activate_stage"], "implementation")
        self.assertEqual(d["severity"], "error")

    def test_parse_inline_dict_scalar_regression(self):
        # 既存 exact_link_counts 形（list 無し）は挙動不変（回帰なし）。
        raw = ('{ node: td, direction: incoming, peer: tc, count: 1, '
               'activate_stage: verification, severity: error, reason: "TDはちょうど1つのTC" }')
        d = validate._parse_inline_config_dict(raw, Path("config.yml"), 1)
        self.assertEqual(d["count"], 1)
        self.assertEqual(d["direction"], "incoming")
        self.assertEqual(d["reason"], "TDはちょうど1つのTC")


class TestLoadSrcSymbolEligibility(unittest.TestCase):
    """Phase B (#163・DD-10): src_symbol_eligibility マッピングブロックの読取。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "doc-system-v2"
        self.root.mkdir()

    def test_reads_mapping_to_dict_of_lists(self):
        _write(
            self.root / "config.yml",
            "src_symbol_eligibility:\n"
            "  mod: [module]\n"
            "  dm: [module]\n"
            "  port: [class]\n",
        )
        self.assertEqual(
            validate.load_src_symbol_eligibility(self.root),
            {"mod": ["module"], "dm": ["module"], "port": ["class"]},
        )

    def test_undeclared_returns_empty_dict(self):
        _write(self.root / "config.yml", 'current_stage: "design"\n')
        self.assertEqual(validate.load_src_symbol_eligibility(self.root), {})


class TestLoadMustLinkRules(unittest.TestCase):
    """Phase B (#163): load_must_link_to / load_must_be_linked_from のブロックリスト読取。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "doc-system-v2"
        self.root.mkdir()

    def test_load_must_link_to_parses_target_lists(self):
        _write(
            self.root / "config.yml",
            "must_link_to:\n"
            "  - { node: p, target: [mod], activate_stage: design, severity: error, reason: \"P→MOD\" }\n"
            "  - { node: src, target: [mod, dm, port, orc], activate_stage: implementation, severity: error, reason: \"SRC\" }\n",
        )
        rules = validate.load_must_link_to(self.root)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["node"], "p")
        self.assertEqual(rules[0]["target"], ["mod"])
        self.assertEqual(rules[1]["target"], ["mod", "dm", "port", "orc"])

    def test_load_must_be_linked_from_preserves_applies_when(self):
        _write(
            self.root / "config.yml",
            "must_be_linked_from:\n"
            "  - { node: spec, source: [td], activate_stage: verification, severity: error, applies_when: condition_present, reason: \"spec←td\" }\n"
            "  - { node: mod, source: [src], activate_stage: implementation, severity: error, reason: \"mod←src\" }\n",
        )
        rules = validate.load_must_be_linked_from(self.root)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["source"], ["td"])
        self.assertEqual(rules[0]["applies_when"], "condition_present")
        self.assertEqual(rules[1]["source"], ["src"])
        self.assertNotIn("applies_when", rules[1])

    def test_undeclared_blocks_return_empty(self):
        _write(self.root / "config.yml", 'current_stage: "design"\n')
        self.assertEqual(validate.load_must_link_to(self.root), [])
        self.assertEqual(validate.load_must_be_linked_from(self.root), [])


class TestValidateMustLinkTo(unittest.TestCase):
    """Phase B (#163): validate_must_link_to の stage gating・severity・行整形と main 連携。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()

    def _write_config(self, current_stage: str | None, activate: str, severity: str) -> None:
        head = f'current_stage: "{current_stage}"\n{_STAGES_LINE}' if current_stage is not None else ""
        _write(
            self.root / "config.yml",
            head
            + "must_link_to:\n"
            + f"  - {{ node: p, target: [mod], activate_stage: {activate}, severity: {severity}, reason: \"P must map to MOD\" }}\n",
        )

    def _write_p(self, name: str, edges_yaml: str) -> None:
        y = self.root / f"nodes/03-analysis/p/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n{edges_yaml}')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _write_mod(self, name: str) -> None:
        y = self.root / f"nodes/05-design/mod/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_error_severity_gap_is_error_and_fails_exit(self):
        self._write_config("design", "design", "error")
        self._write_p("p-a", "edges: []\n")  # 辺なし → gap
        self._write_mod("mod-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("ERROR: must_link_to:", stdout)
        self.assertIn("p-a", stdout)
        self.assertIn("欠如", stdout)

    def test_warning_severity_gap_does_not_fail_exit(self):
        self._write_config("design", "design", "warning")
        self._write_p("p-a", "edges: []\n")
        self._write_mod("mod-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertIn("WARN: must_link_to:", stdout)
        self.assertNotIn("ERROR: must_link_to:", stdout)

    def test_satisfied_link_has_no_gap(self):
        self._write_config("design", "design", "error")
        self._write_p("p-a", 'edges:\n  - to: mod-a\n    ref_version: "0.1"\n')
        self._write_mod("mod-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("must_link_to:", stdout)

    def test_stage_below_activate_skips_rule(self):
        # current_stage=design < activate_stage=verification → 未発火（gap でも ERROR にしない）。
        self._write_config("design", "verification", "error")
        self._write_p("p-a", "edges: []\n")
        self._write_mod("mod-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("must_link_to:", stdout)

    def test_missing_current_stage_is_inactive(self):
        self._write_config(None, "design", "error")
        self._write_p("p-a", "edges: []\n")
        self._write_mod("mod-a")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("must_link_to:", stdout)

    def test_validate_function_returns_error_line(self):
        # 純関数の直接呼び出し（行整形の忠実性）。
        self._write_config("design", "design", "error")
        self._write_p("p-a", "edges: []\n")
        self._write_mod("mod-a")

        lines = validate.validate_must_link_to(self.root)

        self.assertTrue(any(m.startswith("ERROR: must_link_to:") and "p-a" in m for m in lines), lines)


class TestValidateMustBeLinkedFrom(unittest.TestCase):
    """Phase B (#163): validate_must_be_linked_from の applies_when・stage gating・severity。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()
        _write(self.repo / "tests/test_sample.py", "def test_a():\n    pass\n")

    def _write_config(self, current_stage: str, activate: str, severity: str) -> None:
        _write(
            self.root / "config.yml",
            f'current_stage: "{current_stage}"\n{_STAGES_LINE}'
            + "must_be_linked_from:\n"
            + f"  - {{ node: spec, source: [td], activate_stage: {activate}, severity: {severity}, applies_when: condition_present, reason: \"testable spec←td\" }}\n",
        )

    def _write_spec(self, name: str, condition: str | None) -> None:
        cond = f'condition: "{condition}"\n' if condition else ""
        y = self.root / f"nodes/02-what/spec/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n{cond}edges: []\n')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _write_td_to(self, name: str, target: str) -> None:
        y = self.root / f"nodes/04-verification/td/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  f'edges:\n  - to: {target}\n    ref_version: "0.1"\n')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_condition_present_node_without_incoming_is_error(self):
        self._write_config("verification", "verification", "error")
        self._write_spec("spec-cond", "normal")  # incoming td 無し → gap

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("ERROR: must_be_linked_from:", stdout)
        self.assertIn("spec-cond", stdout)

    def test_node_without_condition_is_not_targeted(self):
        self._write_config("verification", "verification", "error")
        self._write_spec("spec-plain", None)  # 傘（condition 無）→ 対象外

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("must_be_linked_from:", stdout)

    def test_incoming_source_satisfies(self):
        self._write_config("verification", "verification", "error")
        self._write_spec("spec-cond", "normal")
        self._write_td_to("td-a", "spec-cond")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("must_be_linked_from:", stdout)

    def test_stage_below_activate_skips_rule(self):
        self._write_config("design", "verification", "error")
        self._write_spec("spec-cond", "normal")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("must_be_linked_from:", stdout)


class TestSourceKindVocabulary(unittest.TestCase):
    """Phase B (#163): source.kind 語彙拡張 {module, class, function, method, file}。"""

    def _sidecar(self, kind: str) -> list[str]:
        data = {
            "title": "x",
            "version": "0.1.0",
            "labels": [],
            "scheduled": "sprint-1",
            "edges": [],
            "source.file": "pkg/mod.py",
            "source.qualname": "x",
            "source.kind": kind,
        }
        return validate.validate_sidecar(data)

    def test_module_kind_accepted(self):
        self.assertFalse([m for m in self._sidecar("module") if "source.kind 不正" in m])

    def test_file_kind_accepted(self):
        self.assertFalse([m for m in self._sidecar("file") if "source.kind 不正" in m])

    def test_existing_kinds_still_accepted(self):
        for k in ("function", "class", "method"):
            self.assertFalse([m for m in self._sidecar(k) if "source.kind 不正" in m], k)

    def test_invalid_kind_still_error(self):
        self.assertTrue(any("source.kind 不正" in m for m in self._sidecar("banana")))


if __name__ == "__main__":
    unittest.main()
