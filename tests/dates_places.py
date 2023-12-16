import unittest
from datetime import datetime
from context import Actual

class Context(unittest.TestCase):
    def test_current_timestamp(self):
        self.assertEqual(Actual().value, datetime.now())

    def test_custom_timestamp(self):
        self.assertEqual(Actual("11.1.2011").value, datetime(2011, 1, 11))

    def test_no_location_fallback(self):
        self.assertEqual(Actual(t="place".value), "Prague")

    def test_false_location_fallback(self):
        self.assertEqual(Actual("Blabla", t="place").value, "Prague")
    
    # - date inputs check also
    # - as well as various places
    # - add negative time

if __name__ == '__main__':
    unittest.main()
