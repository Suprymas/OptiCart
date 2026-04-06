from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock, patch

from shop import search as search_mod
from shop.models import Product


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

    def test_search_products_matches_accentless_query_against_db_text(self):
        Product.objects.create(
            name="Grietinė DVARO 30% 380 g",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: grietinė; Riebumas: 30%; Svoris: 380 g",
            price="2.69",
        )

        qs = search_mod.search_products("grietine")

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().name, "Grietinė DVARO 30% 380 g")

    def test_search_products_applies_category_and_detail_filters(self):
        matching = Product.objects.create(
            name="Pienas DVARO 2,5% 1 l",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 2,5%; Kiekis: 1 L",
            price="1.59",
        )
        Product.objects.create(
            name="Pienas DVARO 3,5% 1 l",
            store="rimi",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 3,5%; Kiekis: 1 L",
            price="1.79",
        )

        qs = search_mod.search_products(
            "pienas",
            "pieno-produktai",
            {"dairy_type": "pienas", "milk_fat": "2.5", "milk_volume": "1l"},
        )

        self.assertEqual(list(qs), [matching])

    def test_search_products_filters_by_dairy_type_pienas_only(self):
        milk = Product.objects.create(
            name="Pienas DVARO 2,5% 1 l",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 2,5%; Kiekis: 1 L",
            price="1.59",
        )
        Product.objects.create(
            name="Kefyras VILKYŠKIŲ 2,5% 1 kg",
            store="rimi",
            description="Kategorija: pieno produktai; Tipas: kefyras; Riebumas: 2,5%; Svoris: 1 kg",
            price="1.49",
        )

        qs = search_mod.search_products(
            "",
            "pieno-produktai",
            {"dairy_type": "pienas"},
        )

        self.assertEqual(list(qs), [milk])

    def test_search_products_works_with_filters_even_without_query(self):
        matching = Product.objects.create(
            name="Sviestas ROKIŠKIO NAMINIS 82% 180 g",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: sviestas; Riebumas: 82%; Svoris: 180 g",
            price="2.39",
        )
        Product.objects.create(
            name="Pienas DVARO 2,5% 1 l",
            store="rimi",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 2,5%; Kiekis: 1 L",
            price="1.65",
        )

        qs = search_mod.search_products(
            "",
            "pieno-produktai",
            {"dairy_type": "sviestas"},
        )

        self.assertEqual(list(qs), [matching])

    def test_search_products_filters_produce_group(self):
        fruit = Product.objects.create(
            name="Bananai 1 kg",
            store="barbora",
            description="Kategorija: vaisiai ir daržovės; Tipas: vaisiai; Grupė: vaisiai; Pavidalas: bananai; Svoris: 1 kg",
            price="1.15",
        )
        Product.objects.create(
            name="Lietuviški trumpavaisiai agurkai 1 kg",
            store="rimi",
            description="Kategorija: vaisiai ir daržovės; Tipas: daržovės; Grupė: daržovės; Pavidalas: trumpavaisiai agurkai; Svoris: 1 kg",
            price="1.99",
        )

        qs = search_mod.search_products(
            "",
            "vaisiai-darzoves",
            {"produce_type": "vaisiai"},
        )

        self.assertEqual(list(qs), [fruit])

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
