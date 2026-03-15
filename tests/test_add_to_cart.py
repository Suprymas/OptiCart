from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
import json


class CartViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('shop.views.Product')
    def test_add_to_cart_adds_new_product_by_name(self, MockProduct):
        # Mock Product.objects.get to return a product with id and name
        prod = MagicMock()
        prod.id = 123
        prod.name = 'Apelsinai'
        MockProduct.objects.get.return_value = prod

        resp = self.client.post('/add-to-cart/', data=json.dumps({'product_id': prod.id, 'quantity': 5}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('quantity'), 5)
        self.assertEqual(data.get('action'), 'added')

        # session should have cart entry keyed by product name
        session = self.client.session
        self.assertIn('cart', session)
        self.assertEqual(session['cart'].get('Apelsinai'), 5)

    @patch('shop.views.Product')
    def test_add_to_cart_replaces_existing_and_removes_numeric_key(self, MockProduct):
        prod = MagicMock()
        prod.id = 77
        prod.name = 'Pienas'
        MockProduct.objects.get.return_value = prod

        # prepopulate session with a numeric-keyed entry (old behavior)
        session = self.client.session
        session['cart'] = {str(prod.id): 3}
        session.save()

        resp = self.client.post('/add-to-cart/', data=json.dumps({'product_id': prod.id, 'quantity': 2}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('quantity'), 2)
        self.assertEqual(data.get('action'), 'updated')

        session = self.client.session
        self.assertIn('cart', session)
        # numeric key should be removed, name key should exist
        self.assertNotIn(str(prod.id), session['cart'])
        self.assertEqual(session['cart'].get('Pienas'), 2)

    @patch('shop.views.search_products')
    @patch('shop.views.has_search_results')
    def test_search_view_groups_stores_and_shows_single_control(self, mock_has, mock_search):
        # create two product-like objects with same name different stores
        p1 = SimpleNamespace(name='Apelsinai', store='barbora', price='1.50', id=1)
        p2 = SimpleNamespace(name='Apelsinai', store='rimi', price='0.90', id=2)

        mock_search.return_value = [p1, p2]
        mock_has.return_value = True

        resp = self.client.get('/?q=apelsinai')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        # both stores should be present
        self.assertIn('Barbora', content)
        self.assertIn('Rimi', content)

        # only one add/update control per product name: look for 'add-btn' occurrences
        count_controls = content.count('class="add-btn"')
        self.assertEqual(count_controls, 1)
