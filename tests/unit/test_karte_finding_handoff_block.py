"""申し送り本文とハッシュのオフライン試験。"""

import unittest
from dataclasses import replace

from karte.finding_handoff_block import parse_block, render_block
from karte.finding_handoff_hash import content_hash
from karte.finding_record import Finding


def digest(item):
    return content_hash(item.id, item.harm, item.summary, item.locus, item.expected)


class HandoffBlockTest(unittest.TestCase):
    def setUp(self):
        self.item = Finding(id="F-7-01", harm="none", summary="要約", locus=["b.py", "a.py"],
                            expected="期待", evidence="根拠", recheck="確認")

    def test_round_trip_and_normalization(self):
        body = render_block(self.item, "Codex")
        parsed = parse_block(body)
        self.assertEqual(digest(self.item), parsed["content_hash"])
        self.assertEqual(digest(self.item), content_hash(parsed["finding"], parsed["harm"],
                         parsed["summary"], parsed["locus"], parsed["expected"]))
        windows = "\r\n" + "\r\n".join(line + "  " for line in body.splitlines()) + "\r\n"
        self.assertEqual(parsed, parse_block(windows))
        self.assertEqual(digest(self.item), digest(replace(self.item, locus=list(reversed(self.item.locus)))))

    def test_empty_locus(self):
        parsed = parse_block(render_block(replace(self.item, locus=[]), "Codex"))
        self.assertEqual([], parsed["locus"])

    def test_hash_fields(self):
        for field in ("evidence", "harm_detail", "recheck", "severity"):
            with self.subTest(field=field):
                self.assertEqual(digest(self.item), digest(replace(self.item, **{field: "変更"})))
        for field, value in (("id", "F-7-02"), ("harm", "real"), ("summary", "別"),
                             ("locus", ["別"]), ("expected", "別")):
            with self.subTest(field=field):
                self.assertNotEqual(digest(self.item), digest(replace(self.item, **{field: value})))

    def test_malformed(self):
        body = render_block(self.item, "Claude Code")
        for bad in (body + "\n" + body, body.replace("<!-- /karte-handoff -->", ""),
                    body.replace("- expected:", "- unexpected:"), body.replace("hash_version: 1", "hash_version: 2"),
                    body.replace("harm: none", "harm: unknown"), "prefix" + body):
            self.assertIsNone(parse_block(bad))
