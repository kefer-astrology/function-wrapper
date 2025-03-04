import unittest
from datetime import datetime
from module.context import Actual


class Context(unittest.TestCase):
    def test_current_timestamp(self):
        self.assertEqual(Actual().value.replace(microsecond=0), datetime.now().replace(microsecond=0))

    def test_custom_timestamp(self):
        self.assertEqual(Actual("11.1.2011").value, datetime(2011, 1, 11))

    def test_gregorian_timestamp(self):
        self.assertEqual(Actual("2023-348").value, datetime(2023, 12, 14))

    def test_julian_timestamp(self):
        self.assertEqual(Actual("2023-12-14").value, datetime(2023, 12, 14))

    def test_no_location_fallback(self):
        self.assertIn("Prague", Actual(t="place").value.address)

    def test_dummy_location(self):
        self.assertIn("Russia", Actual("Blabla", t="place").value.address)

    def test_false_location_fallback(self):
        self.assertIn("Brno", Actual("neexistuje", t="place").value.address)

    # - date inputs check also
    # - as well as various places
    # - add negative time


if __name__ == "__main__":
    unittest.main()
