import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, '/workspace/review-system')
import httpx2
from typesafe_sdk import AsyncTypeSafeClient
from jev_hooks.config import load_config
from jev_hooks.evaluator import JevEvaluator, MockEvaluator
from jev_hooks.runner import run_event
from jev_hooks.semantic_eval import main as semantic_main

class SensitiveInputPrivacyRepro(unittest.TestCase):
    def exercise(self, tool, changes):
        captured = []
        def handler(request):
            payload = json.loads(request.content)
            captured.append(payload)
            answers = {key: {'type': 'choice', 'choice': 'yes', 'confidence': 1.,
                       'probabilities': {'yes': 1., 'no': 0., 'unknown': 0.}}
                       for key in payload['questions']}
            return httpx2.Response(200, json={'model': 'jev-1.13.0', 'answers': answers,
                                        'usage': {'input_tokens': 1, 'output_tokens': 1}})
        def factory(**kwargs):
            return AsyncTypeSafeClient(**kwargs, transport=httpx2.MockTransport(handler))
        canary = 'opaque849726_DATABASE_VALUE'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'SKILL.md').write_text('Verify before editing deployment configuration.')
            definition = {'id': 'privacy', 'skill_path': 'SKILL.md', 'steps': [
                {'id': 'verify', 'kind': 'required', 'evidence': {'tool': 'Bash', 'input': {'command': 'verify'}}, 'watch': []}],
                'operations': [{'tool': tool, 'semantic': 'Edit deployment configuration',
                                'input': {'file_path': '.env'}, 'requires': ['verify']}], 'stop_requires': ['verify']}
            (root / 'definition.json').write_text(json.dumps(definition))
            config = load_config()
            config.update(mode='enforce', evaluator='jev', retries=0, state_dir=str(root / 'state'),
                          skill_definitions=[str(root / 'definition.json')])
            base = {'cwd': directory, 'session_id': 'privacy-repro'}
            with patch.dict(os.environ, {'TYPESAFE_API_KEY': 'fixture-auth-key'}, clear=True):
                run_event(dict(base, hook_event_name='PostToolUse', tool_name='Read', tool_use_id='read',
                    tool_input={'file_path': str(root / 'SKILL.md')}, tool_response={'content': 'verified'}),
                    config, MockEvaluator())
                inputs = {'file_path': str(root / '.env'), **{key: value.replace('CANARY', canary)
                                                              for key, value in changes.items()}}
                event = dict(base, hook_event_name='PreToolUse', tool_name=tool, tool_use_id='sensitive-write', tool_input=inputs)
                with patch('typesafe_sdk.AsyncTypeSafeClient', factory):
                    decision = run_event(event, config, JevEvaluator(config))
                    self.assertTrue(decision)
                    evidence = {'current_tool_input': inputs, 'hook_event_name': 'PreToolUse',
                        'skill_context': {'current_tool': {'name': tool, 'input': inputs}, 'role': 'operation'}}
                    (root / 'config.json').write_text(json.dumps(config))
                    (root / 'corpus.jsonl').write_text(json.dumps({'id': 'opaque', 'question': 'r4_operation_relevant',
                                                                 'evidence': evidence, 'expected': True}) + '\n')
                    argv = ['semantic_eval', '--config', str(root / 'config.json'), '--corpus', str(root / 'corpus.jsonl')]
                    with patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()):
                        semantic_main()
        self.assertEqual(len(captured), 2)
        for index, payload in enumerate(captured):
            route = ('run_event/R4', 'semantic_eval/R4')[index]
            inputs = payload['state']['current_tool_input']
            nested = payload['state']['skill_context']['current_tool']['input']
            print(json.dumps({'route': route, 'tool': tool, 'questions': list(payload['questions']),
                              'current_input_canary': canary in json.dumps(inputs),
                              'skill_context_input_canary': canary in json.dumps(nested)}))
            with self.subTest(route=route, tool=tool):
                self.assertNotIn(canary, json.dumps(payload))
    def test_write_env_body(self):
        self.exercise('Write', {'content': 'DB_URI=postgresql://local:CANARY@db.local/app'})
    def test_edit_env_body(self):
        self.exercise('Edit', {'old_string': 'DB_URI=old-CANARY', 'new_string': 'DB_URI=new-CANARY'})

if __name__ == '__main__':
    unittest.main(verbosity=2)
