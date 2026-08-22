"""Contract tests for the Python implementation of the Rust model boundary."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from module.astronomy import (
    ChartData,
    compute_normalized_chart_aspects,
    compute_normalized_cross_aspects,
)
from module.cli import _build_chart_response_from_chart_data
from module.event_time import parse_event_time
from module.model_catalog import builtin_standard_model
from module.models import (
    AspectDefinition,
    ChartConfig,
    ChartMode,
    ChartPreset,
    EngineType,
    HouseSystem,
    SettingSource,
    Workspace,
    WorkspaceDefaults,
    ZodiacType,
)
from module.resolution import (
    current_model_report,
    resolve_preset,
    settings_layer_from_dict,
)
from module.utils import parse_chart_config
from module.workspace import load_workspace_aggregate


def chart_config(**changes):
    values = {
        "mode": ChartMode.NATAL,
        "house_system": None,
        "zodiac_type": ZodiacType.TROPICAL,
        "included_points": [],
        "aspect_orbs": {},
        "display_style": "default",
        "color_theme": "default",
    }
    values.update(changes)
    return ChartConfig(**values)


def workspace(**changes):
    values = {
        "owner": "test",
        "subjects": [],
        "charts": [],
        "chart_presets": [],
        "layouts": [],
        "annotations": [],
        "active_model": "standard",
        "models": {"standard": builtin_standard_model()},
    }
    values.update(changes)
    return Workspace(**values)


class PythonContractParityTests(unittest.TestCase):
    def test_shared_event_time_fixture_matches_rust_contract(self):
        fixture_path = (
            Path(__file__).resolve().parents[2]
            / "tauri-application"
            / "contracts"
            / "event-time.json"
        )
        if not fixture_path.exists():
            fixture_path = (
                Path(__file__).resolve().parents[2]
                / "contracts"
                / "event-time.json"
            )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        for case in fixture["accepted"]:
            self.assertEqual(
                parse_event_time(case["input"]).isoformat(),
                case["utc"],
            )
        for value in fixture["rejected"]:
            with self.assertRaisesRegex(ValueError, "^invalid_event_time:"):
                parse_event_time(value)

    def test_typed_chart_result_includes_motion_and_lunar_details(self):
        chart = SimpleNamespace(
            config=SimpleNamespace(
                engine=EngineType.JPL,
                override_ephemeris=None,
            )
        )
        result = _build_chart_response_from_chart_data(
            chart,
            ChartData(
                positions={
                    "sun": {"longitude": 0.0, "speed": 1.0},
                    "moon": {
                        "longitude": 90.0,
                        "speed": 13.0,
                        "retrograde": False,
                    },
                }
            ),
            [],
            "typed-chart",
            False,
        )

        self.assertIn("motion", result)
        self.assertEqual(result["motion"]["moon"]["speed"], 13.0)
        self.assertEqual(result["moon_details"]["phase_id"], "first_quarter")
        self.assertAlmostEqual(
            result["moon_details"]["illuminated_fraction"], 0.5
        )

    def test_strict_workspace_loader_retains_reference_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "workspace.yaml"
            manifest.write_text(
                "\n".join([
                    "owner: Tester",
                    "active_model: standard",
                    "default: {}",
                    "charts:",
                    "  - charts/missing.yml",
                    "subjects: []",
                    "chart_presets: []",
                    "layouts: []",
                    "annotations: []",
                ]),
                encoding="utf-8",
            )
            loaded = load_workspace_aggregate(str(manifest))
            report = loaded.validation_report()

        self.assertFalse(report.valid)
        self.assertEqual(report.counts.charts, 0)
        self.assertIn(
            "referenced_item_load_failed",
            {diagnostic.code for diagnostic in report.diagnostics},
        )

    def test_strict_workspace_loader_reports_missing_event_time(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "workspace.yaml"
            manifest.write_text(
                json.dumps({
                    "owner": "Tester",
                    "active_model": "standard",
                    "default": {},
                    "charts": [{
                        "id": "missing-time",
                        "subject": {
                            "id": "subject",
                            "name": "Subject",
                            "location": {
                                "name": "Prague",
                                "latitude": 50.08,
                                "longitude": 14.42,
                                "timezone": "Europe/Prague",
                            },
                        },
                        "config": {},
                    }],
                    "subjects": [],
                    "chart_presets": [],
                    "layouts": [],
                    "annotations": [],
                }),
                encoding="utf-8",
            )
            report = load_workspace_aggregate(str(manifest)).validation_report()

        self.assertFalse(report.valid)
        self.assertIn(
            "subject_event_time_missing",
            {diagnostic.code for diagnostic in report.diagnostics},
        )

    def test_shared_resolution_fixture_matches_rust_contract(self):
        fixture_path = (
            Path(__file__).resolve().parents[2]
            / "tauri-application"
            / "contracts"
            / "settings-resolution.json"
        )
        if not fixture_path.exists():
            fixture_path = (
                Path(__file__).resolve().parents[2]
                / "contracts"
                / "settings-resolution.json"
            )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        workspace_layer = settings_layer_from_dict(fixture["workspace"])
        ws = workspace(
            default=WorkspaceDefaults(
                default_house_system=workspace_layer.house_system,
                default_bodies=workspace_layer.bodies,
                default_aspects=workspace_layer.aspects,
                default_aspect_orbs=workspace_layer.aspect_orbs,
                ephemeris_engine=workspace_layer.engine,
                time_system=workspace_layer.time_system,
            )
        )
        report = current_model_report(
            ws,
            parse_chart_config(fixture["chart"]),
            settings_layer_from_dict(fixture["preset"]),
            settings_layer_from_dict(fixture["operation"]),
        )
        settings = report.effective_settings
        expected = fixture["expected"]

        self.assertEqual(settings.default_house_system.value, expected["houseSystem"])
        self.assertEqual(settings.default_bodies, expected["bodies"])
        self.assertEqual(settings.default_aspects, expected["aspects"])
        self.assertEqual(settings.engine.value, expected["engine"])
        self.assertEqual(settings.zodiac_type.value, expected["zodiacType"])
        self.assertEqual(settings.ayanamsa.value, expected["ayanamsa"])
        self.assertEqual(settings.time_system.value, expected["timeSystem"])
        for aspect_id, orb in expected["aspectOrbs"].items():
            self.assertEqual(settings.aspect_orbs[aspect_id], orb)
        self.assertEqual(
            settings.sources.default_house_system.value,
            expected["sources"]["houseSystem"],
        )
        self.assertEqual(
            settings.sources.default_bodies.value,
            expected["sources"]["bodies"],
        )
        self.assertEqual(
            settings.sources.default_aspects.value,
            expected["sources"]["aspects"],
        )
        for aspect_id, source in expected["sources"]["aspectOrbs"].items():
            self.assertEqual(settings.sources.aspect_orbs[aspect_id].value, source)

    def test_builtin_catalog_matches_canonical_shape(self):
        model = builtin_standard_model()
        self.assertEqual(len(model.body_definitions), 25)
        self.assertEqual(len(model.aspect_definitions), 17)
        self.assertEqual(len(model.signs), 12)
        self.assertEqual(model.settings.degrees_in_circle, 360.0)
        self.assertIn("north_node", model.settings.default_bodies)

    def test_precedence_and_sources_include_explicit_empty_lists(self):
        ws = workspace(
            default=WorkspaceDefaults(
                default_house_system=HouseSystem.WHOLE_SIGN,
                default_bodies=["sun", "moon"],
                default_aspects=["conjunction", "square"],
            ),
            chart_presets=[
                ChartPreset(
                    name="minimal",
                    config=chart_config(
                        observable_objects=["sun"],
                        selected_aspects=["square"],
                    ),
                )
            ],
        )
        chart = chart_config(
            observable_objects=["moon"],
            selected_aspects=["trine"],
        )
        operation = settings_layer_from_dict(
            {
                "bodies": [],
                "aspects": [],
                "aspectOrbs": {"square": 2.0},
                "engine": "jpl",
            }
        )
        report = current_model_report(
            ws, chart, resolve_preset(ws, "minimal"), operation
        )

        self.assertEqual(report.effective_settings.default_bodies, [])
        self.assertEqual(report.effective_settings.default_aspects, [])
        self.assertEqual(report.effective_settings.aspect_orbs["square"], 2.0)
        self.assertEqual(report.effective_settings.engine, EngineType.JPL)
        self.assertEqual(
            report.effective_settings.sources.default_bodies,
            SettingSource.OPERATION,
        )
        self.assertEqual(
            report.effective_settings.sources.default_house_system,
            SettingSource.WORKSPACE,
        )

    def test_diagnostics_reject_unknown_effective_selection(self):
        report = current_model_report(
            workspace(),
            chart_config(),
            operation=settings_layer_from_dict({"bodies": ["not_a_body"]}),
        )
        self.assertIn(
            "unknown_selected_body",
            {diagnostic.code for diagnostic in report.diagnostics},
        )

    def test_model_defined_aspects_drive_radix_and_cross_chart_detection(self):
        custom = AspectDefinition(
            id="semisextile",
            glyph="⚺",
            angle=30.0,
            default_orb=1.0,
            i18n={"en": "Semisextile"},
        )
        radix = compute_normalized_chart_aspects(
            {"sun": 0.0, "moon": 30.5},
            selected_aspects=["semisextile"],
            aspect_definitions=[custom],
        )
        cross = compute_normalized_cross_aspects(
            {"sun": 0.0},
            {"moon": 30.5},
            selected_aspects=["semisextile"],
            aspect_definitions=[custom],
        )
        self.assertEqual(radix[0]["type"], "semisextile")
        self.assertEqual(cross[0]["from"], "sun")
        self.assertEqual(cross[0]["to"], "moon")

    def test_model_validation_reports_duplicate_identifiers(self):
        model = builtin_standard_model()
        model.body_definitions.append(deepcopy(model.body_definitions[0]))
        report = current_model_report(
            workspace(models={"standard": model}),
            chart_config(),
        )
        self.assertIn(
            "duplicate_body_id",
            {diagnostic.code for diagnostic in report.diagnostics},
        )


if __name__ == "__main__":
    unittest.main()
