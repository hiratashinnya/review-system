"""Issue #797: scope の出所と未証明を区別する。"""
import unittest
from unittest import mock

from karte import cli, model, owner_cli, paths, scope_origin, scope_origin_store
from tests.unit.test_karte_reviewer_ingest import ReviewerIngestCase, _report


class TestScopeOrigin(ReviewerIngestCase):
    def _legacy_ingest(self, round_no, text):
        report = self.root / 'report.md'
        report.write_text(text, encoding='utf-8')
        return self._run(cli.cmd_ingest_review, issue=str(self.issue), round=str(round_no), source=str(report))

    def test_cancellation_main_then_reviewer_same_and_different(self):
        for scope in ('in', 'out'):
            with self.subTest(scope=scope):
                self.setUp()
                self.assertEqual(0, self._activate()[0])
                self.assertEqual(0, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
                self.assertEqual(0, self._legacy_ingest(1, _report(scope='in'))[0])
                fid = f'F-{self.issue}-01'
                self.assertEqual({fid: 'main'}, scope_origin.first_writers(self.issue, self.root))
                self.assertNotIn(fid, scope_origin.reviewer_declarations(self.issue, self.root))
                self.assertEqual(0, self._activate()[0])
                header = self._header(1) + '\n\n'
                path = self._handoff(header + _report(fid, scope=scope))
                self.assertEqual(0, self._run(__import__('karte.reviewer_cli', fromlist=['cmd_ingest_reviewer']).cmd_ingest_reviewer,
                                              issue=str(self.issue), round='1', source=path)[0])
                self.assertEqual('main', scope_origin.first_writers(self.issue, self.root)[fid])
                self.assertEqual([(1, scope)], scope_origin.reviewer_declarations(self.issue, self.root)[fid])

    def test_out_of_scope_and_cancelled_existing_status(self):
        self._activate()
        self._run(owner_cli.cmd_activate, issue=str(self.issue))
        self.assertEqual(0, self._legacy_ingest(1, _report(scope='out'))[0])
        self.assertEqual(0, self._legacy_ingest(2, _report('F-375-01', scope='out', status='resolved'))[0])
        self.assertEqual('resolved', self._finding('F-375-01').status)
        self.assertEqual({'F-375-01': 'main'}, scope_origin.first_writers(self.issue, self.root))
        self.assertEqual({}, scope_origin.reviewer_declarations(self.issue, self.root))

    def test_interrupted_write_is_unknown_and_existing_legacy_is_unknown(self):
        self._run(owner_cli.cmd_activate, issue=str(self.issue))
        with mock.patch.object(paths, 'write_text_atomic', side_effect=OSError('injected')):
            self.assertEqual(cli.EXIT_ERROR, self._legacy_ingest(1, _report())[0])
        self.assertEqual({'F-375-01': 'unknown'}, scope_origin.first_writers(self.issue, self.root))
        self.assertEqual(0, self._legacy_ingest(1, _report())[0])
        self.assertEqual('unknown', scope_origin.first_writers(self.issue, self.root)['F-375-01'])
        scope_origin_store.origin_path(self.issue, self.root).unlink()
        self.assertEqual(0, self._legacy_ingest(2, _report('F-375-01'))[0])
        self.assertEqual('unknown', scope_origin.first_writers(self.issue, self.root)['F-375-01'])

    def test_normal_reviewer_first_and_main_append(self):
        self._activate()
        self.assertEqual(0, self._ingest(_report())[0])
        other = _report('new', scope='out', summary='別件', locus='b.py::other')
        self.assertEqual(0, self._legacy_ingest(1, other)[0])
        self.assertEqual({'F-375-01': 'reviewer', 'F-375-02': 'main'},
                         scope_origin.first_writers(self.issue, self.root))
        self.assertNotIn('F-375-02', scope_origin.reviewer_declarations(self.issue, self.root))

    def test_failed_reviewer_write_does_not_attest_declaration(self):
        self._activate()
        with mock.patch.object(paths, 'write_text_atomic', side_effect=OSError('injected')):
            self.assertEqual(cli.EXIT_ERROR, self._ingest(_report(scope='out'))[0])
        self.assertEqual({}, scope_origin.reviewer_declarations(self.issue, self.root))
        self.assertEqual(0, self._ingest(_report(scope='in'))[0])
        self.assertEqual({'F-375-01': [(1, 'in')]}, scope_origin.reviewer_declarations(self.issue, self.root))

    def test_commit_failure_reports_saved_ledger_and_unknown_origin(self):
        self._run(owner_cli.cmd_activate, issue=str(self.issue))
        append = scope_origin_store.append_event
        def fail_commit(issue, root, event):
            if event['phase'] == 'committed':
                raise OSError('injected')
            return append(issue, root, event)
        with mock.patch.object(scope_origin_store, 'append_event', side_effect=fail_commit):
            code, out, err = self._legacy_ingest(1, _report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn('台帳は保存済み', err)
        self.assertEqual('in', self._finding('F-375-01').scope)
        self.assertEqual({'F-375-01': 'unknown'}, scope_origin.first_writers(self.issue, self.root))
        self.assertEqual(cli.EXIT_ERROR, self._legacy_ingest(1, _report())[0])
        self.assertEqual(0, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])

    def test_commit_path_and_format_errors_report_saved_ledger(self):
        for error in (paths.KartePathError('unsafe'), model.KarteFormatError('corrupt')):
            with self.subTest(error=type(error).__name__):
                self.setUp()
                self._run(owner_cli.cmd_activate, issue=str(self.issue))
                append = scope_origin_store.append_event
                def fail_commit(issue, root, event):
                    if event['phase'] == 'committed':
                        raise error
                    return append(issue, root, event)
                with mock.patch.object(scope_origin_store, 'append_event', side_effect=fail_commit):
                    code, _, err = self._legacy_ingest(1, _report())
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn('台帳は保存済み', err)
                self.assertIn(str(error), err)
                self.assertEqual('in', self._finding('F-375-01').scope)
                self.assertEqual({'F-375-01': 'unknown'}, scope_origin.first_writers(self.issue, self.root))


if __name__ == '__main__':
    unittest.main()
