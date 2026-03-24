from types import SimpleNamespace

from django.test import SimpleTestCase

# tests_comparison monkeypatches `shop.models`, so import the real file by path
from pathlib import Path
import ast


class ModelsSourceTests(SimpleTestCase):
    def setUp(self):
        # tests/ is one level under repo root, so go up one directory to reach shop/
        p = Path(__file__).resolve().parent.parent / 'shop' / 'models.py'
        self.source = p.read_text()
        self.tree = ast.parse(self.source)

    def test_classes_exist(self):
        names = {n.name for n in self.tree.body if isinstance(n, ast.ClassDef)}
        self.assertIn('BasketTemplate', names)
        self.assertIn('BasketTemplateItem', names)

    def test_related_names_and_fields_present(self):
        # simple textual checks are sufficient for these structural assertions
        self.assertIn("related_name=\"basket_templates\"", self.source)
        self.assertIn("related_name=\"items\"", self.source)
        self.assertIn("related_name=\"template_items\"", self.source)
        self.assertIn("quantity = models.PositiveIntegerField(default=1)", self.source)

    def test_unique_together_present(self):
        self.assertIn("unique_together = (\"template\", \"product\")", self.source)

    def test_str_methods_contain_expected_text(self):
        # check that __str__ contains template name and product quantity pattern
        self.assertIn('Template: {self.name}', self.source.replace('"', "'"))
        self.assertIn('x{self.quantity}', self.source)

