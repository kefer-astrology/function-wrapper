"""Location parsing.

Live geocoding (Nominatim) is network-dependent and rate-limited, so those
checks are opt-in: set KEFER_NETWORK_TESTS=1. Everything else runs offline.
"""

import os
import unittest
from unittest import mock

from module import services
from module.utils import Actual

NETWORK = os.environ.get("KEFER_NETWORK_TESTS") == "1"


class OfflineLocationTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(Actual, "_geocode", return_value=None)  # geocoder unreachable
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_coordinates_never_touch_the_network(self):
        loc = Actual("50.0875,14.4214", t="place").value
        self.assertEqual((loc.latitude, loc.longitude), (50.0875, 14.4214))

    def test_built_in_default_place_works_offline(self):
        loc = Actual(t="place").value
        self.assertIn("Prague", loc.address)
        self.assertAlmostEqual(loc.latitude, 50.0875)

    def test_unknown_place_fallback_works_offline(self):
        self.assertIn("Brno", Actual("neexistuje", t="place").value.address)

    def test_unresolvable_name_fails_clearly_instead_of_crashing(self):
        with self.assertRaisesRegex(ValueError, "^location_unresolved:"):
            services.compute_jpl_positions("x", "2024-01-01T12:00:00Z", "Some Unknown Town")


@unittest.skipUnless(NETWORK, "live geocoding; set KEFER_NETWORK_TESTS=1")
class LiveGeocodingTests(unittest.TestCase):
    def test_no_location_fallback(self):
        self.assertIn("Prague", Actual(t="place").value.address)

    def test_dummy_location(self):
        self.assertIn("Russia", Actual("Blabla", t="place").value.address)

    def test_false_location_fallback(self):
        self.assertIn("Brno", Actual("neexistuje", t="place").value.address)


if __name__ == "__main__":
    unittest.main()
