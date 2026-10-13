"""未接続の採用APIを再公開しない。採用判断はagent契約で行う。"""

import unittest

from agy_delegate import adoption


class AdoptionApiTests(unittest.TestCase):
    def test_unconnected_public_api_is_absent(self):
        self.assertFalse(hasattr(adoption, "adoption_reasons"))
