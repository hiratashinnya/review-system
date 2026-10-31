"""``build_parser`` / ``main`` の ``extra_registrars``：別モジュールの verb を足せること。"""

import unittest

from karte import cli


def _register_probe(subparsers, add_issue):
    probe = subparsers.add_parser("probe", help="テスト用の verb")
    add_issue(probe)
    probe.set_defaults(func=lambda args: 42)


class TestExtraRegistrars(unittest.TestCase):
    def test_registered_verb_appears_in_the_parser(self):
        parser = cli.build_parser((_register_probe,))
        args = parser.parse_args(["probe", "--issue", "7"])
        self.assertEqual("7", args.issue)
        self.assertEqual(42, args.func(args))

    def test_main_dispatches_to_a_registered_verb(self):
        self.assertEqual(42, cli.main(["probe"], extra_registrars=(_register_probe,)))

    def test_verb_is_absent_without_the_registrar(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["probe"])

    def test_existing_verbs_are_unchanged_by_registrars(self):
        verbs = {"ingest-review", "render", "append", "close-attempt", "check", "status"}
        parser = cli.build_parser((_register_probe,))
        for verb in verbs:
            with self.subTest(verb=verb):
                self.assertTrue(parser.parse_args([verb, "--issue", "1"] + (
                    ["--from", "x"] if verb == "ingest-review" else []
                ) + (
                    ["--finding-ids", "F-1-01", "--root-cause", "x", "--change-kind", "logic",
                     "--targets", "a.py::f"] if verb == "append" else []
                ) + (["--outcome", "fixed"] if verb == "close-attempt" else [])).func)


if __name__ == "__main__":
    unittest.main()
