"""Conformance of the Python sidecar to kefer-contracts independent references.

Same checks as tauri-application `contract_conformance.rs`: JPL Horizons
positions (mean equinox of date), ERFA axes, USNO moon phases, the aspect
detection fixture and the chart-result API schema.
"""

import math
import unittest
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=ResourceWarning)

from module import services
from module.astronomy import compute_normalized_chart_aspects, compute_normalized_cross_aspects
from module.cli import _build_chart_response_from_chart_data
from module.model_catalog import builtin_standard_model
from module.utils import parse_chart_yaml
from tests.contracts_location import load

PRAGUE = (50.0875, 14.4214)
EPHEMERIS = Path(__file__).resolve().parents[1] / "source" / "de421.bsp"


def chart_at(utc, objects, **config):
    base = {"definition": {"kind": "base", "purpose": "natal"}, "zodiac_type": "Tropical",
            "aspect_orbs": {}, "engine": "jpl", "observable_objects": objects,
            "house_system": "Placidus"}
    base.update(config)
    return parse_chart_yaml({
        "id": "conformance",
        "subject": {"id": "conformance", "name": "conformance", "event_time": utc,
                    "location": {"name": "Prague", "latitude": PRAGUE[0], "longitude": PRAGUE[1],
                                 "timezone": "UTC"}},
        "config": base, "tags": [],
    })


def lon(value):
    return value["longitude"] if isinstance(value, dict) else value


def arcsec(a, b):
    return ((a - b + 540.0) % 360.0 - 180.0) * 3600.0


class ReferenceConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tolerances = load("reference/tolerances.json")

    def test_positions_match_jpl_horizons_on_the_mean_equinox(self):
        horizons = load("reference/positions-horizons.json")
        erfa = load("reference/earth-orientation-erfa.json")["epochs"]
        tol = self.tolerances["positions_mean_equinox_arcsec"]
        bodies = load("capabilities.json")["implementations"]["python"]["ephemeris_grade_bodies"]
        for i, epoch in enumerate(horizons["epochs_utc"]):
            data = services.compute_chart_data_for_chart(chart_at(epoch, bodies))
            for body in bodies:
                with self.subTest(epoch=epoch, body=body):
                    reference = horizons["positions"][body][i]["lon_true_deg"] - erfa[i]["nutation_longitude_deg"]
                    limit = tol.get(body, tol["default"])
                    self.assertLessEqual(abs(arcsec(lon(data.positions[body]), reference)), limit)

    def test_two_body_minor_bodies_are_disclosed_far_from_their_epoch(self):
        data = services.compute_chart_data_for_chart(chart_at("1950-06-15T12:00:00Z", ["ceres", "chiron"]))
        self.assertTrue(any(w.startswith("ceres_two_body_approximation") for w in data.warnings))
        self.assertTrue(any(w.startswith("chiron_two_body_approximation") for w in data.warnings))

    def test_axes_match_erfa_mean_convention(self):
        limit = self.tolerances["axes_mean_convention_arcsec"]
        for epoch in load("reference/earth-orientation-erfa.json")["epochs"]:
            data = services.compute_chart_data_for_chart(chart_at(epoch["utc"], ["sun"]))
            ramc = math.radians(epoch["gmst_deg"] + PRAGUE[1])
            eps = math.radians(epoch["mean_obliquity_deg"])
            lat = math.radians(PRAGUE[0])
            mc = math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps)))
            asc = math.degrees(math.atan2(-math.cos(ramc), math.sin(eps) * math.tan(lat) + math.cos(eps) * math.sin(ramc))) + 180.0
            with self.subTest(epoch=epoch["utc"]):
                self.assertLessEqual(abs(arcsec(data.axes["mc"], mc)), limit)
                self.assertLessEqual(abs(arcsec(data.axes["asc"], asc)), limit)

    def test_usno_new_and_full_moons(self):
        limit = self.tolerances["moon_phase_elongation_arcsec"]
        for phase in load("reference/moon-phases-usno-2024.json")["phases"]:
            data = services.compute_chart_data_for_chart(chart_at(phase["utc"], ["sun", "moon"]))
            target = 0.0 if phase["phase"] == "New Moon" else 180.0
            elongation = lon(data.positions["moon"]) - lon(data.positions["sun"])
            with self.subTest(utc=phase["utc"]):
                self.assertLessEqual(abs(arcsec(elongation, target)), limit)

    def test_speeds_are_computed_not_placeholders(self):
        data = services.compute_chart_data_for_chart(chart_at("2024-04-10T12:00:00Z", ["sun", "moon", "mercury"]))
        speeds = {k: v["speed"] for k, v in data.positions.items() if isinstance(v, dict)}
        self.assertAlmostEqual(speeds["sun"], 0.985, delta=0.02)
        self.assertGreater(speeds["moon"], 11.0)
        self.assertLess(speeds["mercury"], 0.0)  # Mercury retrograde 2024-04-01..25
        self.assertTrue(data.positions["mercury"]["retrograde"])

    def test_aspect_detection_matches_contract_fixture(self):
        fixture = load("aspects/detection.json")
        definitions = builtin_standard_model().aspect_definitions
        all_ids = [a.id for a in definitions]
        for case in fixture["cases"]:
            if case["kind"] == "chart":
                got = compute_normalized_chart_aspects(case["positions"], aspect_orbs=case["aspect_orbs"],
                                                       selected_aspects=all_ids, aspect_definitions=definitions)
            else:
                got = compute_normalized_cross_aspects(case["transiting"], case["transited"],
                                                       aspect_orbs=case["aspect_orbs"],
                                                       selected_aspects=all_ids, aspect_definitions=definitions)

            def key(a):
                pair = (a["from"], a["to"])
                if case["kind"] == "chart":
                    pair = tuple(sorted(pair))
                return pair + (a["type"],)

            actual = {key(a): a["orb"] for a in got}
            expected = {key(e): e["orb"] for e in case["expected"]}
            with self.subTest(case=case["id"]):
                self.assertEqual(sorted(actual), sorted(expected))
                for k, orb in expected.items():
                    self.assertAlmostEqual(actual[k], orb, delta=1e-6)

    def test_declared_capabilities_match_the_implementation(self):
        from module.astronomy import NATIVE_HOUSE_SYSTEMS
        from module._contract_catalog import CALCULATION_CONVENTION
        caps = load("capabilities.json")["implementations"]["python"]
        self.assertEqual(caps["house_systems_native"], list(NATIVE_HOUSE_SYSTEMS))
        from module.conventions import IMPLEMENTED
        self.assertEqual(caps["conventions"], list(IMPLEMENTED))
        self.assertEqual(load("conventions.json")["default"], CALCULATION_CONVENTION)
        self.assertEqual(sorted(caps["approximate_bodies"]), sorted(services._MPC_MINOR_BODY_IDS))
        for flag in ("aspect_dynamics", "event_search", "tradition_presets"):
            self.assertFalse(caps[flag], flag)  # declared unsupported; flip with the implementation

    def test_generated_contract_catalog_is_current(self):
        import subprocess, sys
        result = subprocess.run([sys.executable, "-m", "devtools.sync_contracts", "--check"],
                                capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_chart_result_has_every_field_required_by_the_api_schema(self):
        schema = load("schemas/api/chart-result.schema.json")
        chart = chart_at("2024-01-01T12:00:00Z", ["sun", "moon", "mars"])
        data = services.compute_chart_data_for_chart(chart)
        aspects = compute_normalized_chart_aspects(data.positions)
        response = _build_chart_response_from_chart_data(chart, data, aspects, "conformance", False)
        for field in schema["required"]:
            self.assertIn(field, response)
        for aspect in response["aspects"]:
            for field in schema["properties"]["aspects"]["items"]["required"]:
                self.assertIn(field, aspect)


TRUE_EQUINOX = "kefer-positions/1-true-equinox"


class TrueEquinoxConformanceTests(unittest.TestCase):
    """kefer-positions/1-true-equinox: same checks as Rust contract_conformance.rs."""

    @classmethod
    def setUpClass(cls):
        cls.tolerances = load("reference/tolerances.json")

    def test_positions_match_horizons_true_equinox_directly(self):
        horizons = load("reference/positions-horizons.json")
        tol = self.tolerances["positions_true_equinox_arcsec"]
        bodies = load("capabilities.json")["implementations"]["python"]["ephemeris_grade_bodies"]
        for i, epoch in enumerate(horizons["epochs_utc"]):
            data = services.compute_chart_data_for_chart(
                chart_at(epoch, bodies, calculation_convention=TRUE_EQUINOX))
            for body in bodies:
                with self.subTest(epoch=epoch, body=body):
                    err = arcsec(lon(data.positions[body]), horizons["positions"][body][i]["lon_true_deg"])
                    self.assertLessEqual(abs(err), tol.get(body, tol["default"]))

    def test_axes_match_erfa_gast_and_true_obliquity(self):
        limit = self.tolerances["axes_true_convention_arcsec"]
        for epoch in load("reference/earth-orientation-erfa.json")["epochs"]:
            data = services.compute_chart_data_for_chart(
                chart_at(epoch["utc"], ["sun"], calculation_convention=TRUE_EQUINOX))
            ramc = math.radians(epoch["gast_deg"] + PRAGUE[1])
            eps = math.radians(epoch["true_obliquity_deg"])
            lat = math.radians(PRAGUE[0])
            mc = math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps)))
            asc = math.degrees(math.atan2(-math.cos(ramc), math.sin(eps) * math.tan(lat) + math.cos(eps) * math.sin(ramc))) + 180.0
            with self.subTest(epoch=epoch["utc"]):
                self.assertLessEqual(abs(arcsec(data.axes["mc"], mc)), limit)
                self.assertLessEqual(abs(arcsec(data.axes["asc"], asc)), limit)

    def test_true_equinox_house_fixture_parity(self):
        from module.astronomy import (
            _compute_axes_with, _house_cusps_for_system_with, _local_sidereal_time_deg,
            _mean_obliquity_deg, _normalize_deg,
        )
        from datetime import datetime, timezone
        fixture = load("houses/cusps-true-equinox.json")
        tol = fixture["tolerance_deg"]
        for case in fixture["cases"]:
            _dpsi, deps, ee = services._true_equinox_terms(
                datetime.fromisoformat(case["utc"].replace("Z", "+00:00")).astimezone(timezone.utc))
            ramc = _normalize_deg(_local_sidereal_time_deg(case["jd_ut"], case["longitude"]) + ee)
            eps = _mean_obliquity_deg(case["jd_ut"]) + deps
            with self.subTest(case=case["id"]):
                self.assertLessEqual(abs(arcsec(ramc, case["ramc_deg"])) / 3600, tol)
                self.assertLessEqual(abs(eps - case["obliquity_deg"]), tol)
                axes = _compute_axes_with(case["ramc_deg"], case["obliquity_deg"], case["latitude"])
                for system, expected in case["systems"].items():
                    cusps, warnings = _house_cusps_for_system_with(
                        system, case["ramc_deg"], case["obliquity_deg"], case["latitude"], axes["asc"], axes["mc"])
                    self.assertEqual(warnings, expected["warnings"], system)
                    for got, want in zip(cusps, expected["cusps"]):
                        self.assertLessEqual(abs(arcsec(got, want)) / 3600, 1e-9, system)

    def test_results_report_the_convention_and_never_switch_silently(self):
        def run(convention):
            extra = {"calculation_convention": convention} if convention else {}
            chart = chart_at("2024-01-01T12:00:00Z", ["sun", "moon"], **extra)
            data = services.compute_chart_data_for_chart(chart)
            return _build_chart_response_from_chart_data(chart, data, [], "c", False)
        default, true_eq, unknown = run(None), run(TRUE_EQUINOX), run("kefer-positions/9")
        self.assertEqual(default["calculation_convention"], "kefer-positions/1")
        self.assertEqual(true_eq["calculation_convention"], TRUE_EQUINOX)
        self.assertNotEqual(lon(default["positions"]["sun"]), lon(true_eq["positions"]["sun"]))
        self.assertEqual(unknown["calculation_convention"], "kefer-positions/1")
        self.assertEqual(lon(unknown["positions"]["sun"]), lon(default["positions"]["sun"]))
        self.assertIn("calculation_convention_unsupported: kefer-positions/9; kefer-positions/1_used",
                      unknown["warnings"])


if __name__ == "__main__":
    unittest.main()
