import unittest

from conflict_repair.eligibility import classify


def pr(number, base, head, repo='owner/repo'):
    return {'number': number, 'state': 'open',
            'base': {'repo': {'full_name': repo}, 'ref': base, 'sha': 'a'},
            'head': {'repo': {'full_name': repo}, 'ref': head, 'sha': 'b'}}


class EligibilityTest(unittest.TestCase):
    def check(self, rows, number):
        return classify(rows, number, 'owner/repo', 'main')

    def test_stacks_and_siblings(self):
        rows = [pr(1, 'main', 'parent'), pr(2, 'parent', 'child'),
                pr(3, 'child', 'grandchild'), pr(4, 'parent', 'sibling')]
        for number in range(1, 5):
            self.assertIsNone(self.check(rows, number)[0])
        self.assertEqual(self.check(rows, 1)[2], [2, 4])
        self.assertIsNotNone(self.check(rows[:1], 1)[0])

    def test_duplicate_head_and_incomplete_fail_closed(self):
        self.assertIsNone(self.check([pr(1, 'main', 'a'), pr(2, 'main', 'a')], 1)[0])
        self.assertIsNone(self.check([pr(1, 'main', 'a'), {}], 1)[0])
        fork = pr(1, 'main', 'a')
        fork['head']['repo'] = None
        self.assertIsNone(self.check([fork], 1)[0])
