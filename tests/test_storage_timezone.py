"""Regression: DuckDB datetime filters must not depend on the machine timezone.

`compute_aspects_from_positions` (and the other filtered queries) used to
interpolate `dt.isoformat()` into SQL. DuckDB drops the offset of such a
literal but converts bound aware datetimes to local time on INSERT, so the
query only matched on machines whose UTC offset equaled the data's offset.
`test_storage.test_compute_aspects_from_positions` therefore passed in
Europe/Prague and failed in GitHub Actions (UTC). A +05:30 offset is used
here so the mismatch would reproduce on practically any developer machine.
"""

import tempfile
import unittest
from pathlib import Path

from module.storage import DuckDBStorage

DT = "2024-01-01T12:00:00+05:30"


class StorageTimezoneIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage = DuckDBStorage(Path(self.tmpdir.name) / "tz.db", create_schema=True)
        self.storage.store_positions(
            "tz_chart",
            DT,
            {
                "sun": {"longitude": 0.0, "latitude": 0.0},
                "moon": {"longitude": 120.5, "latitude": 0.0},
            },
            engine="jpl",
        )

    def tearDown(self):
        self.storage.close()
        self.tmpdir.cleanup()

    def test_aspects_found_for_offset_differing_from_local_zone(self):
        aspects = self.storage.compute_aspects_from_positions(chart_id="tz_chart", datetime_str=DT)
        self.assertEqual(list(aspects["aspect_type"]), ["trine"])

    def test_same_instant_in_utc_notation_matches(self):
        aspects = self.storage.compute_aspects_from_positions(
            chart_id="tz_chart", datetime_str="2024-01-01T06:30:00Z"
        )
        self.assertEqual(len(aspects), 1)


if __name__ == "__main__":
    unittest.main()
