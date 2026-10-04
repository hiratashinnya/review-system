"""Content-free replay keys include policy and watched filesystem snapshots."""
import hashlib
import json
from pathlib import Path
from .fingerprints import fingerprint


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
        return hashlib.sha256(json.dumps([event.get("hook_event_name"), identity]).encode()).hexdigest()
    snapshots = []
    for filename in config["skill_definitions"]:
        definition = json.loads(Path(filename).read_text())
        snapshots.append([definition, fingerprint(event.get("cwd", "."),
            [pattern for step in definition["steps"] for pattern in step.get("watch", [])])])
    raw = json.dumps([event.get("hook_event_name"), identity, config, snapshots], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
