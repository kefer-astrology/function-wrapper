import unittest
from datetime import datetime
from context import Actual

class Context(unittest.TestCase):
    def test_current_timestamp(self):
        self.assertEqual(Actual(), datetime.now())

    def test_location_fallback(self):
        self.assertEqual(Actual(t="place"), "Prague")

    # - date inputs check also
    # - as well as various places
    # - add negative time

if __name__ == '__main__':
    unittest.main()
