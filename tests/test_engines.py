"""
Tests for the JPL/Skyfield computation engine.
"""

# Suppress ResourceWarnings from jplephem/skyfield (Skyfield dependency) BEFORE imports
# These are harmless - SQLite connections are closed when objects are garbage collected
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

import unittest
import datetime
from pathlib import Path
from pprint import pformat
import pytz

try:
    from skyfield.api import load_file, Topos
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False

from module.services import compute_jpl_positions


class TestJPLSkyfieldEngine(unittest.TestCase):
    """Test JPL/Skyfield engine position computation."""
    
    @unittest.skipUnless(SKYFIELD_AVAILABLE, "skyfield not available")
    def setUp(self):
        """Set up test ephemeris."""
        # Try to find ephemeris file
        eph_paths = [
            "source/de421.bsp",
            "de421.bsp",
            Path(__file__).parent.parent / "source" / "de421.bsp",
        ]
        
        self.ephemeris_path = None
        for path in eph_paths:
            p = Path(path)
            if p.exists():
                self.ephemeris_path = str(p)
                break
        
        if not self.ephemeris_path:
            self.skipTest("JPL ephemeris file (de421.bsp) not found")
    
    def test_jpl_basic_positions(self):
        """Test basic JPL position computation (longitude only)."""
        dt_str = "2024-01-01T12:00:00+00:00"
        loc_str = "Prague, CZ"
        
        positions = compute_jpl_positions(
            name="Test",
            dt_str=dt_str,
            loc_str=loc_str,
            ephemeris_path=self.ephemeris_path,
            extended=False
        )
        
        self.assertIsInstance(positions, dict)
        self.assertGreater(len(positions), 0)
        
        # Check that we have basic planets
        expected_planets = ["sun", "moon", "mercury", "venus", "mars"]
        for planet in expected_planets:
            if planet in positions:
                lon = positions[planet]
                self.assertIsInstance(lon, float)
                self.assertGreaterEqual(lon, 0.0)
                self.assertLess(lon, 360.0)
    
    @unittest.skipUnless(SKYFIELD_AVAILABLE, "skyfield not available")
    def test_jpl_extended_positions(self):
        """Test extended JPL position computation with all properties."""
        dt_str = "2024-01-01T12:00:00+00:00"
        loc_str = "Prague, CZ"
        
        positions = compute_jpl_positions(
            name="Test",
            dt_str=dt_str,
            loc_str=loc_str,
            ephemeris_path=self.ephemeris_path,
            extended=True,
            include_physical=True,
            include_topocentric=True
        )
        
        self.assertIsInstance(positions, dict)
        self.assertGreater(len(positions), 0)

        # Pure-formula calculated points (lunar nodes, Lilith) have no observed
        # distance/declination/RA — they're directions derived from orbital
        # elements, not bodies Skyfield observes from Earth. Only longitude is
        # guaranteed for these; full extended fields apply to observed bodies
        # (planets, Chiron, Ceres/Pallas/Juno/Vesta).
        calculated_points = {
            "north_node", "south_node", "mean_node", "mean_south_node",
            "true_north_node", "true_south_node", "true_node",
            "lilith", "mean_lilith", "true_lilith",
        }

        # Check extended format
        for planet, pos_data in positions.items():
            self.assertIsInstance(pos_data, dict)

            # Required fields
            self.assertIn("longitude", pos_data)

            # Validate longitude
            lon = pos_data["longitude"]
            self.assertIsInstance(lon, float)
            self.assertGreaterEqual(lon, 0.0)
            self.assertLess(lon, 360.0)

            if planet in calculated_points:
                continue

            self.assertIn("distance", pos_data)
            self.assertIn("declination", pos_data)
            self.assertIn("right_ascension", pos_data)

            # Validate distance (should be positive)
            dist = pos_data["distance"]
            self.assertIsInstance(dist, float)
            self.assertGreater(dist, 0.0)

            # Validate declination (should be between -90 and 90)
            dec = pos_data["declination"]
            self.assertIsInstance(dec, float)
            self.assertGreaterEqual(dec, -90.0)
            self.assertLessEqual(dec, 90.0)

            # Validate RA (should be between 0 and 360)
            ra = pos_data["right_ascension"]
            self.assertIsInstance(ra, float)
            self.assertGreaterEqual(ra, 0.0)
            self.assertLess(ra, 360.0)
            
            # Optional topocentric fields
            if "altitude" in pos_data:
                alt = pos_data["altitude"]
                self.assertIsInstance(alt, float)
                self.assertGreaterEqual(alt, -90.0)
                self.assertLessEqual(alt, 90.0)
            
            if "azimuth" in pos_data:
                az = pos_data["azimuth"]
                self.assertIsInstance(az, float)
                self.assertGreaterEqual(az, 0.0)
                self.assertLess(az, 360.0)
    
    @unittest.skipUnless(SKYFIELD_AVAILABLE, "skyfield not available")
    def test_jpl_known_date(self):
        """Test JPL positions for a known date (2024-01-01)."""
        dt_str = "2024-01-01T12:00:00+00:00"
        loc_str = "Prague, CZ"
        
        positions = compute_jpl_positions(
            name="Test",
            dt_str=dt_str,
            loc_str=loc_str,
            ephemeris_path=self.ephemeris_path,
            extended=False
        )
        
        # Sun should be around 280° (Capricorn) on Jan 1
        if "sun" in positions:
            sun_lon = positions["sun"]
            # Sun on Jan 1 is around 280-290° (Capricorn)
            self.assertGreater(sun_lon, 270.0)
            self.assertLess(sun_lon, 300.0)
    
    @unittest.skipUnless(SKYFIELD_AVAILABLE, "skyfield not available")
    def test_jpl_outer_planets(self):
        """Test that outer planets (Jupiter, Saturn) are computed correctly."""
        dt_str = "2024-01-01T12:00:00+00:00"
        loc_str = "Prague, CZ"
        
        positions = compute_jpl_positions(
            name="Test",
            dt_str=dt_str,
            loc_str=loc_str,
            ephemeris_path=self.ephemeris_path,
            extended=False,
            requested_objects=["jupiter", "saturn"]
        )
        
        # Should have both planets
        self.assertIn("jupiter", positions)
        self.assertIn("saturn", positions)
        
        # Validate positions
        for planet in ["jupiter", "saturn"]:
            lon = positions[planet]
            self.assertIsInstance(lon, float)
            self.assertGreaterEqual(lon, 0.0)
            self.assertLess(lon, 360.0)

    @unittest.skipUnless(SKYFIELD_AVAILABLE, "skyfield not available")
    def test_jpl_available_functions(self):
        """Report and sanity-check available Skyfield API functions."""
        import skyfield.api as skyfield_api

        public_callables = sorted(
            name
            for name in dir(skyfield_api)
            if not name.startswith("_") and callable(getattr(skyfield_api, name))
        )

        # Ensure a few key API helpers are present.
        self.assertIn("load", public_callables)
        self.assertIn("load_file", public_callables)
        self.assertIn("Topos", public_callables)
        self.assertGreater(len(public_callables), 0)
        print("Skyfield public callables:", public_callables)

    @unittest.skipUnless(SKYFIELD_AVAILABLE, "skyfield not available")
    def test_jpl_today_tomorrow_transits_output(self):
        """Report typical JPL output shape for today and tomorrow."""
        if not self.ephemeris_path:
            self.skipTest("JPL ephemeris file (de421.bsp) not found")

        tz = pytz.UTC
        today = datetime.datetime.now(tz).replace(hour=12, minute=0, second=0, microsecond=0)
        tomorrow = today + datetime.timedelta(days=1)

        for dt_value in [today, tomorrow]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=ResourceWarning)
                positions = compute_jpl_positions(
                    name="Test",
                    dt_str=dt_value.isoformat(),
                    loc_str="Prague, CZ",
                    ephemeris_path=self.ephemeris_path,
                    extended=True,
                    include_physical=True,
                    include_topocentric=True,
                )

            self.assertIsInstance(positions, dict)
            self.assertGreater(len(positions), 0)
            print(
                f"JPL positions for {dt_value.isoformat()}:",
                pformat(positions, width=120),
            )

            # Validate a representative planet structure.
            if "sun" in positions:
                sun_data = positions["sun"]
                self.assertIsInstance(sun_data, dict)
                self.assertIn("longitude", sun_data)
                self.assertIn("distance", sun_data)
                self.assertIn("declination", sun_data)
                self.assertIn("right_ascension", sun_data)
                self.assertIsInstance(sun_data["longitude"], float)
                self.assertIsInstance(sun_data["distance"], float)
                self.assertIsInstance(sun_data["declination"], float)
                self.assertIsInstance(sun_data["right_ascension"], float)


if __name__ == "__main__":
    unittest.main()
