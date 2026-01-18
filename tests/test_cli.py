"""
Tests for CLI handlers.
"""

# Suppress ResourceWarnings from jplephem/skyfield (Skyfield dependency) BEFORE imports
# These are harmless - SQLite connections are closed when objects are garbage collected
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

import unittest
import tempfile
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pytz

from module.workspace import init_workspace, load_workspace, add_chart, save_workspace_modular
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
        engine=EngineType.JPL,
        ephemeris_path=None,
        zodiac=ZodiacType.TROPICAL,
        house=HouseSystem.PLACIDUS,
    )


class TestCLI(unittest.TestCase):
    """Test CLI command handlers."""
    
    def setUp(self):
        """Set up test workspace."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name) / "ws"
        self.manifest_path = init_workspace(
            base_dir=self.base,
            owner="Tester",
            active_model="default",
            default_ephemeris={"name": "de421", "backend": "jpl"},
        )
        
        # Add a test chart
        ws = load_workspace(str(self.manifest_path))
        chart = _make_sample_chart(name="Test Chart")
        add_chart(ws, chart, base_dir=self.base)
        # Save workspace to update manifest so CLI can find the chart
        save_workspace_modular(ws, self.base)
        
        self.workspace_path = str(self.manifest_path)
        self.chart_id = "Test Chart"
    
    def tearDown(self):
        """Clean up."""
        self.tmpdir.cleanup()
    
    def _run_cli(self, command: str, args: dict) -> dict:
        """Run CLI command and return parsed JSON result."""
        args_json = json.dumps(args)
        cmd = [sys.executable, "-m", "module.cli", command, args_json]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode != 0 and not result.stdout:
            self.fail(f"CLI command failed: {result.stderr}")
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"Failed to parse JSON output: {e}\nOutput: {result.stdout}\nStderr: {result.stderr}")
    
    def test_compute_chart(self):
        """Test compute_chart command with JPL engine."""
        args = {
            "workspace_path": self.workspace_path,
            "chart_id": self.chart_id,
            "include_physical": False,
            "include_topocentric": False,
        }
        
        result = self._run_cli("compute_chart", args)
        
        self.assertNotIn("error", result, f"Error in result: {result}")
        self.assertIn("positions", result)
        self.assertIn("aspects", result)
        self.assertEqual(result["chart_id"], self.chart_id)
        
        # Check positions structure
        positions = result["positions"]
        self.assertIsInstance(positions, dict)
        self.assertGreater(len(positions), 0)
        
        # For JPL engine, positions should be extended format (dict)
        # Check first position to see format
        first_pos = next(iter(positions.values()))
        if isinstance(first_pos, dict):
            # Extended format (JPL)
            self.assertIn("longitude", first_pos)
            self.assertIn("distance", first_pos)
        else:
            # Simple format (non-JPL)
            self.assertIsInstance(first_pos, (int, float))
        
        # Check aspects structure
        aspects = result["aspects"]
        self.assertIsInstance(aspects, list)
    
    def test_compute_chart_kerykeion(self):
        """Test compute_chart command with Kerykeion engine."""
        # Create a chart with Kerykeion engine
        tz = pytz.timezone("Europe/Prague")
        dt = tz.localize(datetime(2024, 1, 1, 12, 0))
        loc = _make_sample_location()
        chart = prepare_horoscope(
            name="Kerykeion Test",
            dt=dt,
            loc=loc,
            engine=EngineType.SWISSEPH,  # Use Kerykeion
            ephemeris_path=None,
            zodiac=ZodiacType.TROPICAL,
            house=HouseSystem.PLACIDUS,
        )
        
        # Add to workspace
        ws = load_workspace(self.workspace_path)
        add_chart(ws, chart, base_dir=self.base)
        # Save workspace to update manifest
        save_workspace_modular(ws, self.base)
        
        args = {
            "workspace_path": self.workspace_path,
            "chart_id": "Kerykeion Test",
            "include_physical": False,
            "include_topocentric": False,
        }
        
        result = self._run_cli("compute_chart", args)
        
        self.assertNotIn("error", result, f"Error in result: {result}")
        self.assertIn("positions", result)
        
        # For Kerykeion, positions should be simple format (float)
        positions = result["positions"]
        if positions:
            first_pos = next(iter(positions.values()))
            # Kerykeion returns simple float longitude
            self.assertIsInstance(first_pos, (int, float))
    
    def test_compute_chart_not_found(self):
        """Test compute_chart with non-existent chart."""
        args = {
            "workspace_path": self.workspace_path,
            "chart_id": "NonExistent",
        }
        
        result = self._run_cli("compute_chart", args)
        
        self.assertIn("error", result)
        self.assertEqual(result["type"], "ChartNotFound")
    
    def test_get_workspace_settings(self):
        """Test get_workspace_settings command."""
        args = {
            "workspace_path": self.workspace_path,
        }
        
        result = self._run_cli("get_workspace_settings", args)
        
        self.assertNotIn("error", result)
        self.assertIn("owner", result)
        self.assertIn("active_model", result)
        self.assertIn("default", result)
        self.assertEqual(result["owner"], "Tester")
    
    def test_list_charts(self):
        """Test list_charts command."""
        args = {
            "workspace_path": self.workspace_path,
        }
        
        result = self._run_cli("list_charts", args)
        
        self.assertNotIn("error", result)
        self.assertIn("charts", result)
        self.assertIsInstance(result["charts"], list)
        self.assertGreater(len(result["charts"]), 0)
        
        # Check chart structure
        chart = result["charts"][0]
        self.assertIn("id", chart)
        self.assertIn("name", chart)
        self.assertIn("event_time", chart)
    
    def test_get_chart(self):
        """Test get_chart command."""
        args = {
            "workspace_path": self.workspace_path,
            "chart_id": self.chart_id,
        }
        
        result = self._run_cli("get_chart", args)
        
        self.assertNotIn("error", result)
        self.assertIn("id", result)
        self.assertIn("subject", result)
        self.assertIn("config", result)
        self.assertEqual(result["id"], self.chart_id)
    
    def test_get_chart_not_found(self):
        """Test get_chart with non-existent chart."""
        args = {
            "workspace_path": self.workspace_path,
            "chart_id": "NonExistent",
        }
        
        result = self._run_cli("get_chart", args)
        
        self.assertIn("error", result)
        self.assertEqual(result["type"], "ChartNotFound")
    
    def test_compute_transit_series(self):
        """Test compute_transit_series command - adds ONE chart and computes."""
        args = {
            "workspace_path": self.workspace_path,
            "source_chart_id": self.chart_id,
            "start_datetime": "2024-01-01T00:00:00+01:00",
            "end_datetime": "2024-01-01T12:00:00+01:00",
            "time_step": "1 hour",
        }
        
        result = self._run_cli("compute_transit_series", args)
        
        self.assertNotIn("error", result, f"Error in result: {result}")
        self.assertIn("source_chart_id", result)
        self.assertIn("time_range", result)
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)
        self.assertGreater(len(result["results"]), 0)
        
        # Check result entry structure
        entry = result["results"][0]
        self.assertIn("datetime", entry)
        self.assertIn("transit_positions", entry)
        self.assertIn("aspects", entry)


if __name__ == "__main__":
    unittest.main()
