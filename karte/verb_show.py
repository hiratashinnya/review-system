"""verb_show の責務。詳細は .ai/rationale/karte-module-split.md。"""
import json
from . import active_pointer, karte_loader, pointer_completion
from .exit_codes import EXIT_OK
from .render_text import render_lines
from .status_payload import status_payload as _status_payload
from .status_text import status_lines
from .verb_boundary import fail_close

@fail_close(locked=False)
def cmd_render(args, repo_root) -> int:
    """カルテの現在状態を本文として出力する。"""
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    active = active_pointer.read_active(repo_root)
    round_no = pointer_completion.recorded_round(active, issue)
    print("\n".join(render_lines(issue, path, round_no, karte)))
    return EXIT_OK


@fail_close(locked=False)
def cmd_status(args, repo_root) -> int:
    """進捗判定を本文または JSON として出力する。"""
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    payload = _status_payload(karte)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    print("\n".join(status_lines(issue, path, payload)))
    return EXIT_OK
