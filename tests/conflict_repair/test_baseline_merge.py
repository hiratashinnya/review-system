import copy
import json
import unittest

from conflict_repair.baseline_merge import merge_baselines


def baseline():
    return {'schema_version': 2, 'source': 'test', 'module_lines': {},
            'comment_blocks': {}, 'mixed_class_files': {}}


def merge(old, main, head):
    return merge_baselines(*(json.dumps(item) for item in (old, main, head)))


class BaselineMergeTests(unittest.TestCase):
    def test_independent_deletes_and_updates_in_all_sections(self):
        old = baseline()
        old['module_lines'] = {'a.py': {'line_count': 101, 'sha256': 'a' * 64},
                               'b.py': {'line_count': 102, 'sha256': 'b' * 64}}
        old['comment_blocks'] = {'a.py|' + 'c' * 16: 1}
        old['mixed_class_files'] = {'c.py': {'data': ['D'], 'logic': ['L'], 'sha256': 'd' * 64}}
        main, head = copy.deepcopy(old), copy.deepcopy(old)
        del main['module_lines']['a.py']
        del head['module_lines']['b.py']
        main['comment_blocks']['a.py|' + 'c' * 16] = 2
        head['mixed_class_files']['c.py']['sha256'] = 'e' * 64
        result = merge(old, main, head)
        self.assertEqual(result['module_lines'], {})
        self.assertEqual(result['comment_blocks'], main['comment_blocks'])
        self.assertEqual(result['mixed_class_files'], head['mixed_class_files'])

    def test_same_change_and_conflicting_changes(self):
        old = baseline()
        main, head = copy.deepcopy(old), copy.deepcopy(old)
        key = 'x.py|' + 'a' * 16
        main['comment_blocks'][key] = head['comment_blocks'][key] = 1
        self.assertEqual(merge(old, main, head)['comment_blocks'], {key: 1})
        head['comment_blocks'][key] = 2
        with self.assertRaisesRegex(ValueError, 'baseline conflict'):
            merge(old, main, head)
        old['comment_blocks'][key] = 3
        del head['comment_blocks'][key]
        with self.assertRaisesRegex(ValueError, 'baseline conflict'):
            merge(old, main, head)

    def test_invalid_metadata_and_entries_stop(self):
        old = baseline()
        for alter in (lambda b: b.update(source='other'),
                      lambda b: b['module_lines'].update({'x.py': {'line_count': True, 'sha256': 'a' * 64}}),
                      lambda b: b['comment_blocks'].update({'../x.py|' + 'a' * 16: 1})):
            bad = copy.deepcopy(old)
            alter(bad)
            with self.assertRaises(ValueError):
                merge(old, old, bad)
        with self.assertRaises(ValueError):
            merge_baselines('{"source":1,"source":2}', '{}', '{}')


if __name__ == '__main__':
    unittest.main()
