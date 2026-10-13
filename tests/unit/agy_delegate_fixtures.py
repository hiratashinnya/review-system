"""実測型に沿う合成データと fake agy。実測 JSON 自体は fixtures に置く。"""

import json
import tempfile
from pathlib import Path

from agy_delegate.permissions import expected_rules
from agy_delegate.types import Request

FAKE = '''#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv[1:]
if args == ['--version']:
    print('1.3.3')
    sys.exit(0)
data = json.loads(args[args.index('-p') + 1])
pathlib.Path('launched.json').write_text(json.dumps(args))
with pathlib.Path('launch-count.txt').open('a') as log:
    log.write('launch\\n')
if 'image' in data:
    image = pathlib.Path(data['image'])
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(data.get('image_bytes', 'new').encode())
print(data.get('stdout', json.dumps(data.get('output', {}))))
print(data.get('stderr', ''), file=sys.stderr)
sys.exit(data.get('exit', 0))
'''


def synthetic_success(identity="conversation-1", response="result"):
    return dict(status="SUCCESS", denied_actions=[], conversation_id=identity, response=response,
                duration_seconds=1.0, num_turns=1, usage={name: 0 for name in
                ("input_tokens", "output_tokens", "thinking_tokens", "cache_read_tokens", "total_tokens")})


class FakeWorkspace:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "空白 日本語"
        self.workspace.mkdir()
        self.executable = self.workspace / "fake-agy"
        self.executable.write_text(FAKE, encoding="utf-8")
        self.executable.chmod(0o700)
        self.settings = self.workspace / "settings.json"
        self.settings.write_text(json.dumps({"permissions": expected_rules(self.workspace)}))
        self.brain = self.workspace / "brain"
        self.brain.mkdir()

    def request(self, output=None, **kwargs):
        payload = {"output": output or synthetic_success()}
        kwargs.setdefault("caller_state", "ready")
        return Request(self.workspace, self.settings, self.executable,
                       json.dumps(payload), print_timeout=1, **kwargs)

    def close(self):
        self.temp.cleanup()


def synthetic_runtime(request):
    return []


def run_synthetic(request):
    from unittest.mock import patch
    from agy_delegate.runner import run
    with patch("agy_delegate.runner.verify_runtime", synthetic_runtime):
        return run(request)
