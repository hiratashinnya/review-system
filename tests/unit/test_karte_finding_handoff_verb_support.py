"""オフライン handoff verb 試験の一時台帳と GitHub。"""
import contextlib
import io
import json
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from karte import model, paths
from karte.handoff_cli import register
from karte.parser_core import build_parser
from tests.unit.karte_support import RootedCase, writer_lock_is_held
from tests.unit.test_karte_finding_handoff_gh import comment, issue
from tests.unit.test_karte_finding_handoff_predicate import verified_item


class VerbCase(RootedCase):
    def setUp(self):
        super().setUp()
        item = verified_item()
        item.handoff = None
        self.path = paths.karte_path(7, self.root, create_dir=True)
        self.save(item)
        self.comments, self.posts = [], 0
        self.issue = issue() | {"html_url": "https://github.com/Owner/Repo/issues/9",
                                "repository_url": "https://api.github.com/repos/Owner/Repo"}
        self.failure = None
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for module in ("post", "recheck"):
            patcher = mock.patch(f"karte.verb_handoff_{module}.timestamp", return_value=self.now.isoformat())
            patcher.start()
            self.addCleanup(patcher.stop)
        self.patcher = mock.patch("subprocess.run", side_effect=self.run_process)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def save(self, item):
        self.path.write_text(model.dumps(model.Karte(7, [item])), encoding="utf-8")

    def run_process(self, argv, **kwargs):
        self.assertFalse(writer_lock_is_held(self.root))
        if argv[0] == "git":
            return SimpleNamespace(stdout="https://github.com/Owner/Repo.git\n")
        if self.failure:
            self.failure(argv)
        endpoint = argv[3]
        if endpoint == "user":
            value = {"login": "me"}
        elif "/issues/comments/" in endpoint:
            if not self.comments:
                raise subprocess.CalledProcessError(1, argv, stderr="HTTP 404")
            value = self.comments[0]
        elif "/comments?" in endpoint:
            value = self.comments
        elif endpoint.endswith("/comments"):
            self.posts += 1
            value = comment() | {"body": argv[-1][5:],
                "html_url": "https://github.com/Owner/Repo/issues/9#issuecomment-1",
                "issue_url": "https://api.github.com/repos/Owner/Repo/issues/9"}
            self.comments.append(value)
        else:
            value = self.issue
        return SimpleNamespace(stdout="HTTP/2 200 OK\n\n" + json.dumps(value))

    def call(self, verb, *flags):
        parser = build_parser((register,))
        args = parser.parse_args([verb, "--issue", "7", *flags])
        args.repo_root = str(self.root)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = args.func(args)
        return result, out.getvalue(), err.getvalue()

    def flags(self):
        return ["--finding", "F-7-01", "--to", "#9", "--agent", "Codex"]

    def token(self):
        code, output, err = self.call("handoff-preview", *self.flags())
        self.assertEqual(code, 0, err)
        return output.split("確認トークン: ")[-1].strip().splitlines()[0]

    def post(self):
        return self.call("handoff-post", *self.flags(), "--confirm", self.token())
