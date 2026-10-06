"""Content-free replay keys include policy, watched inputs and conditions."""
import hashlib
import json
from pathlib import Path
from .fingerprints import fingerprint
from .policy import RULE_VERSION
from .questions import QUESTION_VERSION


def replay_key(event, config):
    identity = event.get("event_id") or event.get("tool_use_id")
    if not identity and event.get("hook_event_name") == "Stop" and "last_assistant_message" in event:
        try:
            history = Path(event.get("transcript_path", "")).read_bytes()
        except OSError:
            history = b""
        identity = [event["last_assistant_message"], event.get("stop_hook_active"),
                    hashlib.sha256(history).hexdigest()]
    if not identity:
        return None
    if event.get("hook_event_name") != "Stop":
        return hashlib.sha256(json.dumps([event.get("hook_event_name"), identity, RULE_VERSION, QUESTION_VERSION]).encode()).hexdigest()
    snapshots = []
    root = Path(event.get("cwd", "."))
    for filename in config["skill_definitions"]:
        definition = json.loads(Path(filename).read_text())
        conditions = [(root / step["when"]["path_exists"]).exists()
                      for step in definition["steps"] if step.get("when")]
        snapshots.append([definition, fingerprint(root,
            [pattern for step in definition["steps"] for pattern in step.get("watch", [])]), conditions])
    raw = json.dumps([event.get("hook_event_name"), identity, config, snapshots, RULE_VERSION, QUESTION_VERSION], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
