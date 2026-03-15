from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

import shop.template_services


class TemplateServicesTests(SimpleTestCase):
    @patch("shop.template_services.BasketTemplate")
    @patch("shop.template_services.BasketTemplateItem")
    def test_duplicate_template(self, MockItem, MockTemplate):
        orig = MagicMock()
        orig.name = "Weekly"
        it1 = MagicMock()
        it1.product = MagicMock()
        it1.product.id = 1
        it1.product.name = "Milk"
        it1.quantity = 2

        orig.items.all.return_value = [it1]
        MockTemplate.objects.get.return_value = orig

        user = MagicMock()
        MockTemplate.objects.create.return_value = MagicMock()

        from shop.template_services import duplicate_template

        new = duplicate_template(template_id=5, user=user, new_name="Weekly copy")

        MockTemplate.objects.get.assert_called_with(pk=5)
        MockTemplate.objects.create.assert_called_with(user=user, name="Weekly copy")
        MockItem.objects.create.assert_called()

    @patch("shop.template_services.BasketTemplate")
    @patch("shop.template_services.BasketTemplateItem")
    @patch("shop.template_services.Product")
    def test_create_template_from_order(self, MockProduct, MockItem, MockTemplate):
        user = MagicMock()
        MockTemplate.objects.create.return_value = MagicMock()

        mock_prod = MagicMock()
        MockProduct.objects.filter.return_value.first.return_value = mock_prod

        order_items = [
            {"product_name": "Milk", "quantity": 2},
            {"product_name": "Bread", "quantity": 1},
        ]

        from shop.template_services import create_template_from_order

        tpl = create_template_from_order(user=user, name="From Order", order_items=order_items)

        MockTemplate.objects.create.assert_called_with(user=user, name="From Order")
        assert MockProduct.objects.filter.called
