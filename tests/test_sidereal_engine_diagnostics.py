"""Regression tests for Phase 0 stabilization (sidereal / engine diagnostics).

Before these fixes the Python sidecar:
- silently computed Skyfield/JPL positions for charts configured with the
  `jyotish`, `custom` or `swisseph` engine (the Tauri app force-routes
  jyotish/custom charts here) and reported the configured engine name as
  `backend_used`;
- silently fell back to Fagan-Bradley when the ayanamsa was unset or
  `UserDefined`;
- returned tropical positions for a sidereal chart, with only a log line,
  when the ayanamsa could not be applied;
- accepted event-time strings that the shared Rust contract rejects.
"""

import unittest
import warnings
from pathlib import Path
from unittest import mock

warnings.filterwarnings("ignore", category=ResourceWarning)

from module import services
from module.astronomy import ayanamsa_warnings, engine_substitution_warnings
from module.cli import _resolve_backend_used
from module.event_time import parse_event_time
from module.models import Ayanamsa
from module.utils import parse_chart_yaml

EPHEMERIS = Path(__file__).resolve().parents[1] / "source" / "de421.bsp"


def chart(**config):
    base_config = {
        "definition": {"kind": "base", "purpose": "natal"},
        "house_system": "Placidus",
        "zodiac_type": "Tropical",
        "aspect_orbs": {},
        "engine": "jpl",
        "override_ephemeris": str(EPHEMERIS),
        "observable_objects": ["sun", "moon"],
    }
    base_config.update(config)
    return parse_chart_yaml(
        {
            "id": "phase0",
            "subject": {
                "id": "phase0",
                "name": "Phase 0",
                "event_time": "2024-01-01T12:00:00+00:00",
                "location": {
                    "name": "Prague",
                    "latitude": 50.0875,
                    "longitude": 14.4214,
                    "timezone": "Europe/Prague",
                },
            },
            "config": base_config,
            "tags": [],
        }
    )


class EngineSubstitutionTests(unittest.TestCase):
    def test_unimplemented_engines_warn(self):
        for engine in ("jyotish", "custom"):
            with self.subTest(engine=engine):
                self.assertEqual(
                    engine_substitution_warnings(chart(engine=engine)),
                    [f"engine_{engine}_not_implemented: jpl_used"],
                )

    def test_unavailable_engine_warns(self):
        self.assertEqual(
            engine_substitution_warnings(chart(engine="swisseph")),
            ["engine_swisseph_not_available: jpl_used"],
        )

    def test_jpl_and_unset_engine_do_not_warn(self):
        self.assertEqual(engine_substitution_warnings(chart(engine="jpl")), [])
        self.assertEqual(engine_substitution_warnings(chart(engine=None)), [])

    def test_backend_used_reports_backend_that_ran_not_configured_engine(self):
        for engine in ("jyotish", "custom", "swisseph", "jpl"):
            with self.subTest(engine=engine):
                self.assertEqual(_resolve_backend_used(chart(engine=engine)), "jpl")


class AyanamsaWarningTests(unittest.TestCase):
    def test_known_ayanamsa_is_flagged_approximate_only(self):
        self.assertEqual(
            ayanamsa_warnings(Ayanamsa.LAHIRI),
            ["ayanamsa_approximate: linear_precession_model"],
        )

    def test_unset_and_user_defined_fallbacks_are_reported(self):
        self.assertIn("ayanamsa_unspecified: fagan_bradley_used", ayanamsa_warnings(None))
        self.assertIn(
            "ayanamsa_userdefined_not_supported: fagan_bradley_used",
            ayanamsa_warnings(Ayanamsa.USER_DEFINED),
        )


@unittest.skipUnless(EPHEMERIS.exists(), "bundled de421.bsp required")
class ChartDataDiagnosticsTests(unittest.TestCase):
    def test_sidereal_chart_is_shifted_and_flagged(self):
        tropical = services.compute_chart_data_for_chart(chart())
        sidereal = services.compute_chart_data_for_chart(
            chart(zodiac_type="Sidereal", ayanamsa="Lahiri")
        )
        trop_sun = tropical.positions["sun"]["longitude"]
        sid_sun = sidereal.positions["sun"]["longitude"]
        # Lahiri ayanamsa in 2024 is ~24.2 degrees.
        self.assertAlmostEqual((trop_sun - sid_sun) % 360.0, 24.2, delta=0.1)
        self.assertIn("ayanamsa_approximate: linear_precession_model", sidereal.warnings)
        self.assertNotIn("ayanamsa_approximate: linear_precession_model", tropical.warnings)

    def test_failed_sidereal_shift_is_not_silent(self):
        with mock.patch.object(
            services, "apply_ayanamsa_to_chart_data", side_effect=ValueError("boom")
        ):
            data = services.compute_chart_data_for_chart(chart(zodiac_type="Sidereal"))
        self.assertIn("zodiac_sidereal_not_applied: tropical_positions_returned", data.warnings)

    def test_mpc_bodies_far_from_element_epoch_are_flagged(self):
        historical = chart(observable_objects=["sun", "ceres", "chiron"])
        historical.subject.event_time = historical.subject.event_time.replace(year=1950)
        data = services.compute_chart_data_for_chart(historical)
        flagged = [w for w in data.warnings if "_two_body_approximation" in w]
        self.assertEqual(len(flagged), 2, data.warnings)
        recent = services.compute_chart_data_for_chart(chart(observable_objects=["ceres"]))
        self.assertFalse([w for w in recent.warnings if "_two_body_approximation" in w])

    def test_jyotish_chart_result_carries_substitution_warning(self):
        data = services.compute_chart_data_for_chart(chart(engine="jyotish"))
        self.assertIn("engine_jyotish_not_implemented: jpl_used", data.warnings)


class EventTimeGrammarTests(unittest.TestCase):
    """Inline copy of the divergent cases so the regression is caught even
    when the shared contract fixture is not reachable."""

    def test_forms_rejected_by_rust_are_rejected(self):
        for value in (
            "2024-01-01T12:30",
            "2024-01-01T12:30+01:00",
            "2024-01-01T12:30:45+0100",
            "2024-01-01T12:30:45.123",
            "20240101",
            "2024-01-01T12",
            "2024-W01-1",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "^invalid_event_time:"):
                    parse_event_time(value)

    def test_rfc3339_and_legacy_forms_still_accepted(self):
        cases = {
            "2024-01-01T12:00:00+01:00": "2024-01-01T11:00:00+00:00",
            "2024-01-01t12:30:45z": "2024-01-01T12:30:45+00:00",
            "2024-01-01T12:30:45.5Z": "2024-01-01T12:30:45.500000+00:00",
            "2024-01-01 12:30": "2024-01-01T12:30:00+00:00",
            "2024-01-01T12:30:45": "2024-01-01T12:30:45+00:00",
            "2024-01-01": "2024-01-01T00:00:00+00:00",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_event_time(value).isoformat(), expected)

    def test_legacy_naive_value_uses_supplied_timezone(self):
        self.assertEqual(
            parse_event_time("2024-01-01 12:00:00", "Europe/Prague").isoformat(),
            "2024-01-01T11:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
