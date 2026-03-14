import importlib.util
import sys
import types
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


ROOT_DIR = Path(__file__).resolve().parent


def _load_module(module_name, file_name):
    spec = importlib.util.spec_from_file_location(module_name, ROOT_DIR / file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Load the root-level files as a synthetic package so relative imports work.
shop_package = types.ModuleType("shop")
shop_package.__path__ = [str(ROOT_DIR)]
sys.modules.setdefault("shop", shop_package)

# Provide a lightweight stand-in for .models to keep tests unit-level.
fake_models = types.ModuleType("shop.models")


class _Product:
    pass


fake_models.Product = _Product
sys.modules["shop.models"] = fake_models

comparison_module = _load_module("shop.comparison", "comparison.py")
compare_basket_prices = comparison_module.compare_basket_prices


def _item(name, qty):
    item = MagicMock()
    item.product_name = name
    item.quantity = qty
    return item


def _product(price):
    product = MagicMock()
    product.price = Decimal(str(price))
    return product


def _qs(returned):
    qs = MagicMock()
    qs.first.return_value = returned
    return qs


class CompareBasketPricesTests(SimpleTestCase):
    @patch("shop.comparison.Product")
    def test_empty_basket(self, MockProduct):
        result = compare_basket_prices([])

        self.assertEqual(result["items"], [])
        self.assertEqual(result["totals"], {"barbora": 0, "rimi": 0})
        self.assertIsNone(result["cheapest_store"])

    @patch("shop.comparison.Product")
    def test_barbora_cheaper(self, MockProduct):
        MockProduct.objects.filter.side_effect = lambda **kw: (
            _qs(_product("1.00")) if kw["store"] == "barbora" else _qs(_product("2.00"))
        )

        result = compare_basket_prices([_item("Pienas", 1)])

        self.assertEqual(result["items"][0]["prices"]["barbora"], 1.0)
        self.assertEqual(result["items"][0]["prices"]["rimi"], 2.0)
        self.assertEqual(result["cheapest_store"], "barbora")

    @patch("shop.comparison.Product")
    def test_rimi_cheaper(self, MockProduct):
        MockProduct.objects.filter.side_effect = lambda **kw: (
            _qs(_product("3.00")) if kw["store"] == "barbora" else _qs(_product("1.50"))
        )

        result = compare_basket_prices([_item("Duona", 1)])

        self.assertEqual(result["cheapest_store"], "rimi")

    @patch("shop.comparison.Product")
    def test_missing_in_rimi(self, MockProduct):
        MockProduct.objects.filter.side_effect = lambda **kw: (
            _qs(_product("2.00")) if kw["store"] == "barbora" else _qs(None)
        )

        result = compare_basket_prices([_item("Suris", 1)])

        self.assertEqual(result["items"][0]["prices"]["barbora"], 2.0)
        self.assertIsNone(result["items"][0]["prices"]["rimi"])
        self.assertEqual(result["cheapest_store"], "rimi")

    @patch("shop.comparison.Product")
    def test_missing_in_barbora(self, MockProduct):
        MockProduct.objects.filter.side_effect = lambda **kw: (
            _qs(None) if kw["store"] == "barbora" else _qs(_product("1.80"))
        )

        result = compare_basket_prices([_item("Sviestas", 1)])

        self.assertIsNone(result["items"][0]["prices"]["barbora"])
        self.assertEqual(result["items"][0]["prices"]["rimi"], 1.8)

    @patch("shop.comparison.Product")
    def test_quantity_multiplies_price(self, MockProduct):
        MockProduct.objects.filter.side_effect = lambda **kw: (
            _qs(_product("2.00")) if kw["store"] == "barbora" else _qs(None)
        )

        result = compare_basket_prices([_item("Kiausiniai", 3)])

        self.assertEqual(result["items"][0]["prices"]["barbora"], 6.0)

    @patch("shop.comparison.Product")
    def test_multiple_items_totals(self, MockProduct):
        prices = {
            ("Pienas", "barbora"): "1.00",
            ("Pienas", "rimi"): "2.00",
            ("Duona", "barbora"): "3.00",
            ("Duona", "rimi"): "1.50",
        }

        MockProduct.objects.filter.side_effect = lambda **kw: (
            _qs(_product(prices[(kw["name__icontains"], kw["store"])]))
            if (kw["name__icontains"], kw["store"]) in prices
            else _qs(None)
        )

        result = compare_basket_prices([_item("Pienas", 1), _item("Duona", 1)])

        self.assertEqual(result["totals"]["barbora"], 4.0)
        self.assertEqual(result["totals"]["rimi"], 3.5)
        self.assertEqual(result["cheapest_store"], "rimi")

    @patch("shop.comparison.Product")
    def test_no_products_found(self, MockProduct):
        MockProduct.objects.filter.return_value = _qs(None)

        result = compare_basket_prices([_item("Nezinoma", 1)])

        self.assertEqual(result["totals"]["barbora"], 0)
        self.assertEqual(result["totals"]["rimi"], 0)
        self.assertIsNone(result["cheapest_store"])

    @patch("shop.comparison.Product")
    def test_result_has_correct_keys(self, MockProduct):
        MockProduct.objects.filter.return_value = _qs(None)

        result = compare_basket_prices([_item("Jogurtas", 2)])

        self.assertIn("items", result)
        self.assertIn("totals", result)
        self.assertIn("cheapest_store", result)
        self.assertEqual(result["items"][0]["name"], "Jogurtas")
        self.assertEqual(result["items"][0]["quantity"], 2)
