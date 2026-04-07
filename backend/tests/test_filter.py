import time

from django.test import TestCase

from shop import search as search_mod
from shop.models import Product


class FilterTests(TestCase):
    def test_filter_configuration_displays_correct_dairy_products(self):
        """Requirement: product list matches filter configuration."""
        dairy1 = Product.objects.create(
            name="Pienas DVARO 2,5% 1 l",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 2,5%; Kiekis: 1 L",
            price="1.59",
        )
        dairy2 = Product.objects.create(
            name="Kefyras VILKYŠKIŲ 2,5% 1 kg",
            store="rimi",
            description="Kategorija: pieno produktai; Tipas: kefyras; Riebumas: 2,5%; Svoris: 1 kg",
            price="1.49",
        )
        produce = Product.objects.create(
            name="Bananai 1 kg",
            store="barbora",
            description="Kategorija: vaisiai ir daržovės; Tipas: vaisiai; Grupė: vaisiai",
            price="1.15",
        )

        results = search_mod.search_products("", "pieno-produktai", {})

        self.assertEqual(results.count(), 2)
        result_ids = {p.id for p in results}
        self.assertIn(dairy1.id, result_ids)
        self.assertIn(dairy2.id, result_ids)
        self.assertNotIn(produce.id, result_ids)

    def test_filter_configuration_displays_correct_produce_products(self):
        """Requirement: product list matches filter configuration."""
        fruit = Product.objects.create(
            name="Bananai 1 kg",
            store="barbora",
            description="Kategorija: vaisiai ir daržovės; Tipas: vaisiai; Grupė: vaisiai",
            price="1.15",
        )
        vegetable = Product.objects.create(
            name="Pomidorai 1 kg",
            store="rimi",
            description="Kategorija: vaisiai ir daržovės; Tipas: daržovės; Grupė: daržovės",
            price="1.99",
        )
        dairy = Product.objects.create(
            name="Pienas DVARO 2,5% 1 l",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 2,5%; Kiekis: 1 L",
            price="1.59",
        )

        results = search_mod.search_products("", "vaisiai-darzoves", {})

        self.assertEqual(results.count(), 2)
        result_ids = {p.id for p in results}
        self.assertIn(fruit.id, result_ids)
        self.assertIn(vegetable.id, result_ids)
        self.assertNotIn(dairy.id, result_ids)

    def test_detail_filters_narrow_results_correctly(self):
        """Requirement: detail filters narrow results accurately."""
        milk_2_5 = Product.objects.create(
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
        Product.objects.create(
            name="Kefyras VILKYŠKIŲ 2,5% 1 kg",
            store="rimi",
            description="Kategorija: pieno produktai; Tipas: kefyras; Riebumas: 2,5%; Svoris: 1 kg",
            price="1.49",
        )

        results = search_mod.search_products(
            "",
            "pieno-produktai",
            {"dairy_type": "pienas", "milk_fat": "2.5"},
        )

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, milk_2_5.id)

    def test_multiple_filters_produce_accurate_results(self):
        """Requirement: combined filters produce accurate result set."""
        Product.objects.create(
            name="Pienas DVARO 2,5% 1 l",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 2,5%; Kiekis: 1 L",
            price="1.59",
        )
        milk_3_5 = Product.objects.create(
            name="Pienas DVARO 3,5% 1 l",
            store="rimi",
            description="Kategorija: pieno produktai; Tipas: pienas; Riebumas: 3,5%; Kiekis: 1 L",
            price="1.79",
        )
        Product.objects.create(
            name="Jogurtas VILKYŠKIŲ 2,5% 500g",
            store="barbora",
            description="Kategorija: pieno produktai; Tipas: jogurtas; Riebumas: 2,5%; Svoris: 500 g",
            price="0.99",
        )

        results = search_mod.search_products(
            "",
            "pieno-produktai",
            {"dairy_type": "pienas", "milk_fat": "3.5"},
        )

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, milk_3_5.id)

    def test_performance_filter_search_completes_within_five_seconds(self):
        """Requirement: data loads within 5 seconds."""
        products_data = [
            {
                "name": f"Pienas DVARO {fat}% {volume} l",
                "store": "barbora" if i % 2 == 0 else "rimi",
                "description": f"Kategorija: pieno produktai; Tipas: pienas; Riebumas: {fat}%; Kiekis: {volume} L",
                "price": f"{1.50 + i * 0.05}",
            }
            for i in range(20)
            for fat in ["2.5", "3.2", "3.5"]
            for volume in ["0.5", "1", "2"]
        ]

        for data in products_data:
            Product.objects.create(**data)

        start_time = time.time()
        results = search_mod.search_products(
            "",
            "pieno-produktai",
            {"dairy_type": "pienas", "milk_fat": "3.5"},
        )
        elapsed_time = time.time() - start_time

        self.assertLess(elapsed_time, 5.0)
        self.assertGreater(results.count(), 0)
