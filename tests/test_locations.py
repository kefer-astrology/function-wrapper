import unittest
from module.utils import Actual


class Context(unittest.TestCase):
    def test_no_location_fallback(self):
        self.assertIn("Prague", Actual(t="place").value.address)

    def test_dummy_location(self):
        self.assertIn("Russia", Actual("Blabla", t="place").value.address)

    def test_false_location_fallback(self):
        self.assertIn("Brno", Actual("neexistuje", t="place").value.address)

    # - various places inputs check 
    # - once we integrate self hosted geo database
    # - it will also test this one


if __name__ == "__main__":
    unittest.main()
