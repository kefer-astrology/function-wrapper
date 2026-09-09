"""Rust/Python workspace YAML interoperability tests without compute extras."""

from pathlib import Path
import tempfile
import unittest

import yaml

from module.workspace import load_workspace, save_workspace_modular
from module.resolution import current_model_report


class WorkspaceInteropTests(unittest.TestCase):
    def test_python_loads_and_rewrites_the_shared_rust_contract_fixture(self):
        fixture = (
            Path(__file__).resolve().parents[2]
            / "tauri-application"
            / "contracts"
            / "workspace-v1"
        )
        ws = load_workspace(str(fixture / "workspace.yaml"))

        self.assertEqual(ws.schema_version, 1)
        self.assertEqual(ws.active_school, "traditional")
        self.assertEqual(ws.schools["traditional"].default_model, "traditional-test")
        self.assertEqual(ws.models["traditional-test"].school, "traditional")
        self.assertEqual(ws.charts[0].config.model_overrides.aspects[0].angle, 91.0)
        self.assertTrue(ws.transit_analyses[0].station_events)
        self.assertEqual(ws.presentation.glyph_set, "classic")

        report = current_model_report(ws, ws.charts[0].config)
        square = next(
            aspect for aspect in report.model.aspect_definitions
            if aspect.id == "square"
        )
        self.assertEqual(report.requested_school, "traditional")
        self.assertEqual(report.resolved_model, "traditional-test")
        self.assertEqual(square.angle, 91.0)
        self.assertEqual(square.default_orb, 2.0)
        self.assertEqual(square.interpretation_weight, 0.6)

        with tempfile.TemporaryDirectory() as directory:
            manifest_path = save_workspace_modular(ws, directory)
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(raw["schema_version"], 1)
            self.assertEqual(raw["active_school"], "traditional")
            self.assertIn("traditional-test", raw["models"])
            self.assertTrue(raw["model_overrides"]["points"][0]["computed"])
            self.assertEqual(raw["presentation"]["glyph_set"], "classic")
            self.assertEqual(len(raw["transit_analyses"]), 1)

            reopened = load_workspace(str(manifest_path))
            self.assertEqual(reopened.charts[0].roden_rating, "AA")
            self.assertEqual(reopened.transit_analyses[0].model, "traditional-test")


if __name__ == "__main__":
    unittest.main()
