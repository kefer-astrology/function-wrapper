"""
Cross-validation: JplAstronomyBackend at J2000.0 (2000-01-01 12:00:00 UTC, Greenwich).

Validates that the Python JplAstronomyBackend (Skyfield + de421.bsp) produces positions
consistent with the Rust JplAstronomyBackend (anise + de421.bsp).

Run the Rust test first to get its output:
  cd src-tauri && cargo test --features swisseph j2000_positions_match_horizons -- --ignored --nocapture

Then run this test:
  cd backend-python && python -m pytest tests/test_jpl_backend_j2000.py -v -s

Compare the two printed outputs — they should agree to ≤0.01° for all bodies.

Cross-validated reference anchors (Sun well-established; Uranus/Neptune slow movers):
  sun     ~280.4°    uranus  ~314.8°    neptune ~303.2°
"""

import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

import unittest
from datetime import timezone, datetime
from pathlib import Path

try:
    from module.astronomy import JplAstronomyBackend, _extract_longitude
    from module.models import (
        ChartInstance, ChartSubject, ChartConfig, Location,
        ChartMode, HouseSystem, ZodiacType, EngineType,
    )
except ImportError:
    from astronomy import JplAstronomyBackend, _extract_longitude
    from models import (
        ChartInstance, ChartSubject, ChartConfig, Location,
        ChartMode, HouseSystem, ZodiacType, EngineType,
    )

BSP_PATH = Path(__file__).parent.parent / "source" / "de421.bsp"

# Cross-validated anchors (Sun + slow movers only — inner planets validated by Rust/Python comparison)
REFERENCE_J2000: list[tuple[str, float, float]] = [
    ("sun",     280.4, 1.0),
    ("uranus",  314.8, 1.0),
    ("neptune", 303.2, 1.0),
]

EXPECTED_BODIES = ["sun", "moon", "mercury", "venus", "mars",
                   "jupiter", "saturn", "uranus", "neptune", "pluto"]


def _make_j2000_chart(bsp_path: str) -> ChartInstance:
    return ChartInstance(
        id="j2000_test",
        subject=ChartSubject(
            id="j2000",
            name="J2000.0",
            event_time=datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            location=Location(
                name="Greenwich",
                latitude=51.4779,
                longitude=0.0,
                timezone="UTC",
            ),
        ),
        config=ChartConfig(
            mode=ChartMode.NATAL,
            house_system=HouseSystem.WHOLE_SIGN,
            zodiac_type=ZodiacType.TROPICAL,
            included_points=[],
            aspect_orbs={},
            display_style="",
            color_theme="",
            override_ephemeris=bsp_path,
            engine=EngineType.JPL,
        ),
    )


def _angular_diff(a: float, b: float) -> float:
    """Signed angular distance a − b in (−180, 180]."""
    return ((a - b + 180.0) % 360.0) - 180.0


@unittest.skipUnless(BSP_PATH.exists(), f"de421.bsp not found at {BSP_PATH}")
class TestJplBackendJ2000(unittest.TestCase):
    """Validate JplAstronomyBackend.compute_chart_data() at J2000.0."""

    @classmethod
    def setUpClass(cls):
        chart = _make_j2000_chart(str(BSP_PATH))
        backend = JplAstronomyBackend(ephemeris_path=str(BSP_PATH))
        cls.data = backend.compute_chart_data(chart)

        # Normalise: Skyfield returns extended dicts per body; extract plain longitudes.
        cls.longitudes: dict[str, float] = {}
        for body, val in cls.data.positions.items():
            lon = _extract_longitude(val)
            if lon is not None:
                cls.longitudes[body] = lon

        print("\n=== JplAstronomyBackend positions at J2000.0 (Python/Skyfield) ===")
        for body, lon in sorted(cls.longitudes.items()):
            print(f"  {body:<20} {lon:.4f}°")
        if cls.data.axes:
            for key, val in sorted(cls.data.axes.items()):
                print(f"  {key:<20} {val:.4f}°  (axis)")
        else:
            print("  axes: not computed (gap — pending implementation)")
        if cls.data.house_cusps:
            print(f"  house_cusps: {[round(c, 4) for c in cls.data.house_cusps]}")
        else:
            print("  house_cusps: not computed (gap — pending implementation)")

    def test_all_planets_present(self):
        for body in EXPECTED_BODIES:
            self.assertIn(body, self.longitudes, f"{body} missing from positions")

    def test_longitudes_in_range(self):
        for body, lon in self.longitudes.items():
            self.assertGreaterEqual(lon, 0.0, f"{body} longitude below 0")
            self.assertLess(lon, 360.0, f"{body} longitude >= 360")

    def test_reference_anchors(self):
        """Sun and slow-moving outer planets validated against cross-checked values."""
        for body, expected, tol in REFERENCE_J2000:
            lon = self.longitudes.get(body)
            self.assertIsNotNone(lon, f"{body} missing")
            diff = _angular_diff(lon, expected)
            self.assertLessEqual(
                abs(diff), tol,
                f"{body}: got {lon:.4f}°, expected {expected}° ±{tol}° (diff {diff:+.4f}°)",
            )

    def test_axes_are_computed(self):
        """Python JplAstronomyBackend should expose the full cardinal axes payload."""
        for key in ("asc", "desc", "mc", "ic"):
            self.assertIn(key, self.data.axes)
            self.assertGreaterEqual(self.data.axes[key], 0.0)
            self.assertLess(self.data.axes[key], 360.0)

    def test_house_cusps_are_computed(self):
        """Python JplAstronomyBackend should expose 12 normalized house cusps."""
        self.assertEqual(len(self.data.house_cusps), 12)
        for cusp in self.data.house_cusps:
            self.assertGreaterEqual(cusp, 0.0)
            self.assertLess(cusp, 360.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
