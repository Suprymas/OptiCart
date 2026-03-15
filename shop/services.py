from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
import os

from django.db.models import QuerySet

from .models import BasketTemplateItem, Product


def _find_product_for_store(name: str, store: str):
    """Return the first product matching name (icontains) for the given store."""
    return Product.objects.filter(name__icontains=name, store=store).first()


def compare_template_prices(template_id: int, stores: List[str] = None) -> Dict:
    """
    Given a BasketTemplate id, gather its items and perform parallel price lookups
    across the provided stores (defaults to ['barbora', 'rimi']). Returns a dict
    with per-item prices, totals per store and the cheapest store.

    This function parallelizes the per-item/per-store lookups using threads to
    reduce latency when many lookups are required.
    """
    if stores is None:
        stores = ["barbora", "rimi"]

    items_qs: QuerySet = BasketTemplateItem.objects.select_related("product").filter(template_id=template_id)

    # Build the response skeleton
    result = {
        "items": [],
        "totals": {store: 0 for store in stores},
        "cheapest_store": None,
    }

    # Prepare per-item records and tasks for parallel lookup
    tasks = {}
    lookup_executor_workers = min(32, (os.cpu_count() or 1) * 5)
    with ThreadPoolExecutor(max_workers=lookup_executor_workers) as exe:
        for item in items_qs:
            name = getattr(item.product, "name", None) or ""
            record = {"name": name, "quantity": item.quantity, "prices": {}}
            result["items"].append(record)

            for store in stores:
                # submit lookup task per item/store
                future = exe.submit(_find_product_for_store, name, store)
                tasks[future] = (record, store, item.quantity)

        # collect results
        for future in as_completed(tasks):
            record, store, qty = tasks[future]
            product = future.result()
            if product:
                price = round(float(product.price) * qty, 2)
                record["prices"][store] = price
            else:
                record["prices"][store] = None

    # compute totals
    for store in stores:
        prices = [it["prices"][store] for it in result["items"] if it["prices"][store] is not None]
        result["totals"][store] = round(sum(prices), 2) if prices else 0

    if any(result["totals"].values()):
        result["cheapest_store"] = min(result["totals"], key=result["totals"].get)

    return result
