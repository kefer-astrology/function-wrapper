"""
Comprehensive test suite covering all functionality:
- Date, place, location parsing
- Engine functionality (Skyfield/JPL, Kerykeion)
- Workspace flow (including StarFisher import)
- CLI accessibility
- Chart computation with timestamps
- Sample workspace creation
"""

# Suppress ResourceWarnings from jplephem/skyfield (Skyfield dependency) BEFORE imports
# These are harmless - SQLite connections are closed when objects are garbage collected
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

import unittest
import tempfile
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import yaml

from module.workspace import init_workspace, load_workspace, save_workspace_modular, add_chart
from module.utils import prepare_horoscope, Actual, parse_sfs_content, _read_text_with_fallbacks
from module.models import Location, EngineType, HouseSystem, ZodiacType
from module.services import compute_positions_for_chart, compute_positions, get_active_model
try:
    from module.storage import DuckDBStorage, get_storage_path
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    DuckDBStorage = None
    get_storage_path = None
try:
    from module.cli import cmd_compute_chart
except ImportError:
    # Fallback if CLI not available
    def cmd_compute_chart(args):
        return {"error": "CLI not available"}


def _make_sample_location() -> Location:
    """Create a sample location (Prague)."""
    return Location(
        name="Prague, CZ",
        latitude=50.0875,
        longitude=14.4214,
        timezone="Europe/Prague",
    )


def _make_sample_chart(name: str, dt: datetime, loc: Location, engine: EngineType = EngineType.JPL):
    """Create a sample chart."""
    return prepare_horoscope(
        name=name,
        dt=dt,
        loc=loc,
        engine=engine,
        ephemeris_path=None,
        zodiac=ZodiacType.TROPICAL,
        house=HouseSystem.PLACIDUS,
    )


