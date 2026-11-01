"""hook 起動口テストの共通部品：登録コマンドの読取りと、空白を含む project root の実コピー。"""
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / ".claude" / "settings.json"


def registered_commands(tool, script_name):
    """`tool` に一致する PreToolUse matcher に登録された、`script_name` を起動するコマンド。"""
    hooks = json.loads(SETTINGS.read_text("utf-8"))["hooks"]["PreToolUse"]
    return [hook["command"] for entry in hooks if re.fullmatch(entry["matcher"], tool)
            for hook in entry["hooks"] if script_name in hook["command"]]


def copy_project_with_spaces(parent):
    """gate の起動に要る資産（Python package と hook 起動口）を空白入りの root へ実コピーする。"""
    root = Path(parent) / "project root with space"
    ignore = shutil.ignore_patterns("__pycache__")
    for package in ROOT.iterdir():
        if package.name != "tests" and (package / "__init__.py").is_file():
            shutil.copytree(package, root / package.name, ignore=ignore)
    shutil.copytree(ROOT / ".claude" / "hooks", root / ".claude" / "hooks", ignore=ignore)
    return root
