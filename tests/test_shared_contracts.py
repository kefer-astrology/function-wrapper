"""Python side of the shared Rust/Python contract fixtures (Phase 0).

Fixtures live in tauri-application/contracts/ (see tests/contracts_location.py).
"""

import json
import unittest

from module.astronomy import (
    NATIVE_HOUSE_SYSTEMS,
    _compute_axes,
    _house_cusps_for_system,
    engine_substitution_warning,
)
from module.model_catalog import (
    ASPECT_ALIASES,
    ASPECT_CATALOG_VERSION,
    builtin_standard_model,
    canonical_aspect_id,
)
from tests.contracts_location import contracts_dir


def _load(name):
    return json.loads((contracts_dir() / name).read_text(encoding="utf-8"))


def _angle_close(a, b, tol):
    d = (a - b) % 360.0
    return min(d, 360.0 - d) <= tol


class HouseCuspContractTests(unittest.TestCase):
    def test_axes_cusps_and_substitution_warnings_match_rust(self):
        fixture = _load("houses/cusps.json")
        tol = fixture["tolerance_deg"]
        for case in fixture["cases"]:
            axes = _compute_axes(case["jd_ut"], case["latitude"], case["longitude"])
            for name, expected in case["axes"].items():
                self.assertTrue(
                    _angle_close(axes[name], expected, tol),
                    f"{case['id']} {name}: {axes[name]} != {expected}",
                )
            for system, expected in case["systems"].items():
                with self.subTest(case=case["id"], system=system):
                    cusps, warnings = _house_cusps_for_system(
                        system, case["jd_ut"], case["latitude"], case["longitude"],
                        axes["asc"], axes["mc"],
                    )
                    self.assertEqual(warnings, expected["warnings"])
                    self.assertEqual(len(cusps), len(expected["cusps"]))
                    for i, (got, want) in enumerate(zip(cusps, expected["cusps"]), start=1):
                        self.assertTrue(
                            _angle_close(got, want, tol),
                            f"cusp {i}: {got} != {want}",
                        )

    def test_native_house_systems_match_fixture_warnings(self):
        case = _load("houses/cusps.json")["cases"][0]
        substituted = {name for name, value in case["systems"].items() if value["warnings"]}
        self.assertEqual(substituted, set(case["systems"]) - set(NATIVE_HOUSE_SYSTEMS))


class SubstitutionWarningContractTests(unittest.TestCase):
    def test_engine_warning_codes_match_rust(self):
        for case in _load("substitution-warnings.json")["engine"]:
            with self.subTest(case=case):
                self.assertEqual(
                    engine_substitution_warning(case["engine"], case["backend"]),
                    case["warning"],
                )


class AspectCatalogContractTests(unittest.TestCase):
    """D4: the Python built-in aspects equal contracts/catalogs/aspects.json."""

    def test_builtin_aspects_match_shared_catalog_exactly(self):
        catalog = _load("catalogs/aspects.json")
        self.assertEqual(ASPECT_CATALOG_VERSION, catalog["catalog_version"])
        self.assertEqual(ASPECT_ALIASES, catalog["aliases"])
        model = builtin_standard_model()
        self.assertEqual(
            [a.id for a in model.aspect_definitions],
            [entry["id"] for entry in catalog["aspects"]],
        )
        for definition, entry in zip(model.aspect_definitions, catalog["aspects"]):
            with self.subTest(aspect=entry["id"]):
                self.assertEqual(definition.angle, entry["angle"])  # bit-exact
                self.assertEqual(definition.default_orb, entry["default_orb"])
                self.assertEqual(definition.glyph, entry["label"])

    def test_aliases_point_to_canonical_ids(self):
        ids = {entry["id"] for entry in _load("catalogs/aspects.json")["aspects"]}
        for alias, canonical in ASPECT_ALIASES.items():
            self.assertNotIn(alias, ids)
            self.assertIn(canonical, ids)
            self.assertEqual(canonical_aspect_id(alias.upper()), canonical)
        self.assertEqual(canonical_aspect_id("MyCustom"), "MyCustom")


if __name__ == "__main__":
    unittest.main()
