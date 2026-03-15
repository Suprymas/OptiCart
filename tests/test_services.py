from django.test import SimpleTestCase, Client
from unittest.mock import MagicMock, patch
from decimal import Decimal
import shop.services
import shop.views


class ServicesTests(SimpleTestCase):
    @patch("shop.services.Product")
    @patch("shop.services.BasketTemplateItem")
    def test_compare_template_prices_parallel(self, MockBasketTemplateItem, MockProduct):
        # Prepare two template items (Milk x2, Bread x1)
        item1 = MagicMock()
        item1.product = MagicMock()
        item1.product.name = "Milk"
        item1.quantity = 2

        item2 = MagicMock()
        item2.product = MagicMock()
        item2.product.name = "Bread"
        item2.quantity = 1

        MockBasketTemplateItem.objects.select_related.return_value.filter.return_value = [
            item1,
            item2,
        ]

        # Product.objects.filter(...).first() should return different prices per store
        def product_filter(**kw):
            name = kw.get("name__icontains")
            store = kw.get("store")

            class R:
                def __init__(self, price):
                    self._price = price

                def first(self):
                    return MagicMock(price=Decimal(str(self._price))) if self._price is not None else None

            if name == "Milk" and store == "barbora":
                return R("1.00")
            if name == "Milk" and store == "rimi":
                return R("2.00")
            if name == "Bread" and store == "barbora":
                return R("3.00")
            if name == "Bread" and store == "rimi":
                return R("1.50")
            return R(None)

        MockProduct.objects.filter.side_effect = product_filter

        # import here to ensure we're testing the real function
        from shop.services import compare_template_prices

        res = compare_template_prices(template_id=1)

        # Validate items
        items = {it["name"]: it for it in res["items"]}
        self.assertIn("Milk", items)
        self.assertIn("Bread", items)

        self.assertEqual(items["Milk"]["prices"]["barbora"], 2.0)
        self.assertEqual(items["Milk"]["prices"]["rimi"], 4.0)
        self.assertEqual(items["Bread"]["prices"]["barbora"], 3.0)
        self.assertEqual(items["Bread"]["prices"]["rimi"], 1.5)

        # Totals: barbora = 2+3=5.0, rimi = 4+1.5=5.5 -> cheapest barbora
        self.assertEqual(res["totals"]["barbora"], 5.0)
        self.assertEqual(res["totals"]["rimi"], 5.5)
        self.assertEqual(res["cheapest_store"], "barbora")

    @patch("shop.views.compare_template_prices")
    def test_template_compare_view_returns_json(self, mock_service):
        client = Client()
        expected = {
            "items": [{"name": "X", "quantity": 1, "prices": {"barbora": 1.0, "rimi": 2.0}}],
            "totals": {"barbora": 1.0, "rimi": 2.0},
            "cheapest_store": "barbora",
        }
        mock_service.return_value = expected

        resp = client.get("/template/42/compare/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), expected)
