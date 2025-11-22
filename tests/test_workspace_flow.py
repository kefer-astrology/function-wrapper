import unittest
import tempfile
from pathlib import Path
from datetime import datetime
import yaml
import pytz

from module.workspace import init_workspace, load_workspace, save_workspace_modular, add_chart
from module.utils import prepare_horoscope
from module.models import Location, EngineType, HouseSystem, ZodiacType


def _make_sample_location() -> Location:
    return Location(
        name="Prague, CZ",
        latitude=50.0875,
        longitude=14.4214,
        timezone="Europe/Prague",
    )


def _make_sample_chart(name: str = "Sample"):
    tz = pytz.timezone("Europe/Prague")
    dt = tz.localize(datetime(2024, 1, 1, 12, 0))
    loc = _make_sample_location()
    return prepare_horoscope(
        name=name,
        dt=dt,
        loc=loc,
        engine=EngineType.JPL,  # stored in config only for this test
        ephemeris_path=None,
        zodiac=ZodiacType.TROPICAL,
        house=HouseSystem.PLACIDUS,
    )


class TestWorkspaceFlow(unittest.TestCase):
    def test_workspace_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "ws"
            manifest_path = init_workspace(
                base_dir=base,
                owner="Tester",
                active_model="default",
                default_ephemeris={"name": "de421", "backend": "jpl"},
            )
            # Folders
            self.assertTrue((base / "subjects").is_dir())
            self.assertTrue((base / "charts").is_dir())
            self.assertTrue((base / "layouts").is_dir())
            self.assertTrue((base / "annotations").is_dir())
            self.assertTrue((base / "presets").is_dir())
            # Manifest
            self.assertTrue(manifest_path.exists())
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(data["owner"], "Tester")
            self.assertEqual(data["active_model"], "default")
            self.assertEqual(data["default_ephemeris"]["name"], "de421")
            self.assertEqual(data["default_ephemeris"]["backend"], "jpl")
            self.assertIsInstance(data["charts"], list)
            self.assertEqual(len(data["charts"]), 0)

    def test_chart_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "ws"
            init_workspace(
                base_dir=base,
                owner="Tester",
                active_model="default",
                default_ephemeris={"name": "de421", "backend": "jpl"},
            )
            ws = load_workspace(str(base / "workspace.yaml"))
            chart = _make_sample_chart(name="Johannes Kepler")
            rel_path = add_chart(ws, chart, base_dir=base)
            # File written
            self.assertTrue((base / rel_path).exists())
            # Save modular & reload
            save_workspace_modular(ws, base)
            ws2 = load_workspace(str(base / "workspace.yaml"))
            self.assertTrue(ws2.charts and len(ws2.charts) == 1)
            self.assertEqual(ws2.charts[0].id, "Johannes Kepler")

    def test_workspace_setting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "ws"
            init_workspace(
                base_dir=base,
                owner="OwnerName",
                active_model="hellenic",
                default_ephemeris={"name": "de431", "backend": "jpl"},
            )
            ws = load_workspace(str(base / "workspace.yaml"))
            # Basic settings present
            self.assertEqual(ws.owner, "OwnerName")
            self.assertEqual(ws.active_model, "hellenic")
            self.assertEqual(ws.default_ephemeris.name, "de431")
            self.assertEqual(ws.default_ephemeris.backend, "jpl")
            # Add a chart and ensure it surfaces in workspace traversal
            chart = _make_sample_chart(name="Sample A")
            add_chart(ws, chart, base_dir=base)
            save_workspace_modular(ws, base)
            ws_ref = load_workspace(str(base / "workspace.yaml"))
            self.assertEqual(len(ws_ref.charts), 1)
            self.assertEqual(ws_ref.charts[0].subject.name, "Sample A")


if __name__ == "__main__":
    unittest.main()
