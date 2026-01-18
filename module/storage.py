"""
DuckDB and Parquet storage helpers for computed astrological data.

This module provides optional storage functionality for Python to write
computed positions and aspects directly to DuckDB/Parquet, avoiding
large JSON transfers for batch operations like transit series.

Usage:
    from module.storage import DuckDBStorage
    
    storage = DuckDBStorage('/path/to/workspace/data/workspace.db')
    storage.store_positions(chart_id, datetime, positions, engine='jpl')
    storage.store_aspects(relation_id, datetime, aspects)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import sys

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("Warning: duckdb not available. Install with: pip install duckdb", file=sys.stderr)

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("Warning: pyarrow not available. Install with: pip install pyarrow", file=sys.stderr)


class DuckDBStorage:
    """DuckDB storage for computed astrological data.
    
    Provides methods to store positions and aspects directly in DuckDB,
    avoiding large JSON transfers for batch operations.
    """
    
    def __init__(self, db_path: Union[str, Path], create_schema: bool = True):
        """Initialize DuckDB storage.
        
        Args:
            db_path: Path to DuckDB database file
            create_schema: If True, create tables if they don't exist
        """
        if not DUCKDB_AVAILABLE:
            raise ImportError("duckdb package is required. Install with: pip install duckdb")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(str(self.db_path))
        
        if create_schema:
            self._create_schema()
    
    def _create_schema(self):
        """Create database schema if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS computed_positions (
                chart_id TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                object_id TEXT NOT NULL,
                
                -- Ecliptic coordinates (always available)
                longitude REAL NOT NULL,
                latitude REAL,
                
                -- Equatorial coordinates (JPL - always computed)
                declination REAL,
                right_ascension REAL,
                distance REAL,
                
                -- Topocentric coordinates (JPL with location)
                altitude REAL,
                azimuth REAL,
                
                -- Physical properties (JPL optional)
                apparent_magnitude REAL,
                phase_angle REAL,
                elongation REAL,
                light_time REAL,
                
                -- Motion properties
                speed REAL,
                retrograde BOOLEAN,
                
                -- Engine metadata
                engine TEXT,
                ephemeris_file TEXT,
                
                -- Flags for which columns are populated
                has_equatorial BOOLEAN DEFAULT FALSE,
                has_topocentric BOOLEAN DEFAULT FALSE,
                has_physical BOOLEAN DEFAULT FALSE,
                
                PRIMARY KEY (chart_id, datetime, object_id)
            );
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_chart_datetime 
                ON computed_positions(chart_id, datetime);
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_object 
                ON computed_positions(object_id);
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS computed_aspects (
                relation_id TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                source_object TEXT NOT NULL,
                target_object TEXT NOT NULL,
                aspect_type TEXT NOT NULL,
                angle REAL NOT NULL,
                orb REAL NOT NULL,
                exact_angle REAL NOT NULL,
                applying BOOLEAN,
                separating BOOLEAN,
                exact_datetime TIMESTAMP,
                
                PRIMARY KEY (relation_id, datetime, source_object, target_object, aspect_type)
            );
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_aspects_relation_datetime 
                ON computed_aspects(relation_id, datetime);
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_aspects_type 
                ON computed_aspects(aspect_type);
        """)
    
    def store_positions(
        self,
        chart_id: str,
        datetime_str: str,
        positions: Dict[str, Union[float, Dict[str, float]]],
        engine: Optional[str] = None,
        ephemeris_file: Optional[str] = None
    ) -> None:
        """Store computed positions in DuckDB.
        
        Args:
            chart_id: Chart identifier
            datetime_str: ISO format datetime string
            positions: Dict mapping object_id -> position data
                      Can be float (longitude only) or dict (extended format)
            engine: Engine type ('jpl', 'swisseph', etc.)
            ephemeris_file: Path to ephemeris file (for JPL)
        """
        # Parse datetime
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        
        rows = []
        for object_id, pos_data in positions.items():
            if isinstance(pos_data, dict):
                # Extended format (JPL)
                row = {
                    'chart_id': chart_id,
                    'datetime': dt,
                    'object_id': object_id,
                    'longitude': float(pos_data.get('longitude', 0.0)),
                    'latitude': float(pos_data.get('latitude', 0.0)) if pos_data.get('latitude') is not None else None,
                    'declination': float(pos_data.get('declination', 0.0)) if pos_data.get('declination') is not None else None,
                    'right_ascension': float(pos_data.get('right_ascension', 0.0)) if pos_data.get('right_ascension') is not None else None,
                    'distance': float(pos_data.get('distance', 0.0)) if pos_data.get('distance') is not None else None,
                    'altitude': float(pos_data.get('altitude', 0.0)) if pos_data.get('altitude') is not None else None,
                    'azimuth': float(pos_data.get('azimuth', 0.0)) if pos_data.get('azimuth') is not None else None,
                    'apparent_magnitude': float(pos_data.get('apparent_magnitude', 0.0)) if pos_data.get('apparent_magnitude') is not None else None,
                    'phase_angle': float(pos_data.get('phase_angle', 0.0)) if pos_data.get('phase_angle') is not None else None,
                    'elongation': float(pos_data.get('elongation', 0.0)) if pos_data.get('elongation') is not None else None,
                    'light_time': float(pos_data.get('light_time', 0.0)) if pos_data.get('light_time') is not None else None,
                    'speed': float(pos_data.get('speed', 0.0)) if pos_data.get('speed') is not None else None,
                    'retrograde': bool(pos_data.get('retrograde', False)) if pos_data.get('retrograde') is not None else None,
                    'engine': engine,
                    'ephemeris_file': ephemeris_file,
                    'has_equatorial': pos_data.get('declination') is not None and pos_data.get('right_ascension') is not None and pos_data.get('distance') is not None,
                    'has_topocentric': pos_data.get('altitude') is not None and pos_data.get('azimuth') is not None,
                    'has_physical': pos_data.get('apparent_magnitude') is not None or pos_data.get('phase_angle') is not None or pos_data.get('elongation') is not None,
                }
            else:
                # Simple format (non-JPL)
                row = {
                    'chart_id': chart_id,
                    'datetime': dt,
                    'object_id': object_id,
                    'longitude': float(pos_data),
                    'latitude': None,
                    'declination': None,
                    'right_ascension': None,
                    'distance': None,
                    'altitude': None,
                    'azimuth': None,
                    'apparent_magnitude': None,
                    'phase_angle': None,
                    'elongation': None,
                    'light_time': None,
                    'speed': None,
                    'retrograde': None,
                    'engine': engine,
                    'ephemeris_file': ephemeris_file,
                    'has_equatorial': False,
                    'has_topocentric': False,
                    'has_physical': False,
                }
            rows.append(row)
        
        # Insert using DuckDB's insert from values
        if rows:
            # Convert to list of tuples in correct order
            columns = [
                'chart_id', 'datetime', 'object_id', 'longitude', 'latitude',
                'declination', 'right_ascension', 'distance',
                'altitude', 'azimuth',
                'apparent_magnitude', 'phase_angle', 'elongation', 'light_time',
                'speed', 'retrograde',
                'engine', 'ephemeris_file',
                'has_equatorial', 'has_topocentric', 'has_physical'
            ]
            
            values = [
                tuple(row[col] for col in columns)
                for row in rows
            ]
            
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO computed_positions 
                (chart_id, datetime, object_id, longitude, latitude,
                 declination, right_ascension, distance,
                 altitude, azimuth,
                 apparent_magnitude, phase_angle, elongation, light_time,
                 speed, retrograde,
                 engine, ephemeris_file,
                 has_equatorial, has_topocentric, has_physical)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values
            )
    
    def store_aspects(
        self,
        relation_id: str,
        datetime_str: str,
        aspects: List[Dict[str, Any]]
    ) -> None:
        """Store computed aspects in DuckDB.
        
        Args:
            relation_id: Relation identifier (e.g., 'transit_chart1_2024')
            datetime_str: ISO format datetime string
            aspects: List of aspect dictionaries
        """
        if not aspects:
            return
        
        # Parse datetime
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        
        rows = []
        for aspect in aspects:
            row = {
                'relation_id': relation_id,
                'datetime': dt,
                'source_object': aspect.get('from', ''),
                'target_object': aspect.get('to', ''),
                'aspect_type': aspect.get('type', ''),
                'angle': float(aspect.get('angle', 0.0)),
                'orb': float(aspect.get('orb', 0.0)),
                'exact_angle': float(aspect.get('exact_angle', 0.0)),
                'applying': bool(aspect.get('applying', False)) if aspect.get('applying') is not None else None,
                'separating': bool(aspect.get('separating', False)) if aspect.get('separating') is not None else None,
                'exact_datetime': None,  # Could be computed if needed
            }
            rows.append(row)
        
        if rows:
            columns = [
                'relation_id', 'datetime', 'source_object', 'target_object',
                'aspect_type', 'angle', 'orb', 'exact_angle',
                'applying', 'separating', 'exact_datetime'
            ]
            
            values = [
                tuple(row[col] for col in columns)
                for row in rows
            ]
            
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO computed_aspects
                (relation_id, datetime, source_object, target_object,
                 aspect_type, angle, orb, exact_angle,
                 applying, separating, exact_datetime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values
            )
    
    def export_to_parquet(
        self,
        output_dir: Union[str, Path],
        chart_id: Optional[str] = None,
        partition_by_date: bool = True
    ) -> List[Path]:
        """Export positions to Parquet files.
        
        Args:
            output_dir: Directory to write Parquet files
            chart_id: If specified, only export this chart
            partition_by_date: If True, partition by date (YYYY-MM-DD)
        
        Returns:
            List of created Parquet file paths
        """
        if not PARQUET_AVAILABLE:
            raise ImportError("pyarrow is required for Parquet export. Install with: pip install pyarrow")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Query positions
        query = "SELECT * FROM computed_positions"
        if chart_id:
            query += f" WHERE chart_id = '{chart_id}'"
        query += " ORDER BY chart_id, datetime, object_id"
        
        result = self.conn.execute(query).fetchdf()
        
        if result.empty:
            return []
        
        # Convert to PyArrow table
        table = pa.Table.from_pandas(result)
        
        if partition_by_date:
            # Partition by date
            result['date'] = result['datetime'].dt.date
            grouped = result.groupby(['chart_id', 'date'])
            
            parquet_files = []
            for (cid, date), group in grouped:
                group_table = pa.Table.from_pandas(group.drop(columns=['date']))
                parquet_path = output_dir / f"{cid}_{date}.parquet"
                pq.write_table(group_table, parquet_path, compression='snappy')
                parquet_files.append(parquet_path)
            
            return parquet_files
        else:
            # Single file per chart
            if chart_id:
                parquet_path = output_dir / f"{chart_id}.parquet"
            else:
                parquet_path = output_dir / "all_positions.parquet"
            
            pq.write_table(table, parquet_path, compression='snappy')
            return [parquet_path]
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_storage_path(workspace_path: Union[str, Path]) -> Path:
    """Get DuckDB storage path for a workspace.
    
    Args:
        workspace_path: Path to workspace.yaml
    
    Returns:
        Path to workspace.db in data/ directory
    """
    workspace_path = Path(workspace_path)
    workspace_dir = workspace_path.parent
    data_dir = workspace_dir / "data"
    return data_dir / "workspace.db"
