from pathlib import Path
import difflib
import unittest

from devtools.diagram_export import generate_mermaid, generate_enum_overview_markdown


DOCS_PATH = Path(__file__).resolve().parents[1] / "docs" / "site" / "content" / "models.mmd"
ENUMS_PATH = Path(__file__).resolve().parents[1] / "docs" / "site" / "content" / "enums.md"


def unified_diff(
    a: str, b: str, fromfile: str = "generated", tofile: str = "docs/site/content/models.mmd"
) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


class TestDocs(unittest.TestCase):
    def test_models_mermaid_diagram_matches_docs(self):
        generated = generate_mermaid()

        if not DOCS_PATH.exists():
            self.skipTest(
                "No docs/site/content/models.mmd existed; generate it via: "
                f"'python -m devtools.diagram_export --out {DOCS_PATH}'"
            )

        expected = DOCS_PATH.read_text(encoding="utf-8")
        if generated != expected:
            diff = unified_diff(generated, expected)
            self.fail(
                "Mermaid class diagram out of sync with models.\n"
                "Regenerate with: python -m devtools.diagram_export --out docs/site/content/models.mmd\n\n"
                + diff
            )

    def test_enum_overview_matches_docs(self):
        generated = generate_enum_overview_markdown()

        if not ENUMS_PATH.exists():
            self.skipTest(
                "No docs/site/content/enums.md existed; generate it via: "
                f"'python -m devtools.diagram_export --enums-out {ENUMS_PATH}'"
            )

        expected = ENUMS_PATH.read_text(encoding="utf-8")
        if generated != expected:
            diff = unified_diff(
                generated, expected, fromfile="generated", tofile="docs/site/content/enums.md"
            )
            self.fail(
                "Enum overview out of sync with models.\n"
                f"Regenerate with: python -m devtools.diagram_export --enums-out {ENUMS_PATH}\n\n" + diff
            )


if __name__ == "__main__":
    unittest.main()
