from django.test import TestCase, Client
from shop.models import Product
from django.contrib.auth import get_user_model
import time
from urllib.parse import urlparse


class SearchIntegrationTests(TestCase):
    def setUp(self):
        # create couple of comparable products (same name, two stores)
        self.p1 = Product.objects.create(name='Pienas', store='barbora', price=1.0, image_url='')
        self.p2 = Product.objects.create(name='Pienas', store='rimi', price=1.1, image_url='')
        # another comparable pair
        self.b1 = Product.objects.create(name='Duona', store='barbora', price=2.0, image_url='')
        self.b2 = Product.objects.create(name='Duona', store='rimi', price=1.9, image_url='')

        self.client = Client()
        # create and login user for view tests
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='u', password='p')
        self.client.force_login(self.user)

    def test_search_api_basic_match(self):
        """Functional: API returns matching group for simple query."""
        resp = self.client.get('/api/search/', {'q': 'pienas'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [r['name'] for r in data['results']]
        self.assertIn('Pienas', names)
        self.assertFalse(data['no_results'])

    def test_search_view_case_and_whitespace_normalization(self):
        """Robustness: search_view normalizes case/whitespace and returns grouped results."""
        resp = self.client.get('/search/', {'q': '  PiEnAs  '})
        self.assertEqual(resp.status_code, 200)
        groups = resp.context['groups']
        names = [g['name'] for g in groups]
        self.assertIn('Pienas', names)

    def test_search_api_category_and_filter(self):
        """Functional: category+filter narrows results (service+DB integration)."""
        # create product that should match dairy filter keywords
        Product.objects.create(name='Sviestas', store='barbora', price=3.0)
        Product.objects.create(name='Sviestas', store='rimi', price=3.1)
        # query with category and a selected filter (dairy_type=sviestas)
        resp = self.client.get('/api/search/', {'q': 'sviestas', 'category': 'pieno-produktai', 'dairy_type': 'sviestas'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [r['name'] for r in data['results']]
        self.assertIn('Sviestas', names)

    def test_search_api_no_results_flag(self):
        """Usability: no_results toggles when query provided but nothing matches."""
        resp = self.client.get('/api/search/', {'q': 'totallyabsentterm'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['no_results'])
        self.assertEqual(data['results'], [])

    def test_search_api_simple_performance(self):
        """Performance: ensure query completes within reasonable time (conservative)."""
        t0 = time.perf_counter()
        resp = self.client.get('/api/search/', {'q': 'pienas'})
        t1 = time.perf_counter()
        self.assertEqual(resp.status_code, 200)
        elapsed = t1 - t0
        # adjust threshold as needed for environment; 1.0s is conservative for CI/local
        self.assertLess(elapsed, 1.0)

    # ===== ERROR / EDGE CASES =====
    def test_search_api_unknown_category_and_invalid_filters_do_not_error(self):
        """Robustness: unknown category or invalid filter values should not cause errors."""
        # pass a category that is not recognised and invalid filter values
        resp = self.client.get('/api/search/', {
            'q': 'pienas',
            'category': 'not-a-real-category',
            'dairy_type': 'nonexistent',
            'milk_fat': 'x-y-z',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # should still return results or empty list but not error; ensure key exists
        self.assertIn('results', data)

    def test_search_view_short_query_shows_all_comparables(self):
        """Behavior: short queries (<3) in home view should return comparable groups (not search).
        """
        resp = self.client.get('/', {'q': 'pi'})
        self.assertEqual(resp.status_code, 200)
        groups = resp.context.get('groups', [])
        names = [g['name'] for g in groups]
        # comparable names should be present
        self.assertIn('Pienas', names)
        self.assertIn('Duona', names)

    def test_search_api_sql_like_query_is_safe(self):
        """Security: ensure queries with special chars do not cause server errors."""
        resp = self.client.get('/api/search/', {'q': "'; DROP TABLE shop_product; --"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('results', data)
