import unittest
from datetime import datetime, timedelta, UTC
from module.utils import Actual


class Context(unittest.TestCase):
    def test_current_timestamp(self):
        self.assertEqual(Actual().value.replace(microsecond=0), datetime.now().replace(microsecond=0))

    def test_custom_timestamp(self):
        # this is a timestamp specific to czech region (switched day and month)
        self.assertEqual(Actual("11.1.2011").value, datetime(2011, 1, 11))

    def test_gregorian_timestamp(self):
        self.assertEqual(Actual("2023-348").value, datetime(2023, 12, 14))

    def test_iso_week_date(self):
        # 2023-W50-1 is Monday of week 50, 2023-12-11
        self.assertEqual(Actual("2023-W50-1").value, datetime(2023, 12, 11))
    
    def test_julian_timestamp(self):
        self.assertEqual(Actual("2023-12-14").value, datetime(2023, 12, 14))

    def test_julian_day_number(self):
        # JD2451545.0 is 2000-01-01 12:00:00 UTC
        result = Actual("JD2451545.0").value
        expected = datetime(2000, 1, 1, 12, 0, 0)
        self.assertEqual(result, expected)

    def test_julian_day_number_no_prefix(self):
        # 2451545.0 is also 2000-01-01 12:00:00 UTC
        result = Actual("2451545.0").value
        expected = datetime(2000, 1, 1, 12, 0, 0)
        self.assertEqual(result, expected)

    def test_compact_date(self):
        self.assertEqual(Actual("20231214").value, datetime(2023, 12, 14))

    def test_relative_today(self):
        # Allow a few seconds difference
        actual = Actual("today").value.replace(microsecond=0)
        now = datetime.now().replace(microsecond=0)
        self.assertAlmostEqual(actual.timestamp(), now.timestamp(), delta=2)

    def test_relative_yesterday(self):
        actual = Actual("yesterday").value.replace(microsecond=0)
        expected = (datetime.now() - timedelta(days=1)).replace(microsecond=0)
        self.assertAlmostEqual(actual.timestamp(), expected.timestamp(), delta=2)

    def test_relative_tomorrow(self):
        actual = Actual("tomorrow").value.replace(microsecond=0)
        expected = (datetime.now() + timedelta(days=1)).replace(microsecond=0)
        self.assertAlmostEqual(actual.timestamp(), expected.timestamp(), delta=2)

    def test_unix_timestamp(self):
        # 1700000000 is 2023-11-14 22:13:20 UTC
        self.assertEqual(Actual("1700000000").value, datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC))

    def test_year_month_only(self):
        self.assertEqual(Actual("2023-12").value, datetime(2023, 12, 1))

    def test_year_only(self):
        self.assertEqual(Actual("2023").value, datetime(2023, 1, 1))

if __name__ == "__main__":
    unittest.main()
