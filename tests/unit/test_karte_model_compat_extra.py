"""分割前に実測した公開面と境界挙動を検証する。"""

import ast
import importlib
import json
import unittest
from pathlib import Path

from karte import model
from tests.unit.test_karte_model_compat import VALID, karte_extras, mutations

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((ROOT / 'tests/fixtures/karte/model_compat_extra_golden.json').read_text())
REQUIRED_NAMES = {
    'block_fields': '_optional_enum _require_enum _require_int_list _require_nonempty',
    'block_parser': 'Block parse_blocks',
    'disposition': 'DISPOSITION_ALL_KEYS DISPOSITION_REQUIRED_KEYS Disposition parse_disposition',
    'field_validators': 'validate_change_kind validate_finding_ids validate_slug validate_targets',
    'finding_id': 'format_finding_id parse_finding_id',
    'format_error': 'KarteFormatError',
    'harm_detail_lint': 'DISPOSITION_TERMS HARM_DETAIL_FORBIDDEN_TERMS PROCESS_TERMS check_harm_detail find_harm_detail_terms normalize_for_term_match',
    'int_args': 'matched_int require_ascii_int',
    'review_block': 'DISTINCT_FROM_KEY',
    'review_finding': 'ReviewFinding',
    'review_report': 'parse_review',
    'value_codec': 'check_list check_scalar format_value normalize_locus parse_value',
    'vocabulary': 'ATTEMPT_TITLE_RE CHANGE_KINDS CLEARING_DISPOSITIONS CLEARING_HARM DEFAULT_SCOPE DEFERRED_TO_RE DISPOSITIONS DOC_HEADER_RE FINDING_ID_RE FINDING_STATUSES FORBIDDEN_LIST_ITEM_CHARS FORBIDDEN_VALUE_CHARS HARM_LEVELS KEY_RE NEW_FINDING_TITLES OUTCOMES RESULT_TITLE_RE SCOPES SECTION_ATTEMPTS SECTION_FINDINGS SEVERITIES SLUG_RE FORMAT_VERSION',
    'attempt_record': 'Attempt Result',
    'finding_record': 'Finding',
    'karte_record': 'Karte new_karte',
    'finding_dedup': 'normalize_text shingles _jaccard is_same_finding SHINGLE_SIZE DUPLICATE_SIMILARITY_THRESHOLD',
    'block_records': '_finding_from_block _attempt_from_block _result_from_block',
    'karte_parse': 'parse',
    'karte_render': '_emit render_finding render_attempt render_result dumps',
}
NEW_MODULES = ('attempt_record', 'finding_record', 'karte_record', 'finding_dedup',
               'block_records', 'karte_parse', 'karte_render')


class TestModelCompatibilityExtra(unittest.TestCase):
    def test_required_names_are_identical_to_source_objects(self):
        self.assertEqual(sum(len(names.split()) for names in REQUIRED_NAMES.values()), 76)
        for module_name, names in REQUIRED_NAMES.items():
            module = importlib.import_module('karte.' + module_name)
            for name in names.split():
                with self.subTest(name=name):
                    self.assertIs(getattr(model, name), getattr(module, name.lstrip('_') if module_name == 'block_fields' else name))
        self.assertEqual((model.FORMAT_VERSION, model.SHINGLE_SIZE, model.DUPLICATE_SIMILARITY_THRESHOLD), (1, 2, 0.6))

    def test_parse_roundtrip_for_all_successful_inputs(self):
        cases = [('base', VALID), *karte_extras()]
        cases.extend((name, '\n'.join(lines)) for name, lines in mutations(VALID))
        accepted = 0
        exceptions = set()
        for name, text in cases:
            try:
                parsed = model.parse(text)
            except model.KarteFormatError:
                continue
            with self.subTest(name=name):
                again = model.parse(model.dumps(parsed))
                if name in GOLDEN['roundtrip_exceptions']:
                    before = parsed.attempts[0].diagnosis if 'diagnosis' in name else parsed.results[0].note
                    after = again.attempts[0].diagnosis if 'diagnosis' in name else again.results[0].note
                    self.assertEqual({'before': before, 'after': after}, GOLDEN['roundtrip_exceptions'][name])
                    self.assertNotEqual(again, parsed)
                    exceptions.add(name)
                else:
                    self.assertEqual(again, parsed)
            accepted += 1
        self.assertGreater(accepted, 1)
        self.assertEqual(exceptions, set(GOLDEN['roundtrip_exceptions']))

    def test_dedup_boundaries(self):
        for value, expected in GOLDEN['normalize']:
            self.assertEqual(model.normalize_text(value), expected)
        for value, expected in GOLDEN['shingles']:
            self.assertEqual(model.shingles(value), frozenset(expected))
        for a, la, b, lb, expected in GOLDEN['same']:
            with self.subTest(a=a, b=b, la=la, lb=lb):
                self.assertEqual(model.is_same_finding(a, la, b, lb), expected)
        self.assertEqual(model._jaccard(model.shingles('abcd'), model.shingles('abcdef')), 0.6)
        self.assertEqual(model._jaccard(model.shingles('abcde'), model.shingles('abcdexy')), 2 / 3)

    def test_record_predicates(self):
        for harm, disposition, status, cleared, remediation, needs, rounds in GOLDEN['truth']:
            finding = model.Finding('F-1-01', harm=harm, disposition=disposition, status=status, rounds=[1, 2, 4])
            with self.subTest(harm=harm, disposition=disposition, status=status):
                self.assertEqual((finding.cleared_by_disposition, finding.needs_remediation, finding.needs_disposition, finding.max_consecutive_rounds()), (cleared, remediation, needs, rounds))
        for rounds, expected in GOLDEN['rounds']:
            self.assertEqual(model.Finding('F-1-01', rounds=rounds).max_consecutive_rounds(), expected)

    def test_render_records(self):
        finding = model.Finding('F-1-02', locus=['a', 'b'], rounds=[1, 2], resolved_round=3, summary='要約')
        records = {'finding_empty': model.render_finding(model.Finding('F-1-01')),
                   'finding_full': model.render_finding(finding),
                   'attempt': model.render_attempt(model.Attempt(1, 2, [], '', '', [], '')),
                   'result': model.render_result(model.Result(1, [], [], '', ''))}
        self.assertEqual(records, GOLDEN['render'])

    def test_import_direction(self):
        entry = ast.parse((ROOT / 'karte/model.py').read_text())
        imports = {node.module for node in ast.walk(entry) if isinstance(node, ast.ImportFrom) and node.level == 1}
        self.assertTrue(set(NEW_MODULES) <= imports)
        for name in NEW_MODULES:
            tree = ast.parse((ROOT / f'karte/{name}.py').read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(x.name == 'karte.model' or x.name.startswith('karte.model.') for x in node.names), name)
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(node.module in ('karte.model', 'model') or
                                     ((node.level == 1 and node.module is None or node.module == 'karte') and any(x.name == 'model' for x in node.names)), name)
