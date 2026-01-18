"""
Tests for DuckDB storage module.
"""

import unittest
import tempfile
from pathlib import Path
from datetime import datetime
import pytz

try:
    from module.storage import DuckDBStorage, get_storage_path
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    DuckDBStorage = None
    get_storage_path = None


@unittest.skipUnless(STORAGE_AVAILABLE, "duckdb not available")
class TestDuckDBStorage(unittest.TestCase):
    """Test DuckDB storage functionality."""
    
    def setUp(self):
        """Set up test database."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        self.storage = DuckDBStorage(self.db_path, create_schema=True)
    
    def tearDown(self):
        """Clean up."""
        if self.storage:
            self.storage.close()
        self.tmpdir.cleanup()
    
    def test_create_schema(self):
        """Test schema creation."""
        # Schema should be created in __init__
        # Verify tables exist by querying
        result = self.storage.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [row[0] for row in result]
        
        self.assertIn('computed_positions', table_names)
        self.assertIn('computed_aspects', table_names)
    
    def test_store_positions_simple(self):
        """Test storing simple positions (float format)."""
        positions = {
            'sun': 45.5,
            'moon': 120.3,
            'mars': 200.7,
        }
        
        dt_str = '2024-01-01T12:00:00+01:00'
        self.storage.store_positions(
            'test_chart',
            dt_str,
            positions,
            engine='swisseph'
        )
        
        # Verify data
        result = self.storage.conn.execute(
            "SELECT object_id, longitude, distance, engine FROM computed_positions WHERE chart_id = 'test_chart'"
        ).fetchall()
        
        self.assertEqual(len(result), 3)
        # Check one position
        sun_row = next((r for r in result if r[0] == 'sun'), None)
        self.assertIsNotNone(sun_row)
        self.assertAlmostEqual(sun_row[1], 45.5, places=1)
        self.assertIsNone(sun_row[2])  # distance should be None for simple format
        self.assertEqual(sun_row[3], 'swisseph')
    
    def test_store_positions_extended(self):
        """Test storing extended positions (dict format)."""
        positions = {
            'sun': {
                'longitude': 45.5,
                'distance': 0.985,
                'declination': 15.2,
                'right_ascension': 45.8,
                'latitude': 0.0,
            },
            'moon': {
                'longitude': 120.3,
                'distance': 0.0025,
                'declination': 18.5,
                'right_ascension': 122.1,
                'latitude': 2.5,
            },
        }
        
        dt_str = '2024-01-01T12:00:00+01:00'
        self.storage.store_positions(
            'test_chart',
            dt_str,
            positions,
            engine='jpl',
            ephemeris_file='de421.bsp'
        )
        
        # Verify data
        result = self.storage.conn.execute(
            "SELECT object_id, longitude, distance, declination, right_ascension, has_equatorial FROM computed_positions WHERE chart_id = 'test_chart'"
        ).fetchall()
        
        self.assertEqual(len(result), 2)
        # Check sun
        sun_row = next((r for r in result if r[0] == 'sun'), None)
        self.assertIsNotNone(sun_row)
        self.assertAlmostEqual(sun_row[1], 45.5, places=1)
        self.assertAlmostEqual(sun_row[2], 0.985, places=3)
        self.assertAlmostEqual(sun_row[3], 15.2, places=1)
        self.assertAlmostEqual(sun_row[4], 45.8, places=1)
        self.assertTrue(sun_row[5])  # has_equatorial should be True
    
    def test_store_aspects(self):
        """Test storing aspects."""
        aspects = [
            {
                'from': 'sun',
                'to': 'moon',
                'type': 'trine',
                'angle': 119.5,
                'orb': 0.5,
                'exact_angle': 120.0,
                'applying': True,
                'separating': False,
            },
            {
                'from': 'mars',
                'to': 'venus',
                'type': 'square',
                'angle': 91.2,
                'orb': 1.2,
                'exact_angle': 90.0,
                'applying': False,
                'separating': True,
            },
        ]
        
        dt_str = '2024-01-01T12:00:00+01:00'
        relation_id = 'test_relation'
        
        self.storage.store_aspects(relation_id, dt_str, aspects)
        
        # Verify data
        result = self.storage.conn.execute(
            "SELECT source_object, target_object, aspect_type, angle, orb FROM computed_aspects WHERE relation_id = ?",
            (relation_id,)
        ).fetchall()
        
        self.assertEqual(len(result), 2)
        # Check trine aspect
        trine = next((r for r in result if r[2] == 'trine'), None)
        self.assertIsNotNone(trine)
        self.assertEqual(trine[0], 'sun')
        self.assertEqual(trine[1], 'moon')
        self.assertAlmostEqual(trine[3], 119.5, places=1)
        self.assertAlmostEqual(trine[4], 0.5, places=1)
    
    def test_store_positions_replace(self):
        """Test that storing same position twice replaces it."""
        positions1 = {'sun': 45.5}
        positions2 = {'sun': 50.0}  # Different longitude
        
        dt_str = '2024-01-01T12:00:00+01:00'
        
        self.storage.store_positions('test_chart', dt_str, positions1)
        self.storage.store_positions('test_chart', dt_str, positions2)
        
        # Should only have one row (replaced)
        result = self.storage.conn.execute(
            "SELECT longitude FROM computed_positions WHERE chart_id = 'test_chart' AND object_id = 'sun'"
        ).fetchall()
        
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][0], 50.0, places=1)
    
    def test_get_storage_path(self):
        """Test storage path helper."""
        workspace_path = '/some/path/to/workspace.yaml'
        db_path = get_storage_path(workspace_path)
        
        self.assertEqual(str(db_path), '/some/path/to/data/workspace.db')
    
    def test_context_manager(self):
        """Test using storage as context manager."""
        with DuckDBStorage(self.db_path) as storage:
            storage.store_positions(
                'test_chart',
                '2024-01-01T12:00:00+01:00',
                {'sun': 45.5}
            )
        
        # Should be closed after context
        # (We can't easily test this without accessing private attributes,
        # but we can verify data was stored)
        storage2 = DuckDBStorage(self.db_path, create_schema=False)
        result = storage2.conn.execute(
            "SELECT COUNT(*) FROM computed_positions"
        ).fetchone()
        self.assertEqual(result[0], 1)
        storage2.close()


@unittest.skipUnless(STORAGE_AVAILABLE, "duckdb and pyarrow not available")
class TestParquetExport(unittest.TestCase):
    """Test Parquet export functionality."""
    
    def setUp(self):
        """Set up test database with data."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        self.storage = DuckDBStorage(self.db_path, create_schema=True)
        
        # Add some test data
        positions = {
            'sun': {'longitude': 45.5, 'distance': 0.985},
            'moon': {'longitude': 120.3, 'distance': 0.0025},
        }
        self.storage.store_positions(
            'chart1',
            '2024-01-01T12:00:00+01:00',
            positions,
            engine='jpl'
        )
        self.storage.store_positions(
            'chart1',
            '2024-01-02T12:00:00+01:00',
            positions,
            engine='jpl'
        )
    
    def tearDown(self):
        """Clean up."""
        if self.storage:
            self.storage.close()
        self.tmpdir.cleanup()
    
    def test_export_to_parquet(self):
        """Test exporting to Parquet."""
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow not available")
        
        output_dir = Path(self.tmpdir.name) / "parquet"
        files = self.storage.export_to_parquet(
            output_dir,
            chart_id='chart1',
            partition_by_date=True
        )
        
        self.assertGreater(len(files), 0)
        # Verify file exists
        self.assertTrue(files[0].exists())


if __name__ == "__main__":
    unittest.main()