class TestComprehensive(unittest.TestCase):
    """Comprehensive test suite for all functionality."""
    
    def setUp(self):
        """Set up test workspace in tests/sample directory."""
        # Aggressively suppress ResourceWarnings (they come from skyfield/jplephem)
        warnings.simplefilter("ignore", ResourceWarning)
        
        self.test_base = Path(__file__).parent / "sample"
        self.test_base.mkdir(exist_ok=True)
        
        # Clean up existing charts directory to avoid accumulation
        charts_dir = self.test_base / "charts"
        if charts_dir.exists():
            for chart_file in charts_dir.glob("*.yml"):
                chart_file.unlink()
        
        # Create or reinitialize workspace (this will overwrite workspace.yaml)
        self.manifest_path = init_workspace(
            base_dir=self.test_base,
            owner="Test User",
            active_model="default",
            default_ephemeris={"name": "de421", "backend": "jpl"},
        )
        
        # Load workspace
        self.ws = load_workspace(str(self.manifest_path))
        
        # Test location and time
        self.tz = pytz.timezone("Europe/Prague")
        self.base_time = self.tz.localize(datetime(2024, 1, 1, 12, 0, 0))
        self.loc = _make_sample_location()
    
    def _reload_workspace(self):
        """Reload workspace from disk to ensure sync."""
        self.ws = load_workspace(str(self.manifest_path))
    
    def tearDown(self):
        """Clean up - keep sample directory for inspection."""
        # Don't delete - keep for inspection
        pass
    
    def test_01_date_place_location_parsing(self):
        """Test date, place, and location parsing utilities."""
        # Test Actual date parsing
        dt_str = "2024-01-01T12:00:00+01:00"
        actual_date = Actual(dt_str, t="date")
        self.assertIsInstance(actual_date.value, datetime)
        
        # Test Actual location parsing
        loc_str = "Prague, CZ"
        actual_loc = Actual(loc_str, t="loc")
        # Location might be from geopy or our models - check it has expected attributes
        self.assertIsNotNone(actual_loc.value)
        self.assertTrue(hasattr(actual_loc.value, 'name') or hasattr(actual_loc.value, 'latitude'))
        # If it's our Location model, check name; otherwise check it has coordinates
        if hasattr(actual_loc.value, 'name'):
            self.assertIn("Prague", actual_loc.value.name)
        if hasattr(actual_loc.value, 'latitude'):
            self.assertIsNotNone(actual_loc.value.latitude)
        
        # Test timezone handling
        self.assertTrue(actual_date.value.tzinfo is not None)
    
    def test_02_workspace_initialization(self):
        """Test workspace initialization with standardized settings."""
        # Check directory structure
        self.assertTrue((self.test_base / "subjects").is_dir())
        self.assertTrue((self.test_base / "charts").is_dir())
        self.assertTrue((self.test_base / "layouts").is_dir())
        self.assertTrue((self.test_base / "annotations").is_dir())
        self.assertTrue((self.test_base / "presets").is_dir())
        
        # Check manifest exists
        self.assertTrue(self.manifest_path.exists())
        
        # Check manifest content
        data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data["owner"], "Test User")
        self.assertEqual(data["active_model"], "default")
        self.assertIn("default", data)
        self.assertIn("ephemeris_engine", data["default"])
        self.assertIn("ephemeris_backend", data["default"])
        self.assertIn("language", data["default"])
        self.assertIn("theme", data["default"])
        
        # Check workspace object
        self.assertEqual(self.ws.owner, "Test User")
        self.assertEqual(self.ws.active_model, "default")
        self.assertIsNotNone(self.ws.default)
    
    def test_03_jpl_engine_functionality(self):
        """Test JPL/Skyfield engine functionality."""
        chart = _make_sample_chart("JPL Test", self.base_time, self.loc, EngineType.JPL)
        
        # Compute positions
        positions = compute_positions_for_chart(chart, ws=self.ws)
        
        self.assertIsInstance(positions, dict)
        self.assertGreater(len(positions), 0)
        
        # Check extended format for JPL
        first_pos = next(iter(positions.values()))
        if isinstance(first_pos, dict):
            # Extended format
            self.assertIn("longitude", first_pos)
            self.assertIn("distance", first_pos)
            self.assertIn("declination", first_pos)
            self.assertIn("right_ascension", first_pos)
            
            # Validate longitude
            lon = first_pos["longitude"]
            self.assertGreaterEqual(lon, 0.0)
            self.assertLess(lon, 360.0)
    
    def test_04_kerykeion_engine_functionality(self):
        """Test Kerykeion engine functionality."""
        chart = _make_sample_chart("Kerykeion Test", self.base_time, self.loc, EngineType.SWISSEPH)
        
        # Compute positions
        positions = compute_positions_for_chart(chart, ws=self.ws)
        
        self.assertIsInstance(positions, dict)
        self.assertGreater(len(positions), 0)
        
        # Kerykeion returns simple float format
        first_pos = next(iter(positions.values()))
        self.assertIsInstance(first_pos, (int, float))
        self.assertGreaterEqual(first_pos, 0.0)
        self.assertLess(first_pos, 360.0)
    
    def test_05_workspace_chart_creation(self):
        """Test creating and saving charts in workspace."""
        chart = _make_sample_chart("Test Chart", self.base_time, self.loc)
        
        # Add chart to workspace
        rel_path = add_chart(self.ws, chart, base_dir=self.test_base)
        
        # Check file was created
        self.assertTrue((self.test_base / rel_path).exists())
        
        # Save workspace
        save_workspace_modular(self.ws, self.test_base)
        
        # Reload and verify
        self._reload_workspace()
        self.assertGreater(len(self.ws.charts), 0)
        self.assertEqual(self.ws.charts[0].id, "Test Chart")
    
    def test_06_starfisher_import(self):
        """Test StarFisher file import."""
        # Check if sample StarFisher file exists
        sfs_path = Path(__file__).parent.parent / "source" / "starfisher_sample.sfs"
        if not sfs_path.exists():
            self.skipTest("StarFisher sample file not found")
        
        # Parse StarFisher file using encoding fallback (handles UTF-8, UTF-16, etc.)
        content = _read_text_with_fallbacks(sfs_path)
        if content is None:
            self.skipTest(f"Could not decode StarFisher file {sfs_path} with known encodings")
        
        model, display_config = parse_sfs_content(content)
        
        # Verify model structure
        self.assertIsNotNone(model)
        self.assertIsNotNone(model.settings)
        self.assertGreater(len(model.body_definitions), 0)
        self.assertGreater(len(model.aspect_definitions), 0)
        self.assertGreater(len(model.signs), 0)
        
        # Verify settings
        self.assertIsNotNone(model.settings.default_house_system)
        self.assertIsNotNone(model.settings.standard_orb)
        # Check constants are present
        self.assertEqual(model.settings.degrees_in_circle, 360.0)
        self.assertEqual(model.settings.obliquity_j2000, 23.4392911)
        self.assertEqual(model.settings.coordinate_tolerance, 0.0001)
    
    def test_07_cli_accessibility(self):
        """Test CLI is accessible and functional."""
        # Reload workspace to get current state
        self._reload_workspace()
        
        # Add ONE chart for CLI test (don't accumulate)
        chart = _make_sample_chart("CLI Test Chart", self.base_time, self.loc)
        add_chart(self.ws, chart, base_dir=self.test_base)
        save_workspace_modular(self.ws, self.test_base)
        self._reload_workspace()
        
        # Test CLI command
        args = {
            "workspace_path": str(self.manifest_path),
            "chart_id": "CLI Test Chart",
            "include_physical": False,
            "include_topocentric": False,
        }
        
        result = cmd_compute_chart(args)
        
        self.assertNotIn("error", result)
        self.assertIn("positions", result)
        self.assertIn("aspects", result)
        self.assertEqual(result["chart_id"], "CLI Test Chart")
    
    def test_08_chart_computation_exact_timestamp(self):
        """Test chart computation with exact timestamp and default location."""
        # Reload workspace to get current state
        self._reload_workspace()
        
        # Create chart with exact timestamp
        exact_time = self.tz.localize(datetime(2024, 1, 1, 12, 0, 0))
        chart = _make_sample_chart("Exact Time Chart", exact_time, self.loc)
        
        # Add to workspace
        add_chart(self.ws, chart, base_dir=self.test_base)
        save_workspace_modular(self.ws, self.test_base)
        self._reload_workspace()
        
        # Compute positions
        positions = compute_positions_for_chart(chart, ws=self.ws)
        
        self.assertIsInstance(positions, dict)
        self.assertGreater(len(positions), 0)
        
        # Verify we have expected planets
        expected_planets = ["sun", "moon", "mercury", "venus", "mars"]
        for planet in expected_planets:
            if planet in positions:
                pos = positions[planet]
                if isinstance(pos, dict):
                    lon = pos.get("longitude", pos)
                else:
                    lon = pos
                self.assertGreaterEqual(lon, 0.0)
                self.assertLess(lon, 360.0)
    
    def test_09_chart_computation_time_offset(self):
        """Test chart computation with +1 hour offset."""
        # Create chart at base time
        chart1 = _make_sample_chart("Base Time Chart", self.base_time, self.loc)
        positions1 = compute_positions_for_chart(chart1, ws=self.ws)
        
        # Create chart at +1 hour
        offset_time = self.base_time + timedelta(hours=1)
        chart2 = _make_sample_chart("Offset Time Chart", offset_time, self.loc)
        positions2 = compute_positions_for_chart(chart2, ws=self.ws)
        
        # Both should have positions
        self.assertGreater(len(positions1), 0)
        self.assertGreater(len(positions2), 0)
        
        # Positions should be different (moon moves ~0.5° per hour)
        if "moon" in positions1 and "moon" in positions2:
            moon1 = positions1["moon"]
            moon2 = positions2["moon"]
            
            # Extract longitude
            if isinstance(moon1, dict):
                lon1 = moon1.get("longitude", 0)
            else:
                lon1 = moon1
            if isinstance(moon2, dict):
                lon2 = moon2.get("longitude", 0)
            else:
                lon2 = moon2
            
            # Moon should have moved (at least 0.3° in 1 hour)
            diff = abs(lon2 - lon1)
            if diff > 180:
                diff = 360 - diff
            self.assertGreater(diff, 0.3, "Moon should move in 1 hour")
    
    def test_10_sample_workspace_structure(self):
        """Test that sample workspace has correct structure for inspection."""
        # Reload workspace to get current state
        self._reload_workspace()
        
        # Add exactly 2 charts for final structure test
        chart1 = _make_sample_chart("Chart 1", self.base_time, self.loc)
        chart2 = _make_sample_chart("Chart 2", self.base_time + timedelta(hours=1), self.loc)
        
        add_chart(self.ws, chart1, base_dir=self.test_base)
        add_chart(self.ws, chart2, base_dir=self.test_base)
        
        # Save workspace
        save_workspace_modular(self.ws, self.test_base)
        
        # Reload and verify
        self._reload_workspace()
        
        # Verify structure
        self.assertTrue((self.test_base / "workspace.yaml").exists())
        self.assertTrue((self.test_base / "charts").is_dir())
        self.assertTrue((self.test_base / "subjects").is_dir())
        
        # Verify charts directory has files
        chart_files = list((self.test_base / "charts").glob("*.yml"))
        self.assertEqual(len(chart_files), 2, f"Expected exactly 2 charts, found {len(chart_files)}")
        
        # Verify workspace is in sync
        self.assertEqual(len(self.ws.charts), 2, f"Workspace should have exactly 2 charts, found {len(self.ws.charts)}")
    
    def test_11_engine_comparison(self):
        """Test that both engines produce reasonable results."""
        chart_jpl = _make_sample_chart("JPL", self.base_time, self.loc, EngineType.JPL)
        chart_kery = _make_sample_chart("Kerykeion", self.base_time, self.loc, EngineType.SWISSEPH)
        
        pos_jpl = compute_positions_for_chart(chart_jpl, ws=self.ws)
        pos_kery = compute_positions_for_chart(chart_kery, ws=self.ws)
        
        # Both should have positions
        self.assertGreater(len(pos_jpl), 0)
        self.assertGreater(len(pos_kery), 0)
        
        # Compare common planets
        common_planets = ["sun", "moon", "mercury", "venus", "mars"]
        for planet in common_planets:
            if planet in pos_jpl and planet in pos_kery:
                jpl_lon = pos_jpl[planet]
                kery_lon = pos_kery[planet]
                
                # Extract longitude
                if isinstance(jpl_lon, dict):
                    jpl_lon = jpl_lon.get("longitude", 0)
                if isinstance(kery_lon, dict):
                    kery_lon = kery_lon.get("longitude", 0)
                
                # Should be within 5 degrees (different algorithms)
                diff = abs(jpl_lon - kery_lon)
                if diff > 180:
                    diff = 360 - diff
                self.assertLess(diff, 5.0, f"{planet} positions should be close")
    
    @unittest.skipUnless(STORAGE_AVAILABLE, "duckdb not available")
    def test_12_storage_and_parquet_export(self):
        """Test storing computed data in DuckDB and exporting to Parquet."""
        # Reload workspace to get current state
        self._reload_workspace()
        
        # Create charts and compute positions
        chart1 = _make_sample_chart("Storage Test 1", self.base_time, self.loc)
        chart2 = _make_sample_chart("Storage Test 2", self.base_time + timedelta(hours=1), self.loc)
        
        # Add to workspace
        add_chart(self.ws, chart1, base_dir=self.test_base)
        add_chart(self.ws, chart2, base_dir=self.test_base)
        save_workspace_modular(self.ws, self.test_base)
        self._reload_workspace()
        
        # Compute positions
        pos1 = compute_positions_for_chart(chart1, ws=self.ws)
        pos2 = compute_positions_for_chart(chart2, ws=self.ws)
        
        # Get storage path
        db_path = get_storage_path(str(self.manifest_path))
        data_dir = db_path.parent
        
        # Store positions in DuckDB
        with DuckDBStorage(db_path, create_schema=True) as storage:
            # Store first chart
            dt1_str = chart1.subject.event_time.isoformat()
            cfg1 = getattr(chart1, 'config', None)
            engine1 = cfg1.engine.value if cfg1 and cfg1.engine else None
            eph1 = cfg1.override_ephemeris if cfg1 else None
            
            storage.store_positions(
                chart1.id,
                dt1_str,
                pos1,
                engine=engine1,
                ephemeris_file=eph1
            )
            
            # Store second chart
            dt2_str = chart2.subject.event_time.isoformat()
            cfg2 = getattr(chart2, 'config', None)
            engine2 = cfg2.engine.value if cfg2 and cfg2.engine else None
            eph2 = cfg2.override_ephemeris if cfg2 else None
            
            storage.store_positions(
                chart2.id,
                dt2_str,
                pos2,
                engine=engine2,
                ephemeris_file=eph2
            )
            
            # Verify data was stored
            result = storage.conn.execute(
                "SELECT COUNT(*) FROM computed_positions"
            ).fetchone()
            self.assertGreater(result[0], 0, "Positions should be stored in DuckDB")
            
            # Export to Parquet
            parquet_dir = data_dir / "parquet"
            parquet_files = storage.export_to_parquet(
                parquet_dir,
                partition_by_date=True
            )
            
            self.assertGreater(len(parquet_files), 0, "Parquet files should be created")
            
            # Verify Parquet files exist
            for parquet_file in parquet_files:
                self.assertTrue(parquet_file.exists(), f"Parquet file should exist: {parquet_file}")
        
        # Verify database file exists
        self.assertTrue(db_path.exists(), f"DuckDB file should exist: {db_path}")
        
        # Verify Parquet directory exists
        self.assertTrue(parquet_dir.exists(), f"Parquet directory should exist: {parquet_dir}")
        
        # List Parquet files for inspection
        parquet_files_list = list(parquet_dir.glob("*.parquet"))
        self.assertGreater(len(parquet_files_list), 0, "Parquet files should be in directory")
        
        print(f"\n✅ Storage test passed:")
        print(f"   - DuckDB: {db_path}")
        print(f"   - Parquet files: {len(parquet_files_list)} files in {parquet_dir}")
        for pf in parquet_files_list:
            print(f"     - {pf.name} ({pf.stat().st_size} bytes)")


if __name__ == "__main__":
    unittest.main()
