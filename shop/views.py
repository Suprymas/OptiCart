from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .search import search_products, has_search_results
from .comparison import compare_basket_prices
from .models import BasketItem, Product, PriceHistory
from .services import compare_template_prices, _get_price_at_date
from django.db import DatabaseError
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from django.urls import reverse


def search_view(request):
    query = request.GET.get('q', '')
    results = search_products(query)
    no_results = query != '' and not has_search_results(results)

    return render(request, 'shop/search_results.html', {
        'results': results,
        'query': query,
        'no_results': no_results,
    })


@login_required
def basket_comparison(request):
    basket_items = BasketItem.objects.filter(user=request.user)
    comparison = compare_basket_prices(basket_items)
    return render(request, 'shop/comparison.html', {'comparison': comparison})


@require_http_methods(["GET"])
def template_compare(request, template_id: int):
    """API endpoint: perform parallel price lookup for a BasketTemplate.

    Returns JSON with `items`, `totals`, and `cheapest_store`.
    """
    data = compare_template_prices(template_id)
    return JsonResponse(data)



@require_http_methods(["GET", "POST"])
def demo_save_template(request):
    """Demo page to show a simple Save-as-Template form without auth checks.

    This is for manual testing / UI preview only. It stores the submitted
    template name in the session under `demo_saved` and shows a small
    confirmation on the page.
    """
    # Hardcoded demo products shown on the page
    demo_products = [
        {'id': 'apples', 'name': 'Apelsinai'},
        {'id': 'milk', 'name': 'Pienas (1L)'},
        {'id': 'bread', 'name': 'Duona'},
        {'id': 'eggs', 'name': 'Kiaušiniai (10vnt)'},
        {'id': 'cheese', 'name': 'Sūris'},
    ]

    saved = None
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        # collect selected items and quantities
        items = []
        for p in demo_products:
            pid = p['id']
            if request.POST.get(f'select_{pid}'):
                try:
                    qty = int(request.POST.get(f'qty_{pid}', '1'))
                except ValueError:
                    qty = 1
                items.append({'product_name': p['name'], 'quantity': qty})

        if name:
            sess = request.session.setdefault('demo_saved', [])
            sess.append({'name': name, 'items': items})
            request.session.modified = True
            saved = name

    return render(request, 'shop/demo_save.html', {'saved': saved, 'products': demo_products})


def _synthetic_history_for_key(key: str, days: int = 30):
    """Return a deterministic synthetic daily price series for the last `days` days.

    Produces `days` points ending at today.
    """
    from datetime import date, timedelta

    today = date.today()
    series = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        # deterministic price based on hash of key and day
        base = 1.0 + (abs(hash(key + str(d.toordinal()))) % 200) / 100.0
        # add a smooth trend so the chart looks plausible
        price = round(base + ((i % 7) - 3) * 0.02, 2)
        series.append({'date': d.isoformat(), 'price': price})
    return series


def demo_chart_data(request):
    """Return JSON price history for a demo product.

    Query params:
      - product: product key (matches our demo product ids) or product name
    If PriceHistory exists for a matched real Product, return those rows. Otherwise
    return synthetic demo data.
    """
    from django.http import JsonResponse
    prod = request.GET.get('product')
    if not prod:
        return JsonResponse({'error': 'missing product'}, status=400)

    stores_param = request.GET.get('stores') or 'barbora,rimi,lidl'
    stores = [s.strip() for s in stores_param.split(',') if s.strip()]
    try:
        days = int(request.GET.get('interval', '30'))
    except ValueError:
        days = 30
    if days not in (7, 30, 90):
        days = 30

    result = {}
    for store in stores:
        # try to find a real product for this store; if DB isn't ready, fall back to synthetic
        try:
            p = Product.objects.filter(name__icontains=prod, store=store).first()
        except DatabaseError:
            p = None

        if p:
            try:
                # build daily series over the requested range
                from datetime import date, timedelta

                today = date.today()
                series = []
                for i in range(days - 1, -1, -1):
                    d = today - timedelta(days=i)
                    price = _get_price_at_date(p.id, d)
                    series.append({'date': d.isoformat(), 'price': float(price) if price is not None else None})
                result[store] = series
            except DatabaseError:
                # fallback to synthetic if any DB error occurs while fetching history
                result[store] = _synthetic_history_for_key(prod + '|' + store, days)
        else:
            # synthetic per-store
            result[store] = _synthetic_history_for_key(prod + '|' + store, days)

    return JsonResponse({'series': result})
