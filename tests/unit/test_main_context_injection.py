"""主文脈専用の規範（`.claude/main-context/*.md`）の配送経路の検査。全文は SessionStart の
`orchestrator-context.sh` が委譲ルールに続けて注入し、毎ターンの `inject-governance.sh` は写し
（`governance-directives.md`・項12が要約）だけを注入する。読込失敗は当該ファイルだけを飛ばす（fail-open）。"""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS = REPO_ROOT / ".claude" / "hooks"
MAIN_CONTEXT_DIR = REPO_ROOT / ".claude" / "main-context"
DELEGATION_RULES = "orchestrator-context/orchestrator-task-delegation-rules.md"
DELIVERY_COPY = HOOKS / "governance-directives.md"
HISTORY_RE = re.compile(r"(?:Issue|PR)\s*#\d+|\d{4}-\d{2}-\d{2}")


def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()


def run_hook(root, name):
    return subprocess.run(
        ["bash", str(root / ".claude" / "hooks" / name)],
        input="{}", text=True, capture_output=True, check=False,
    )


def context_of(completed):
    return json.loads(completed.stdout)["hookSpecificOutput"]["additionalContext"]


def copy_hooks(root):
    hooks = root / ".claude" / "hooks"
    (hooks / "orchestrator-context").mkdir(parents=True)
    for name in ("orchestrator-context.sh", DELEGATION_RULES):
        (hooks / name).write_bytes((HOOKS / name).read_bytes())


def main_context_bodies():
    paths = sorted(MAIN_CONTEXT_DIR.glob("*.md"))
    return {p.name: strip_comments(p.read_text(encoding="utf-8")) for p in paths}


def delegation_rules():
    return (HOOKS / DELEGATION_RULES).read_text(encoding="utf-8").strip()


class TestSessionStartDeliversFullText(unittest.TestCase):
    def test_delegation_rules_then_every_main_context_body(self):
        completed = run_hook(REPO_ROOT, "orchestrator-context.sh")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        context = context_of(completed)
        self.assertTrue(context.startswith(delegation_rules()))
        self.assertTrue(main_context_bodies(), f"{MAIN_CONTEXT_DIR} に規範が無い")
        for name, body in main_context_bodies().items():
            self.assertIn(body, context, f"{name} の全文が SessionStart の注入に含まれない")

    def test_invalid_utf8_file_is_skipped_and_the_rest_is_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_hooks(root)
            main_context = root / ".claude" / "main-context"
            main_context.mkdir()
            (main_context / "01-broken.md").write_bytes(b"\xff\xfe not utf-8 \x80")
            (main_context / "02-valid.md").write_text("## 有効な規範\n本文", encoding="utf-8")
            completed = run_hook(root, "orchestrator-context.sh")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            context = context_of(completed)
            self.assertIn("Orchestrator Task Delegation Rules", context)
            self.assertIn("## 有効な規範\n本文", context)
            self.assertIn("[orchestrator-context]", completed.stderr)
            self.assertIn("01-broken.md", completed.stderr)

    def test_missing_main_context_directory_still_injects_delegation_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_hooks(Path(tmp))
            completed = run_hook(Path(tmp), "orchestrator-context.sh")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(context_of(completed), delegation_rules())


class TestPerTurnInjectionCarriesOnlyTheCopy(unittest.TestCase):
    def test_per_turn_context_is_the_copy_without_main_context_bodies(self):
        completed = run_hook(REPO_ROOT, "inject-governance.sh")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        context = context_of(completed)
        self.assertEqual(context, strip_comments(DELIVERY_COPY.read_text(encoding="utf-8")))
        for name, body in main_context_bodies().items():
            self.assertNotIn(body, context, f"{name} の全文を毎ターン注入している")

    def test_injected_text_carries_no_history(self):
        """検査するのは Issue/PR 番号と ISO 日付だけ。決定 ID・「〜で導入」等の経緯は検出しない。"""
        texts = {"governance-directives.md": strip_comments(DELIVERY_COPY.read_text(encoding="utf-8"))}
        texts.update(main_context_bodies())
        for name, text in texts.items():
            match = HISTORY_RE.search(text)
            self.assertIsNone(match, f"{name} に Issue/PR 番号か ISO 日付がある（rationale へ移す・検査はこの2種のみ）: {match}")
