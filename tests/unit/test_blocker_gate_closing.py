import unittest

from blocker_gate.closing import (
    ClosingReferenceError,
    CommitMessageSource,
    DELIVERED_MESSAGE_FORMATTER_VERSION,
    SQUASH_COMMIT_MESSAGES_EVIDENCE,
    SQUASH_COMMIT_MESSAGES_EVIDENCE_FINGERPRINT,
    build_delivered_messages,
    parse_closing_references,
)


def commit(oid, message, *, tree="1" * 40, parent="0" * 40, parent_tree="2" * 40):
    return CommitMessageSource(oid, message, tree, (parent,), parent_tree)


class ClosingReferenceTests(unittest.TestCase):
    def test_parser_canonicalizes_local_qualified_and_url_references(self):
        actual = parse_closing_references(
            [
                "Fixes: #7, closes : Example/Repo#8.\nResolved:https://github.com/example/repo/issues/9!"
            ],
            "example/repo",
        )
        self.assertEqual(actual, ("example/repo#7", "example/repo#8", "example/repo#9"))

    def test_parser_ignores_natural_language_but_rejects_malformed_and_cross_repo(self):
        self.assertEqual(parse_closing_references(["fixes performance"], "example/repo"), ())
        for message, reason in (
            ("fixes #0", "CLOSING_KEYWORD_PARSE"),
            ("closes: other/repo#1", "CROSS_REPOSITORY_UNSUPPORTED"),
        ):
            with self.subTest(message=message), self.assertRaises(ClosingReferenceError) as caught:
                parse_closing_references([message], "example/repo")
            self.assertEqual(caught.exception.reason, reason)


class DeliveredMessageTests(unittest.TestCase):
    def test_merge_includes_source_commits_and_reconstructed_merge_commit(self):
        bundle = build_delivered_messages(
            repository="example/repo",
            number=50,
            merge_method="merge",
            pr_title="PR title",
            pr_body="PR body",
            head_label="owner:topic",
            commits=[commit("a" * 40, "fixes: #7")],
            settings={"merge_commit_title": "MERGE_MESSAGE", "merge_commit_message": "PR_BODY"},
            commit_title=None,
            commit_message=None,
        )
        self.assertEqual(
            bundle.messages,
            ("fixes: #7", "Merge pull request #50 from owner:topic\n\nPR body"),
        )
        self.assertTrue(bundle.message_source_fingerprint.startswith("sha256:"))
        self.assertTrue(bundle.delivered_message_fingerprint.startswith("sha256:"))

    def test_rebase_drops_originally_empty_commit_and_rejects_override(self):
        kept = commit("a" * 40, "fixes: #7", tree="3" * 40, parent_tree="2" * 40)
        empty = commit("b" * 40, "fixes: #8", tree="4" * 40, parent_tree="4" * 40)
        bundle = build_delivered_messages(
            repository="example/repo", number=50, merge_method="rebase",
            pr_title="p", pr_body="", head_label="o:h", commits=[kept, empty],
            settings=None, commit_title=None, commit_message=None,
        )
        self.assertEqual(bundle.messages, ("fixes: #7",))
        with self.assertRaises(ClosingReferenceError) as caught:
            build_delivered_messages(
                repository="example/repo", number=50, merge_method="rebase",
                pr_title="p", pr_body="", head_label="o:h", commits=[kept],
                settings=None, commit_title="override", commit_message=None,
            )
        self.assertEqual(caught.exception.reason, "MERGE_OVERRIDE_AMBIGUOUS")

    def test_squash_uses_only_the_verified_effective_squash_message(self):
        source = commit("a" * 40, "fixes: #7")
        bundle = build_delivered_messages(
            repository="example/repo", number=50, merge_method="squash",
            pr_title="title", pr_body="no closing reference", head_label="o:h",
            commits=[source],
            settings={"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY"},
            commit_title=None, commit_message=None,
        )
        self.assertEqual(parse_closing_references(bundle.messages, "example/repo"), ())
        ambiguous_sources = [
            source,
            commit("b" * 40, "Unicode 本文 🧪\n\nCloses: #7"),
            commit("c" * 40, "subject\n\nbody: with colon"),
        ]
        with self.assertRaises(ClosingReferenceError) as caught:
            build_delivered_messages(
                repository="example/repo", number=50, merge_method="squash",
                pr_title="title", pr_body="", head_label="o:h",
                commits=ambiguous_sources,
                settings={
                    "squash_merge_commit_title": "PR_TITLE",
                    "squash_merge_commit_message": "COMMIT_MESSAGES",
                },
                commit_title=None, commit_message=None,
            )
        self.assertEqual(caught.exception.reason, "MERGE_MESSAGE_AMBIGUOUS")

        exact_override = build_delivered_messages(
            repository="example/repo", number=50, merge_method="squash",
            pr_title="title", pr_body="", head_label="o:h",
            commits=ambiguous_sources,
            settings={
                "squash_merge_commit_title": "PR_TITLE",
                "squash_merge_commit_message": "COMMIT_MESSAGES",
            },
            commit_title=None,
            commit_message="Unicode 本文 🧪\n\nCloses: #7\nbody: with colon",
        )
        self.assertEqual(
            parse_closing_references(exact_override.messages, "example/repo"),
            ("example/repo#7",),
        )
        self.assertEqual(DELIVERED_MESSAGE_FORMATTER_VERSION, "github-delivered-message/2")
        self.assertFalse(SQUASH_COMMIT_MESSAGES_EVIDENCE["verified"])
        self.assertRegex(
            SQUASH_COMMIT_MESSAGES_EVIDENCE_FINGERPRINT,
            r"^sha256:[0-9a-f]{64}$",
        )


if __name__ == "__main__":
    unittest.main()
