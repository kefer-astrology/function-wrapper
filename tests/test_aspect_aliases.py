"""D4 regression: legacy aspect ids resolve to canonical ids in every layer.

Python used `semisquare`/`sesquiquadrate` for 45/135 degrees; Rust (and the
shared catalog) use `octile`/`trioctile`. A Rust-saved `octile` selection
used to raise `unknown_selected_aspect` in Python and never be detected.
"""

import unittest
from copy import deepcopy

from module.astronomy import compute_normalized_chart_aspects, compute_normalized_cross_aspects
from module.model_catalog import builtin_standard_model
from module.models import (
    BaseChartPurpose,
    ChartConfig,
    ChartDefinition,
    Workspace,
    WorkspaceDefaults,
    ZodiacType,
)
from module.resolution import canonicalize_model_aspect_ids, current_model_report


def chart_config(**changes):
    values = {
        "definition": ChartDefinition(kind="base", purpose=BaseChartPurpose.NATAL),
        "house_system": None,
        "zodiac_type": ZodiacType.TROPICAL,
        "aspect_orbs": {},
    }
    values.update(changes)
    return ChartConfig(**values)


def workspace(**changes):
    values = {
        "owner": "test", "subjects": [], "charts": [], "chart_presets": [],
        "layouts": [], "annotations": [], "active_model": "standard",
        "models": {"standard": builtin_standard_model()},
    }
    values.update(changes)
    return Workspace(**values)


class AspectAliasResolutionTests(unittest.TestCase):
    def test_rust_saved_octile_is_known_and_detected(self):
        report = current_model_report(workspace(), chart_config(selected_aspects=["octile"]))
        self.assertEqual(report.effective_settings.default_aspects, ["octile"])
        self.assertFalse([d for d in report.diagnostics if "aspect" in d.code])

    def test_legacy_aliases_in_every_layer_resolve_with_layer_precedence(self):
        ws = workspace(default=WorkspaceDefaults(
            default_aspects=["semisquare", "trine"],
            default_aspect_orbs={"sesquiquadrate": 2.5},
        ))
        config = chart_config(
            selected_aspects=["Semisquare", "octile"],
            aspect_orbs={"semisquare": 0.75},
        )
        report = current_model_report(ws, config)
        settings = report.effective_settings
        self.assertEqual(settings.default_aspects, ["octile"])
        self.assertEqual(settings.aspect_orbs["octile"], 0.75)  # chart alias beats model default
        self.assertEqual(settings.aspect_orbs["trioctile"], 2.5)
        self.assertNotIn("semisquare", settings.aspect_orbs)
        self.assertFalse([d for d in report.diagnostics if "aspect" in d.code], report.diagnostics)

    def test_detectors_accept_aliases_and_emit_canonical_types(self):
        definitions = builtin_standard_model().aspect_definitions
        positions = {"sun": 0.0, "mars": 45.2, "saturn": 135.1}
        found = compute_normalized_chart_aspects(
            positions,
            selected_aspects=["semisquare", "SESQUIQUADRATE"],
            aspect_definitions=definitions,
        )
        self.assertEqual({a["type"] for a in found}, {"octile", "trioctile"})
        cross = compute_normalized_cross_aspects(
            {"mars": 45.2}, {"sun": 0.0},
            aspect_orbs={"semisquare": 0.1},
            selected_aspects=["semisquare"],
            aspect_definitions=definitions,
        )
        self.assertEqual(cross, [])  # the alias orb (0.1) applies to octile

    def test_workspace_model_with_legacy_id_is_canonicalized(self):
        model = builtin_standard_model("legacy")
        octile = next(a for a in model.aspect_definitions if a.id == "octile")
        object.__setattr__(octile, "id", "semisquare")
        object.__setattr__(octile, "default_orb", 2.0)
        canonical = canonicalize_model_aspect_ids(deepcopy(model))
        ids = [a.id for a in canonical.aspect_definitions]
        self.assertIn("octile", ids)
        self.assertNotIn("semisquare", ids)
        self.assertEqual(next(a for a in canonical.aspect_definitions if a.id == "octile").default_orb, 2.0)

    def test_default_orbs_are_the_canonical_rust_values(self):
        orbs = {a.id: a.default_orb for a in builtin_standard_model().aspect_definitions}
        self.assertEqual(
            (orbs["square"], orbs["trine"], orbs["sextile"], orbs["quincunx"], orbs["octile"]),
            (6.0, 6.0, 5.0, 2.0, 1.5),
        )


if __name__ == "__main__":
    unittest.main()
