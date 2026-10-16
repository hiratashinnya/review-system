"""CLI の書込み境界と pending の即時通知。"""
import json
import tomllib
from pathlib import Path
from .github import create_issue, issue_body
from .model import new_id, normalize
from .references import validate_assets, validate_references
from .store import issue_lock, load, write


def notify_pending(root):
    pending = [data["id"] for data, _ in load(root)
               if data["decision"]["tracking_status"] == "pending"]
    if pending:
        print(json.dumps({"systemMessage": "ADR: Issue未起票: " + ", ".join(pending)},
                         ensure_ascii=False))


def new_entry(args):
    data = tomllib.loads(Path(args.draft).read_text(encoding="utf-8"))
    data.setdefault("id", new_id(data))
    data = normalize(data)
    validate_assets(data, args.repo)
    validate_references(data, args.root, args.repo)
    path = write(args.root, data)
    print(path)
    notify_pending(args.root)


def file_issue(args):
    with issue_lock(args.root):
        _file_issue_locked(args)


def _file_issue_locked(args):
    matches = [(data, path) for data, path in load(args.root) if data["id"] == args.id]
    if not matches:
        raise ValueError("ADR が存在しない")
    data, path = matches[0]
    if data["decision"]["tracking_status"] != "pending":
        raise ValueError("file-issue は pending のみ対象")
    if args.create and args.issue:
        raise ValueError("--create と --issue は併用できない")
    if not args.create and args.issue is None:
        print(issue_body(data))
        return
    if args.issue is not None:
        if args.issue <= 0:
            raise ValueError("Issue番号は正の整数")
        number = args.issue
    else:
        number, url = create_issue(data, args.repo)
        print(url, flush=True)
    data["decision"].update(tracking_status="filed", tracking_issue=number)
    try:
        write(args.root, data, replace=True)
    except Exception as exc:
        raise ValueError(f"Issue #{number} は存在。--issue {number} で復旧: {exc}") from exc
    notify_pending(args.root)
