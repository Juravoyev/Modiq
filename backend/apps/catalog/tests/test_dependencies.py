import ast
from pathlib import Path

from django.test import SimpleTestCase

CATALOG = Path(__file__).resolve().parents[1]


class CatalogDependencyTests(SimpleTestCase):
    """Katalog moduli quyi qatlam: u inventory, sales yoki discounts modullarini import qilmasligi kerak."""

    FORBIDDEN = ("apps.inventory", "apps.sales", "apps.discounts", "apps.insights", "apps.reports")

    def test_catalog_does_not_import_higher_modules(self):
        found = []
        for path in CATALOG.rglob("*.py"):
            if "tests" in path.parts or "migrations" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = [node.module or ""] if isinstance(node, ast.ImportFrom) else \
                    [a.name for a in node.names] if isinstance(node, ast.Import) else []
                found += [f"{path.name}: {n}" for n in names if n.startswith(self.FORBIDDEN)]
        self.assertEqual(found, [])
