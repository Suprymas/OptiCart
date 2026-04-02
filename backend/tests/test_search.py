from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock, patch

from shop import search as search_mod


class SearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='searchuser', password='testpass123')
        self.client.force_login(self.user)

    def test_process_search_query_trims_and_lowercases(self):
        s = search_mod.process_search_query("  MiLk  ")
        self.assertEqual(s, "milk")

    @patch("shop.search.Product")
    def test_search_products_calls_filter_and_returns_results(self, MockProduct):
        # prepare fake product objects returned by the ORM
        fake1 = MagicMock()
        fake1.name = "Milk"
        fake2 = MagicMock()
        fake2.name = "Milk"

        MockProduct.objects.filter.return_value = [fake1, fake2]

        qs = search_mod.search_products("Milk")

        MockProduct.objects.filter.assert_called_once_with(name__icontains="milk")
        self.assertEqual(list(qs), [fake1, fake2])

    @patch("shop.views.search_products")
    def test_search_api_groups_results_and_no_results(self, mock_search_products):
        # case: no results
        mock_search_products.return_value = []
        resp = self.client.get('/api/search/', {'q': 'doesnotexist'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['no_results'])

        # case: some results -> grouped and no_results False
        p1 = MagicMock()
        p1.name = "Banana"
        p1.id = 11
        p1.image_url = "https://example.com/banana.jpg"
        p2 = MagicMock()
        p2.name = "Banana"
        p2.id = 12
        p2.image_url = None

        mock_search_products.return_value = [p1, p2]
        resp = self.client.get('/api/search/', {'q': 'Banana'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['no_results'])
        # should include single grouped result with representative id
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], 'Banana')
        self.assertIn('rep_id', data['results'][0])
