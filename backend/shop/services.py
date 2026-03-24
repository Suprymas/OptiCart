from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
import os

from django.db.models import QuerySet

from .models import BasketTemplateItem, Product
from .models import PriceHistory
from django.db.models import Q
from datetime import date


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


def _get_price_at_date(product_id: int, when: date):
    """Return the price (Decimal) for product at the given date or None.

    Preference is given to a PriceHistory entry that explicitly covers the date
    (date_from <= when < date_until or date_until is null). The most recent
    matching entry (largest date_from) is returned.
    """
    ph = (
        PriceHistory.objects.filter(product_id=product_id)
        .filter(date_from__lte=when)
        .filter(Q(date_until__isnull=True) | Q(date_until__gt=when))
        .order_by('-date_from')
        .first()
    )
    if ph:
        return ph.price
    return None


def compute_price_change(product_id: int, start: date, end: date) -> Dict:
    """Compute percent price change for a product between two dates.

    Returns a dict with keys: start_price, end_price, percent_change.
    If a price is missing for either end, percent_change will be None and
    a 'missing' key will explain which price was absent.
    """
    if start > end:
        start, end = end, start

    start_price = _get_price_at_date(product_id, start)
    end_price = _get_price_at_date(product_id, end)

    result = {
        'start_price': start_price,
        'end_price': end_price,
        'percent_change': None,
    }

    if start_price is None or end_price is None:
        missing = []
        if start_price is None:
            missing.append('start')
        if end_price is None:
            missing.append('end')
        result['missing'] = missing
        return result

    try:
        # Decimal arithmetic is handled by Django DecimalField type; convert to float for percent calc
        sp = float(start_price)
        ep = float(end_price)
        if sp == 0:
            # avoid division by zero
            result['percent_change'] = None
            result['error'] = 'start_price_zero'
        else:
            pct = ((ep - sp) / sp) * 100.0
            result['percent_change'] = round(pct, 4)
    except Exception as exc:
        result['error'] = str(exc)

    # Determine whether the percent change is significant enough to notify.
    # Business rule: alert if absolute percent change > 50%
    result['alert'] = False
    pct = result.get('percent_change')
    if isinstance(pct, (int, float)):
        if abs(pct) > 50.0:
            result['alert'] = True
            # TODO: enqueue email alert here (e.g. add to EmailQueue or call mailer)
            # Example (pseudo):
            # EmailQueue.enqueue(subject=f"Price alert for product {product_id}",
            #                    body=f"Price changed {pct}% from {sp} to {ep} between {start} and {end}.")

    return result
