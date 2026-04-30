import unittest
from datetime import datetime

from src.models.user import User


class UserModelTest(unittest.TestCase):
    def test_default_created_at_uses_timezone_aware_utc_timestamp(self):
        user = User(username="tester")

        created_at = datetime.fromisoformat(user.created_at)

        self.assertIsNotNone(created_at.tzinfo)
        self.assertEqual(created_at.utcoffset().total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
