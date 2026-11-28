"""Exercise AC extraction, trusted activation, ingest and owner write together."""
import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte import ac_owner_update, handoff_header, model, owner_cli, paths, review_envelope, reviewer_cli
from karte.ac_snapshot import digest, from_issue_body
from karte.active_pointer import read_active
from karte.errors import KarteUsageError
from tests.unit.test_karte_ac_comment_blocks import comment_cases

OPTIONS = dict(run_id="run-html", target_key="pr-846", phase="implementation",
               snapshot_oid="a" * 40, input_digest="b" * 64)
ORIGIN = dict(host="github.com", repository="owner/project")
HEAD = "## Acceptance criteria\n"
FIRST = HEAD + "- [ ] AC1\n"
LAST = "\n- [ ] AC2\n"


def cases():
    yield from comment_cases()
    for fake in ("- [ ] example only", "## Notes"):
        for prefix, opening, closing in (
            (FIRST + "\n", "<div>", "</div>"),
            (HEAD, "<span>", "</span>"),
            (FIRST + "\n### Example\n", "<span>", "</span>"),
            ("Acceptance criteria\n===================\n", "<span>", "</span>"),
            (FIRST + "\n### Example\n", "  <div>", "  </div>"),
            (FIRST + "\n~~~\ncode\n~~~\n", "  <div>", "  </div>"),
            (FIRST + "\n<pre>\nexample\n</pre>\n", "<span>", "</span>"),
            (FIRST + "\n<div>\nexample\n</div>\n\n", "  <div>", "  </div>"),
            (FIRST, "<!--", "-->"),
        ):
            body = prefix + opening + "\n" + fake + "\n" + closing + "\n" + LAST
            yield body, ["AC1", "AC2"] if "AC1" in prefix else ["AC2"], "AC2"
    yield "<!--\n## Acceptance criteria\n- [ ] example only\n-->\n\n" + FIRST + "- [ ] AC2\n", ["AC1", "AC2"], "AC2"
    yield FIRST + "  <div>\n  example\n  </div>\n- [ ] AC2\n", ["AC1", "AC2"], "AC2"
    yield FIRST + "  <pre>\n  example\n- [ ] AC2\n", ["AC1", "AC2"], "AC2"
    yield HEAD + "- [ ] AC1 " + chr(96) + "literal\n  foo <!--\n  bar" + chr(96) + "\n- [ ] AC2\n", ["AC1", "AC2"], "AC2"
    yield HEAD + "- [ ] AC1 unmatched " + chr(96) + "\n- [x] AC2 " + chr(96) + "code" + chr(96) + "\n", ["AC1", "AC2"], "AC2"
    yield HEAD + "- [ ] AC1 \\<!-- must authenticate -->\n- [x] AC2\n", ["AC1", "AC2"], "must authenticate"


class HtmlOwnerFlowTest(unittest.TestCase):
    def call(self, handler, root, **fields):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return handler(argparse.Namespace(repo_root=str(root), **fields))

    def ingest(self, root, criteria, count):
        report = ("## Review Summary\n\n### Summary\nfinding_count: 0\n"
                  f"ac_count: {count}\nac_snapshot_digest: {digest(criteria)}\n")
        for index in range(1, count + 1):
            report += f"\n### AC {index}\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
        report += "<!-- review-complete -->\n"
        handoff = root / "tmp" / "_handoff" / f"pr-reviewer--html-{count}.md"
        expected = review_envelope.expected_of(issue=801, **OPTIONS)
        handoff.write_text(handoff_header.render_header(1, expected) + "\n" + report, encoding="utf-8")
        return self.call(reviewer_cli.cmd_ingest_reviewer, root, source=str(handoff), issue=None, round=None)

    def test_regressions_through_real_cli_and_mock_remote(self):
        for body, expected, drift in cases():
            with self.subTest(body=body), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "tmp" / "_handoff").mkdir(parents=True)
                source = root / "tmp" / "issue.md"
                source.write_text(body, encoding="utf-8")
                criteria = from_issue_body(body)
                self.assertEqual([i.text.split()[0] for i in criteria if i.checked is not None], expected)
                with patch("karte.ac_repository.checkout_origin", return_value=ORIGIN):
                    self.assertEqual(0, self.call(owner_cli.cmd_activate, root, issue="801",
                                     ac_snapshot_file=str(source), repair_declared_scope=False, **OPTIONS))
                    frozen = read_active(root, required=True)["ac_snapshot"]
                    self.assertNotEqual(0, self.ingest(root, criteria, len(criteria) - 1))
                    self.assertEqual(0, self.ingest(root, criteria, len(criteria)))
                    record = model.parse(paths.read_text(paths.karte_path(801, root))).review_rounds[0]
                    self.assertEqual(frozen["source"], record.ac_source)
                    calls, live = [], [body.replace(drift, "changed")]
                    def remote(host, repository, issue, *, new_body=None):
                        self.assertEqual((host, repository, issue), ("github.com", "owner/project", 801))
                        calls.append(new_body is not None)
                        if new_body is not None:
                            live[0] = new_body
                        return live[0]
                    with self.assertRaises(KarteUsageError):
                        ac_owner_update.perform(root, 801, 1, frozen["source"], ORIGIN["repository"], remote=remote)
                    self.assertNotIn(True, calls)
                    calls.clear()
                    live[0] = body
                    changed = ac_owner_update.perform(root, 801, 1, frozen["source"], ORIGIN["repository"], remote=remote)
                    self.assertEqual(changed, [n for n, ac in enumerate(criteria, 1) if ac.checked is False])
                    self.assertEqual(calls, [False, False, True, False])
                    self.assertEqual(live[0], body.replace("[ ] AC1", "[x] AC1").replace("[ ] AC2", "[x] AC2"))
