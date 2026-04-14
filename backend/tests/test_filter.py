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

    def test_get_selected_filters_extracts_known_values_only(self):
        selected = search_mod.get_selected_filters(
            {
                "dairy_type": " Pienas ",
                "milk_fat": "2.5",
                "unknown": "x",
                "egg_size": "",
            }
        )

        self.assertEqual(selected, {"dairy_type": "pienas", "milk_fat": "2.5"})

    def test_search_products_returns_none_for_empty_query_and_filters(self):
        Product.objects.create(name="Pienas", store="barbora", price="1.00")

        results = search_mod.search_products("", "", {})

        self.assertEqual(results.count(), 0)

    def test_search_products_query_only_uses_fast_queryset_path(self):
        milk = Product.objects.create(name="Pienas DVARO", store="barbora", price="1.00")
        Product.objects.create(name="Duona", store="rimi", price="1.00")

        results = search_mod.search_products("pienas", "", {})

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, milk.id)

    def test_search_products_query_without_matches_returns_empty(self):
        Product.objects.create(name="Duona", store="barbora", price="1.00")
        Product.objects.create(name="Sultys", store="rimi", price="1.00")

        results = search_mod.search_products("neegzistuoja", "", {})

        self.assertEqual(results.count(), 0)

    def test_parse_amount_returns_none_when_no_amount_in_text(self):
        self.assertIsNone(search_mod._parse_amount("be kiekio"))

    def test_infer_category_returns_none_for_unknown_text(self):
        self.assertIsNone(search_mod._infer_category("visiskai nezinoma kategorija"))

    def test_extract_signature_dairy_type_fallback_without_explicit_type_field(self):
        product = Product(name="Sviestas kaimiskas", description="Riebumas: 82%")

        signature = search_mod._extract_product_signature(product)

        self.assertEqual(signature["category"], "pieno-produktai")
        self.assertEqual(signature["dairy_type"], "sviestas")

    def test_extract_signature_egg_meat_produce_and_drink_variants(self):
        egg = Product(name="Kiausiniai", description="Dydis M")
        meat = Product(name="Jautienos ispjova", description="")
        produce = Product(name="Agurkai", description="")
        drink = Product(name="Gerimas alus sviesus", description="")

        egg_sig = search_mod._extract_product_signature(egg)
        meat_sig = search_mod._extract_product_signature(meat)
        produce_sig = search_mod._extract_product_signature(produce)
        drink_sig = search_mod._extract_product_signature(drink)

        self.assertEqual(egg_sig["egg_size"], "m")
        self.assertEqual(meat_sig["meat_type"], "jautiena")
        self.assertEqual(produce_sig["produce_type"], "darzoves")
        self.assertEqual(drink_sig["drink_type"], "alkoholis")

    def test_matches_query_and_matches_category_helpers(self):
        product = Product(name="Pienas DVARO 2,5%", description="Kiekis 1 L")

        self.assertTrue(search_mod._matches_query(product, "pienas 2.5"))
        self.assertFalse(search_mod._matches_query(product, "pienas 3.5"))
        self.assertTrue(search_mod._matches_category({"category": "pieno-produktai"}, ""))

    def test_matches_selected_filters_handles_missing_category_and_invalid_value(self):
        signature = {"milk_fat": "2.5"}

        self.assertTrue(search_mod._matches_selected_filters(signature, "", {"milk_fat": "2.5"}))
        self.assertTrue(
            search_mod._matches_selected_filters(
                signature,
                "pieno-produktai",
                {"milk_fat": "9.9"},
            )
        )

    def test_infer_category_from_filters_empty_and_detected(self):
        self.assertEqual(search_mod._infer_category_from_filters({}), "")
        self.assertEqual(search_mod._infer_category_from_filters({"dairy_type": "pienas"}), "pieno-produktai")

    def test_infer_category_from_filters_returns_empty_for_unrelated_fields(self):
        self.assertEqual(search_mod._infer_category_from_filters({"unknown": "value"}), "")

    def test_matches_query_returns_false_for_blank_query(self):
        product = Product(name="Pienas", description="")

        self.assertFalse(search_mod._matches_query(product, "   "))

    def test_has_search_results_supports_queryset_and_list(self):
        qs = Product.objects.none()

        self.assertFalse(search_mod.has_search_results(qs))
        self.assertTrue(search_mod.has_search_results([1]))
