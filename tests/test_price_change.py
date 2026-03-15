import datetime

import pytest

from shop.models import Product, PriceHistory
from shop.services import compute_price_change


@pytest.mark.django_db
def test_compute_price_change_basic():
    p = Product.objects.create(name='Test Milk', store='barbora', price='1.00')

    # price 1.00 for Jan, then 1.20 from Feb onward
    PriceHistory.objects.create(product=p, date_from=datetime.date(2026, 1, 1), date_until=datetime.date(2026, 2, 1), price='1.00')
    PriceHistory.objects.create(product=p, date_from=datetime.date(2026, 2, 1), date_until=None, price='1.20')

    res = compute_price_change(p.id, datetime.date(2026, 1, 15), datetime.date(2026, 2, 15))
    assert float(res['start_price']) == 1.00
    assert float(res['end_price']) == 1.20
    assert round(res['percent_change'], 2) == 20.00


@pytest.mark.django_db
def test_compute_price_change_missing():
    p = Product.objects.create(name='Mystery', store='rimi', price='5.00')
    # no price history
    res = compute_price_change(p.id, datetime.date(2026, 1, 1), datetime.date(2026, 2, 1))
    assert res['start_price'] is None
    assert res['end_price'] is None
    assert 'missing' in res