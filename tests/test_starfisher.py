import os
import unittest
from datetime import datetime
from module.utils import parse_sfs_content, AstroModel

class TestStarfisher(unittest.TestCase):
    def test_load_starfisher_sample(self):
        sfs_path = os.path.join(os.path.dirname(__file__), '../source/starfisher_sample.sfs')
        encodings = ["utf-8-sig", "utf-16", "latin-1", "windows-1250"]
        sfs_content = None
        for enc in encodings:
            try:
                with open(sfs_path, encoding=enc) as f:
                    sfs_content = f.read()
                break
            except Exception:
                continue
        self.assertIsNotNone(sfs_content, f"Could not decode {sfs_path} with known encodings.")
        model, display = parse_sfs_content(sfs_content)
        self.assertIsInstance(model, AstroModel, "Parsed model is not an AstroModel instance.")
        self.assertIsInstance(display, dict, "Display config is not a dictionary.")
        self.assertIsNotNone(getattr(model, 'body_definitions', None))
        self.assertTrue(hasattr(model, 'settings'))

    def test_create_sfs_from_current_time(self):
        # Use the provided current time
        now = datetime(2025, 7, 6, 16, 57, 59)
        sfs_content = (
            '_settings.Model.DefaultHouseSystem = "Placidus";\n'
            '_settings.Model.StandardComparisonOrbCoef = "1.0";\n'
        )
        sfs_filename = "test_current_time.sfs"
        try:
            with open(sfs_filename, "w", encoding="utf-8") as f:
                f.write(sfs_content)
            with open(sfs_filename, "r", encoding="utf-8") as f:
                loaded_content = f.read()
            model, display = parse_sfs_content(loaded_content)
            self.assertIsInstance(model, AstroModel)
            self.assertEqual(model.settings.default_house_system.name, "PLACIDUS")
            self.assertEqual(model.settings.standard_orb, 1.0)
        finally:
            if os.path.exists(sfs_filename):
                os.remove(sfs_filename)

if __name__ == "__main__":
    unittest.main()
