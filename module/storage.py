"""
DuckDB and Parquet storage helpers for computed astrological data.

This module provides optional storage functionality for Python to write
computed positions and aspects directly to DuckDB/Parquet, avoiding
large JSON transfers for batch operations like transit series.

Usage:
    from module.storage import DuckDBStorage
    
    storage = DuckDBStorage('/path/to/workspace/data/workspace.db')
    storage.store_positions(chart_id, datetime, positions, engine='jpl')
    
    # Optimized batch computation
    storage.compute_and_store_series(
        chart_id='transit_base',
        start_datetime=start_dt,
        end_datetime=end_dt,
        time_step=timedelta(minutes=1),
        location=location,
        engine='jpl',
        requested_objects=['sun', 'moon', ...],
        include_physical=True,
        include_topocentric=True
    )
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

try:
    from module.logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger(__name__)

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    logger.warning("duckdb not available. Install with: pip install duckdb")

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    logger.warning("pyarrow not available. Install with: pip install pyarrow")


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
                -- Longitude is relative to vernal equinox (spring solstice = 0°)
                longitude REAL NOT NULL,
                latitude REAL,
                
                -- Equatorial coordinates (extended/dict positions only; NULL for simple float positions)
                -- Declination and distance for 3D view
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
                
                -- Radix/relation tracking (for transit analysis)
                -- radix_chart_id: If this is a transit, reference to base chart
                -- If NULL, this is a radix/base chart position
                radix_chart_id TEXT,
                
                -- Flags for which columns are populated
                has_equatorial BOOLEAN DEFAULT FALSE,
                has_topocentric BOOLEAN DEFAULT FALSE,
                has_physical BOOLEAN DEFAULT FALSE,
                is_radix BOOLEAN DEFAULT TRUE,  -- TRUE for base charts, FALSE for transits
                
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
            CREATE INDEX IF NOT EXISTS idx_positions_radix 
                ON computed_positions(radix_chart_id);
        """)
        
        # Note: Aspects are NOT stored - they are computed on-demand from positions via SQL
        # This avoids duplication and allows flexible aspect computation with different orbs/rules
    
    def store_positions(
        self,
        chart_id: str,
        datetime_str: str,
        positions: Dict[str, Union[float, Dict[str, float]]],
        engine: Optional[str] = None,
        ephemeris_file: Optional[str] = None,
        radix_chart_id: Optional[str] = None
    ) -> None:
        """Store computed positions in DuckDB.
        
        Args:
            chart_id: Chart identifier
            datetime_str: ISO format datetime string
            positions: Dict mapping object_id -> position data
                      Can be float (longitude only) or dict (extended format)
            engine: Engine type ('jpl', 'swisseph', etc.)
            ephemeris_file: Path to ephemeris file (for JPL)
            radix_chart_id: If this is a transit, reference to base/radix chart.
                          If None, this is a radix/base chart position.
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
                    'radix_chart_id': radix_chart_id,
                    'has_equatorial': pos_data.get('declination') is not None and pos_data.get('right_ascension') is not None and pos_data.get('distance') is not None,
                    'has_topocentric': pos_data.get('altitude') is not None and pos_data.get('azimuth') is not None,
                    'has_physical': pos_data.get('apparent_magnitude') is not None or pos_data.get('phase_angle') is not None or pos_data.get('elongation') is not None,
                    'is_radix': radix_chart_id is None,  # True if this is a base chart, False if transit
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
                    'radix_chart_id': radix_chart_id,
                    'has_equatorial': False,
                    'has_topocentric': False,
                    'has_physical': False,
                    'is_radix': radix_chart_id is None,
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
                'engine', 'ephemeris_file', 'radix_chart_id',
                'has_equatorial', 'has_topocentric', 'has_physical', 'is_radix'
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
                 engine, ephemeris_file, radix_chart_id,
                 has_equatorial, has_topocentric, has_physical, is_radix)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values
            )
    
    def compute_and_store_series(
        self,
        chart_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        time_step: timedelta,
        location: 'Location',
        engine: str = 'jpl',
        ephemeris_file: Optional[str] = None,
        requested_objects: Optional[List[str]] = None,
        include_physical: bool = False,
        include_topocentric: bool = False,
        batch_size: int = 1000,
        radix_chart_id: Optional[str] = None
    ) -> int:
        """Optimized: Compute and store time series with pre-initialized JPL/Skyfield engine.

        `engine` is accepted for backward compatibility with old callers that
        still pass 'swisseph'/'kerykeion'; only the JPL/Skyfield engine is
        computed now, regardless of its value.

        This is MUCH faster than cmd_compute_transit_series because it:
        - Pre-initializes engine components ONCE (not per timestamp)
        - Uses direct position computation (no ChartInstance overhead)
        - Batches storage operations
        - Skips aspect computation (not stored anyway)

        Performance: computes each body's whole series in one vectorized Skyfield call
        (via an array-valued Time) instead of one call per timestamp - see
        `services._compute_planet_extended_positions_vectorized`.

        Args:
            chart_id: Chart identifier
            start_datetime: Start datetime
            end_datetime: End datetime
            time_step: Time step (e.g., timedelta(minutes=1))
            location: Location object
            engine: Accepted for backward compatibility; ignored (JPL/Skyfield always runs)
            ephemeris_file: Path to ephemeris file
            requested_objects: List of object IDs to compute (defaults to all planets)
            include_physical: Include physical properties
            include_topocentric: Include topocentric properties
            batch_size: Number of timestamps to batch before storing
            radix_chart_id: If this is a transit, reference to base/radix chart.
                          If None, this is a radix/base chart position.

        Returns:
            Number of timestamps computed
        """

        # Import here to avoid circular dependencies
        from module.utils import default_ephemeris_path, ensure_aware, compute_vernal_equinox_offset
        from pathlib import Path
        import numpy as np

        if engine not in ('jpl', 'JPL'):
            logger.info("engine=%s requested but only the JPL/Skyfield engine is available; using JPL", engine)
        engine_str = 'jpl'

        try:
            from skyfield.api import load, Topos, load_file
        except ImportError:
            raise ImportError("skyfield is required")

        # Use default ephemeris if not provided
        if not ephemeris_file:
            ephemeris_file = default_ephemeris_path()

        # Pre-initialize Skyfield components
        ts = load.timescale()
        eph = load_file(ephemeris_file)
        observer = Topos(latitude_degrees=location.latitude, longitude_degrees=location.longitude)
        is_de421 = "de421" in Path(ephemeris_file).name.lower()

        # Import position computation helpers
        from module.services import _compute_planet_extended_positions_vectorized, _load_mpc_orbits, _MPC_MINOR_BODY_IDS

        # Determine which planets/minor bodies to compute
        jpl_supported = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
        if requested_objects:
            planets = [p for p in jpl_supported if p in requested_objects]
            minor_bodies = [b for b in _MPC_MINOR_BODY_IDS if b in requested_objects]
        else:
            planets = jpl_supported
            minor_bodies = list(_MPC_MINOR_BODY_IDS)

        # MPC orbits don't change per-timestamp; load/cache once (mirrors ts/eph/observer above).
        mpc_orbits = _load_mpc_orbits(ts) if minor_bodies else {}
        sun_body = eph["sun"] if minor_bodies else None

        # Generate time points
        time_points = []
        current = start_datetime
        while current <= end_datetime:
            time_points.append(current)
            current += time_step

        total_timestamps = len(time_points)
        logger.info(
            "Computing %s timestamps with %s engine (vectorized per body)...",
            f"{total_timestamps:,}",
            engine_str.upper(),
        )

        if total_timestamps == 0:
            return 0

        dt_aware_list = [ensure_aware(tp, location.timezone) for tp in time_points]
        barycenter_planets = ["mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]

        stored_count = 0

        # Process in chunks of batch_size: each chunk still vectorizes every body's Skyfield
        # call across the WHOLE chunk at once (one .observe().apparent() call per body, not
        # one per timestamp), while bounding memory for very large date ranges.
        for chunk_start in range(0, total_timestamps, batch_size):
            chunk_end = min(chunk_start + batch_size, total_timestamps)
            chunk_dts = dt_aware_list[chunk_start:chunk_end]
            chunk_dt_strs = [dt.isoformat() for dt in chunk_dts]
            n_chunk = len(chunk_dts)

            t_array = ts.from_datetimes(chunk_dts)

            # Vernal equinox offset per timestamp (cached per year); a chunk spanning a
            # year boundary needs one offset value per distinct year, not just one scalar.
            years = [dt.year for dt in chunk_dts]
            offset_by_year = {y: compute_vernal_equinox_offset(y, eph, observer, ts) for y in set(years)}
            vernal_offsets = np.array([offset_by_year[y] for y in years])

            sun_astrometric = (
                (eph["earth"] + observer).at(t_array).observe(eph["sun"]).apparent()
                if include_physical else None
            )

            per_body_results: Dict[str, Dict[str, Any]] = {}
            for planet in planets:
                try:
                    if is_de421 and planet in barycenter_planets:
                        body = eph[f"{planet} barycenter"]
                    else:
                        try:
                            body = eph[planet]
                        except KeyError:
                            if planet in barycenter_planets:
                                body = eph[f"{planet} barycenter"]
                            else:
                                continue

                    pos = _compute_planet_extended_positions_vectorized(
                        body, eph, observer, t_array, vernal_offsets,
                        include_physical=include_physical,
                        include_topocentric=include_topocentric,
                        sun_astrometric=sun_astrometric,
                    )
                    if pos:
                        per_body_results[planet] = pos
                except (KeyError, ValueError):
                    continue

            for body_id in minor_bodies:
                orbit = mpc_orbits.get(body_id)
                if orbit is None:
                    continue
                try:
                    pos = _compute_planet_extended_positions_vectorized(
                        sun_body + orbit, eph, observer, t_array, vernal_offsets,
                        include_physical=include_physical,
                        include_topocentric=include_topocentric,
                        sun_astrometric=sun_astrometric,
                    )
                    if pos:
                        per_body_results[body_id] = pos
                except (KeyError, ValueError):
                    continue

            # Unpack the vectorized (numpy-array-per-field) results back into the same
            # per-timestamp dict shape _store_batch expects - cheap (no Skyfield calls left).
            positions_batch = []
            for i in range(n_chunk):
                positions = {}
                for body_id, fields in per_body_results.items():
                    pos_data = {}
                    for key, arr in fields.items():
                        if arr is None:
                            pos_data[key] = None
                        elif key == 'retrograde':
                            pos_data[key] = bool(arr[i])
                        else:
                            pos_data[key] = float(arr[i])
                    positions[body_id] = pos_data
                positions_batch.append((chunk_dt_strs[i], positions))

            self._store_batch(chart_id, positions_batch, engine_str, ephemeris_file, radix_chart_id)
            stored_count += n_chunk

            logger.info(
                "Progress: %s/%s (%.1f%%)",
                f"{chunk_end:,}",
                f"{total_timestamps:,}",
                100 * chunk_end / total_timestamps,
            )

        return stored_count
    
    def _store_batch(self, chart_id: str, positions_batch: List[tuple], engine: str, ephemeris_file: Optional[str], radix_chart_id: Optional[str] = None):
        """Store a batch of positions using a single bulk INSERT.

        Builds one pandas DataFrame for the whole batch and inserts it via
        `INSERT OR REPLACE INTO ... SELECT ... FROM <registered df>`, which DuckDB runs as
        one vectorized columnar operation. `executemany()` with per-row parameter binding
        measured ~300 rows/sec here; this is dramatically faster for large batches.
        """
        rows = []
        for datetime_str, positions in positions_batch:
            # Parse datetime once
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            
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
                        'radix_chart_id': radix_chart_id,
                        'has_equatorial': pos_data.get('declination') is not None and pos_data.get('right_ascension') is not None and pos_data.get('distance') is not None,
                        'has_topocentric': pos_data.get('altitude') is not None and pos_data.get('azimuth') is not None,
                        'has_physical': pos_data.get('apparent_magnitude') is not None or pos_data.get('phase_angle') is not None or pos_data.get('elongation') is not None,
                        'is_radix': radix_chart_id is None,
                    }
                else:
                    # Simple format (plain float longitude, no extended fields)
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
                        'radix_chart_id': radix_chart_id,
                        'has_equatorial': False,
                        'has_topocentric': False,
                        'has_physical': False,
                        'is_radix': radix_chart_id is None,
                    }
                rows.append(row)
        
        if not rows:
            return

        import pandas as pd

        columns = [
            'chart_id', 'datetime', 'object_id', 'longitude', 'latitude',
            'declination', 'right_ascension', 'distance',
            'altitude', 'azimuth',
            'apparent_magnitude', 'phase_angle', 'elongation', 'light_time',
            'speed', 'retrograde',
            'engine', 'ephemeris_file', 'radix_chart_id',
            'has_equatorial', 'has_topocentric', 'has_physical', 'is_radix'
        ]

        df = pd.DataFrame(rows, columns=columns)
        # 'retrograde' mixes True/False/None - the pandas nullable boolean dtype maps it to a
        # proper nullable BOOLEAN column; the has_* / is_radix flags are always plain bool.
        df['retrograde'] = df['retrograde'].astype('boolean')
        for bool_col in ('has_equatorial', 'has_topocentric', 'has_physical', 'is_radix'):
            df[bool_col] = df[bool_col].astype(bool)

        view_name = f"_positions_batch_{id(df)}"
        self.conn.register(view_name, df)
        try:
            column_list = ', '.join(columns)
            self.conn.execute(
                f"INSERT OR REPLACE INTO computed_positions ({column_list}) "
                f"SELECT {column_list} FROM {view_name}"
            )
        finally:
            self.conn.unregister(view_name)
    
    def store_positions_batch(
        self,
        chart_id: str,
        positions_list: List[tuple],  # List of (datetime_str, positions_dict)
        engine: Optional[str] = None,
        ephemeris_file: Optional[str] = None,
        auto_export_parquet: bool = True,
        parquet_threshold: int = 100,
        parquet_dir: Optional[Union[str, Path]] = None
    ) -> Optional[List[Path]]:
        """Store multiple positions in batch (for transit series).
        
        Args:
            chart_id: Chart identifier
            positions_list: List of (datetime_str, positions_dict) tuples
            engine: Engine type ('jpl', 'swisseph', etc.)
            ephemeris_file: Path to ephemeris file (for JPL)
            auto_export_parquet: If True, automatically export to Parquet for large batches
            parquet_threshold: Minimum number of timestamps to trigger Parquet export
            parquet_dir: Directory for Parquet export (defaults to data/parquet relative to db)
        
        Returns:
            List of created Parquet file paths if exported, None otherwise
        """
        # Store all positions in DuckDB
        for datetime_str, positions in positions_list:
            self.store_positions(chart_id, datetime_str, positions, engine, ephemeris_file)
        
        # Auto-export to Parquet if threshold met
        if auto_export_parquet and len(positions_list) >= parquet_threshold:
            if parquet_dir is None:
                parquet_dir = self.db_path.parent / "parquet"
            return self.export_to_parquet(
                parquet_dir,
                chart_id=chart_id,
                partition_by_date=True
            )
        return None
    
    def store_radix_positions(
        self,
        radix_chart_id: str,
        datetime_str: str,
        positions: Dict[str, Union[float, Dict[str, float]]],
        engine: Optional[str] = None,
        ephemeris_file: Optional[str] = None
    ) -> None:
        """Store radix (base chart) positions.
        
        Radix positions are the reference/base positions for transit analysis.
        All positions are relative to vernal equinox (spring solstice = 0°).
        
        Args:
            radix_chart_id: Radix/base chart identifier
            datetime_str: ISO format datetime string
            positions: Dict mapping object_id -> position data
            engine: Engine type ('jpl', 'swisseph', etc.)
            ephemeris_file: Path to ephemeris file (for JPL)
        """
        # Store as radix (radix_chart_id = None means it's a base chart)
        self.store_positions(
            radix_chart_id,
            datetime_str,
            positions,
            engine=engine,
            ephemeris_file=ephemeris_file,
            radix_chart_id=None  # None = this IS the radix
        )
    
    def query_radix_relative_positions(
        self,
        transit_chart_id: str,
        radix_chart_id: str,
        datetime_str: Optional[str] = None,
        start_datetime: Optional[Union[str, datetime]] = None,
        end_datetime: Optional[Union[str, datetime]] = None
    ):
        """Query transit positions relative to radix positions.
        
        Returns positions with differences from radix (for transit analysis).
        All positions are relative to vernal equinox (spring solstice = 0°).
        
        Note: Radix positions are at a fixed time (the radix chart's event_time).
        Transit positions are compared to this fixed radix, not joined on datetime.
        
        Args:
            transit_chart_id: Transit chart identifier
            radix_chart_id: Radix/base chart identifier
            datetime_str: Optional specific datetime (ISO format) for transit
            start_datetime: Optional start datetime for range query
            end_datetime: Optional end datetime for range query
        
        Returns:
            DataFrame with columns: datetime, object_id, transit_longitude, radix_longitude,
                                   longitude_diff, transit_declination, radix_declination,
                                   declination_diff, transit_distance, radix_distance, distance_diff
        """
        # Get radix datetime (radix is stored at its event_time)
        radix_result = self.conn.execute(f"""
            SELECT DISTINCT datetime 
            FROM computed_positions 
            WHERE chart_id = '{radix_chart_id}' AND is_radix = TRUE
            LIMIT 1
        """).fetchone()
        
        if not radix_result:
            # Return empty DataFrame with correct schema
            return self.conn.execute("""
                SELECT 
                    t.datetime, t.object_id,
                    t.longitude AS transit_longitude, 0.0 AS radix_longitude, 0.0 AS longitude_diff,
                    t.declination AS transit_declination, 0.0 AS radix_declination, 0.0 AS declination_diff,
                    t.distance AS transit_distance, 0.0 AS radix_distance, 0.0 AS distance_diff
                FROM computed_positions t
                WHERE 1=0
            """).fetchdf()
        
        radix_datetime = radix_result[0]
        
        # Build query to join transit positions with radix positions
        # Radix is at fixed time, transit is at variable time
        conditions = [
            f"t.chart_id = '{transit_chart_id}'",
            f"r.chart_id = '{radix_chart_id}'",
            "t.object_id = r.object_id",
            f"r.datetime = '{radix_datetime}'",  # Radix is at fixed time
            "r.is_radix = TRUE"
        ]
        
        if datetime_str:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            conditions.append(f"t.datetime = '{dt.isoformat()}'")
        elif start_datetime or end_datetime:
            if start_datetime:
                if isinstance(start_datetime, str):
                    start_datetime = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                conditions.append(f"t.datetime >= '{start_datetime.isoformat()}'")
            if end_datetime:
                if isinstance(end_datetime, str):
                    end_datetime = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                conditions.append(f"t.datetime <= '{end_datetime.isoformat()}'")
        
        query = f"""
            SELECT 
                t.datetime,
                t.object_id,
                t.longitude AS transit_longitude,
                r.longitude AS radix_longitude,
                CASE 
                    WHEN ABS(t.longitude - r.longitude) > 180.0 
                    THEN (t.longitude - r.longitude) - SIGN(t.longitude - r.longitude) * 360.0
                    ELSE t.longitude - r.longitude
                END AS longitude_diff,
                t.declination AS transit_declination,
                r.declination AS radix_declination,
                CASE 
                    WHEN t.declination IS NOT NULL AND r.declination IS NOT NULL
                    THEN t.declination - r.declination
                    ELSE NULL
                END AS declination_diff,
                t.distance AS transit_distance,
                r.distance AS radix_distance,
                CASE 
                    WHEN t.distance IS NOT NULL AND r.distance IS NOT NULL
                    THEN t.distance - r.distance
                    ELSE NULL
                END AS distance_diff,
                t.engine AS transit_engine,
                r.engine AS radix_engine
            FROM computed_positions t
            JOIN computed_positions r
                ON t.object_id = r.object_id
            WHERE {' AND '.join(conditions)}
            ORDER BY t.datetime, t.object_id
        """
        
        return self.conn.execute(query).fetchdf()
    
    def compute_aspects_from_positions(
        self,
        chart_id: str,
        datetime_str: Optional[str] = None,
        aspect_definitions: Optional[List[Dict[str, float]]] = None,
        max_orb: float = 10.0
    ):
        """Compute aspects from stored positions using SQL.
        
        Aspects are computed on-demand from positions, avoiding storage duplication.
        This allows flexible aspect computation with different orbs/rules.
        
        Args:
            chart_id: Chart identifier
            datetime_str: Optional specific datetime (ISO format). If None, computes for all timestamps.
            aspect_definitions: List of aspect definitions with 'angle' and 'orb' keys.
                               Defaults to standard aspects: conjunction (0°), sextile (60°), 
                               square (90°), trine (120°), opposition (180°)
            max_orb: Maximum orb to consider (degrees)
        
        Returns:
            DataFrame with columns: datetime, source_object, target_object, aspect_type, 
                                   angle, orb, exact_angle
        """
        # Default aspect definitions (standard astrological aspects)
        if aspect_definitions is None:
            aspect_definitions = [
                {'angle': 0.0, 'orb': 8.0, 'type': 'conjunction'},
                {'angle': 60.0, 'orb': 6.0, 'type': 'sextile'},
                {'angle': 90.0, 'orb': 8.0, 'type': 'square'},
                {'angle': 120.0, 'orb': 8.0, 'type': 'trine'},
                {'angle': 180.0, 'orb': 8.0, 'type': 'opposition'},
            ]
        
        # Build base query with datetime filter
        datetime_filter = ""
        if datetime_str:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            datetime_filter = f"AND p1.datetime = '{dt.isoformat()}'"
        
        # Build aspect definitions as UNION ALL subqueries
        aspect_unions = []
        for asp_def in aspect_definitions:
            exact_angle = asp_def['angle']
            orb = asp_def.get('orb', max_orb)
            asp_type = asp_def.get('type', f"aspect_{exact_angle}")
            
            aspect_unions.append(f"""
                SELECT 
                    p1.datetime,
                    p1.chart_id,
                    p1.object_id AS source_object,
                    p2.object_id AS target_object,
                    '{asp_type}' AS aspect_type,
                    CASE 
                        WHEN ABS(p1.longitude - p2.longitude) > 180.0 
                        THEN 360.0 - ABS(p1.longitude - p2.longitude)
                        ELSE ABS(p1.longitude - p2.longitude)
                    END AS angle,
                    ABS(
                        CASE 
                            WHEN ABS(p1.longitude - p2.longitude) > 180.0 
                            THEN 360.0 - ABS(p1.longitude - p2.longitude)
                            ELSE ABS(p1.longitude - p2.longitude)
                        END - {exact_angle}
                    ) AS orb,
                    {exact_angle} AS exact_angle
                FROM computed_positions p1
                JOIN computed_positions p2 
                    ON p1.chart_id = p2.chart_id 
                    AND p1.datetime = p2.datetime
                    AND p1.object_id < p2.object_id
                WHERE p1.chart_id = '{chart_id}'
                    {datetime_filter}
                    AND ABS(
                        CASE 
                            WHEN ABS(p1.longitude - p2.longitude) > 180.0 
                            THEN 360.0 - ABS(p1.longitude - p2.longitude)
                            ELSE ABS(p1.longitude - p2.longitude)
                        END - {exact_angle}
                    ) <= {orb}
            """)
        
        # Combine all aspect queries
        query = " UNION ALL ".join(aspect_unions)
        query += " ORDER BY datetime, source_object, target_object, aspect_type"
        
        return self.conn.execute(query).fetchdf()
    
    def query_positions(
        self,
        chart_id: Optional[str] = None,
        start_datetime: Optional[Union[str, datetime]] = None,
        end_datetime: Optional[Union[str, datetime]] = None,
        object_id: Optional[str] = None,
        use_parquet: Optional[bool] = None,  # None = auto-detect
        parquet_dir: Optional[Union[str, Path]] = None,
        auto_route: bool = True  # Auto-choose DuckDB vs Parquet based on query size
    ):
        """Query positions with optional Parquet fallback and smart routing.
        
        Args:
            chart_id: Chart identifier (optional)
            start_datetime: Start datetime (ISO string or datetime)
            end_datetime: End datetime (ISO string or datetime)
            object_id: Filter by object ID (optional)
            use_parquet: If None and auto_route=True, automatically chooses based on query size.
                        If True, force Parquet. If False, force DuckDB.
            parquet_dir: Directory containing Parquet files (defaults to data/parquet)
            auto_route: If True, automatically chooses DuckDB for small queries, Parquet for large
        
        Returns:
            DataFrame with query results
        
        Performance:
            - Single timestamp: DuckDB (~0.02s) is much faster than Parquet (~2s)
            - Large ranges (>1 day): Parquet may be faster due to columnar format
            - Auto-routing defaults to DuckDB for single timestamps
        """
        # Auto-route if not explicitly specified
        if use_parquet is None and auto_route:
            if start_datetime and end_datetime:
                # Parse datetimes
                if isinstance(start_datetime, str):
                    start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                else:
                    start_dt = start_datetime
                
                if isinstance(end_datetime, str):
                    end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                else:
                    end_dt = end_datetime
                
                # Use Parquet for ranges > 1 day (86400 seconds)
                time_range = (end_dt - start_dt).total_seconds()
                use_parquet = time_range > 86400
            else:
                # Single timestamp or no range -> use DuckDB (much faster)
                use_parquet = False
        
        # Default to False if still None
        if use_parquet is None:
            use_parquet = False
        
        if use_parquet and PARQUET_AVAILABLE:
            if parquet_dir is None:
                parquet_dir = self.db_path.parent / "parquet"
            parquet_dir = Path(parquet_dir)
            
            # OPTIMIZATION: For single timestamp queries, use specific file instead of glob
            # This is much faster (0.3s vs 2s) because we only read one file
            if start_datetime == end_datetime and start_datetime and chart_id:
                # Parse datetime to get date
                if isinstance(start_datetime, str):
                    dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                else:
                    dt = start_datetime
                
                date_str = dt.date().isoformat()
                parquet_file = parquet_dir / f"{chart_id}_{date_str}.parquet"
                
                if parquet_file.exists():
                    # Query specific file - much faster than glob pattern
                    query = f"SELECT * FROM read_parquet('{parquet_file}') WHERE datetime = '{dt.isoformat()}'"
                    if object_id:
                        query += f" AND object_id = '{object_id}'"
                    query += " ORDER BY object_id"
                    return self.conn.execute(query).fetchdf()
                else:
                    # File doesn't exist, return empty
                    return self.conn.execute("SELECT * FROM computed_positions WHERE 1=0").fetchdf()
            
            # For range queries, use glob pattern (original implementation)
            # Build Parquet file pattern
            if chart_id:
                pattern = f"{chart_id}_*.parquet"
            else:
                pattern = "*.parquet"
            
            parquet_files = list(parquet_dir.glob(pattern))
            if not parquet_files:
                # Return empty DataFrame with correct schema
                return self.conn.execute("SELECT * FROM computed_positions WHERE 1=0").fetchdf()
            
            # Query Parquet files using glob pattern
            # DuckDB's read_parquet supports glob patterns
            file_pattern = str(parquet_dir / pattern)
            query = f"SELECT * FROM read_parquet('{file_pattern}')"
            conditions = []
            
            if chart_id:
                conditions.append(f"chart_id = '{chart_id}'")
            if start_datetime:
                if isinstance(start_datetime, str):
                    start_datetime = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                conditions.append(f"datetime >= '{start_datetime.isoformat()}'")
            if end_datetime:
                if isinstance(end_datetime, str):
                    end_datetime = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                conditions.append(f"datetime <= '{end_datetime.isoformat()}'")
            if object_id:
                conditions.append(f"object_id = '{object_id}'")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY chart_id, datetime, object_id"
            return self.conn.execute(query).fetchdf()
        else:
            # Query DuckDB
            query = "SELECT * FROM computed_positions"
            conditions = []
            
            if chart_id:
                conditions.append(f"chart_id = '{chart_id}'")
            if start_datetime:
                if isinstance(start_datetime, str):
                    start_datetime = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                conditions.append(f"datetime >= '{start_datetime.isoformat()}'")
            if end_datetime:
                if isinstance(end_datetime, str):
                    end_datetime = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                conditions.append(f"datetime <= '{end_datetime.isoformat()}'")
            if object_id:
                conditions.append(f"object_id = '{object_id}'")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY chart_id, datetime, object_id"
            return self.conn.execute(query).fetchdf()
    
    def export_to_parquet(
        self,
        output_dir: Union[str, Path],
        chart_id: Optional[str] = None,
        partition_by_date: bool = True,
        partition_by_hour: bool = False,
        compression: str = 'snappy'
    ) -> List[Path]:
        """Export positions to Parquet files.
        
        Args:
            output_dir: Directory to write Parquet files
            chart_id: If specified, only export this chart
            partition_by_date: If True, partition by date (YYYY-MM-DD)
            partition_by_hour: If True, partition by hour (YYYY-MM-DD-HH) - overrides date
            compression: Compression algorithm ('snappy', 'zstd', 'gzip', 'brotli')
        
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
        
        if partition_by_hour:
            # Partition by hour
            result['date'] = result['datetime'].dt.date
            result['hour'] = result['datetime'].dt.hour
            grouped = result.groupby(['chart_id', 'date', 'hour'])
            
            parquet_files = []
            for (cid, date, hour), group in grouped:
                group_table = pa.Table.from_pandas(group.drop(columns=['date', 'hour']))
                parquet_path = output_dir / f"{cid}_{date}_{hour:02d}.parquet"
                pq.write_table(group_table, parquet_path, compression=compression)
                parquet_files.append(parquet_path)
            
            return parquet_files
        elif partition_by_date:
            # Partition by date
            result['date'] = result['datetime'].dt.date
            grouped = result.groupby(['chart_id', 'date'])
            
            parquet_files = []
            for (cid, date), group in grouped:
                group_table = pa.Table.from_pandas(group.drop(columns=['date']))
                parquet_path = output_dir / f"{cid}_{date}.parquet"
                pq.write_table(group_table, parquet_path, compression=compression)
                parquet_files.append(parquet_path)
            
            return parquet_files
        else:
            # Single file per chart
            if chart_id:
                parquet_path = output_dir / f"{chart_id}.parquet"
            else:
                parquet_path = output_dir / "all_positions.parquet"
            
            table = pa.Table.from_pandas(result)
            pq.write_table(table, parquet_path, compression=compression)
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
