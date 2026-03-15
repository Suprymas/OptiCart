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
from django.shortcuts import get_object_or_404


def search_view(request):
    query = request.GET.get('q', '')
    results_qs = search_products(query)
    no_results = query != '' and not has_search_results(results_qs)

    # prepare results list and attach current cart quantity (aggregated by product name)
    results = list(results_qs)
    sess_cart = request.session.get('cart', {})

    # Build name -> quantity map from session cart. Support old numeric-id keys and name keys.
    name_qty = {}
    if sess_cart:
        for key, val in sess_cart.items():
            try:
                pid = int(key)
                try:
                    prod = Product.objects.get(pk=pid)
                    name = prod.name
                except Exception:
                    name = str(key)
            except Exception:
                name = str(key)

            try:
                qty = int(val or 0)
            except Exception:
                qty = 0
            name_qty[name] = name_qty.get(name, 0) + qty

    # Group products by name preserving order
    groups = []
    seen_names = {}
    for p in results:
        pname = getattr(p, 'name', '')
        if pname in seen_names:
            groups[seen_names[pname]]['stores'].append(p)
        else:
            idx = len(groups)
            seen_names[pname] = idx
            groups.append({
                'name': pname,
                'stores': [p],
                'in_cart_qty': int(name_qty.get(pname, 0)) if name_qty.get(pname, 0) > 0 else 0,
                'rep_id': getattr(p, 'id', None),
            })

    return render(request, 'shop/search_results.html', {
        'groups': groups,
        'query': query,
        'no_results': no_results,
        'cart': sess_cart,
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


def search_api(request):
    """Return JSON list of matching product groups for client-side live search."""
    q = request.GET.get('q', '')
    results_qs = search_products(q)

    # build unique-name groups (name + representative id)
    groups = []
    seen = set()
    for p in results_qs:
        name = getattr(p, 'name', '')
        if name in seen:
            continue
        seen.add(name)
        groups.append({'name': name, 'rep_id': getattr(p, 'id', None)})

    return JsonResponse({'query': q, 'results': groups, 'no_results': q != '' and len(groups) == 0})


def product_detail(request, product_id: int):
    """Render product detail using the same product-group UI as search results.

    This preserves the quantity controls and add/update behaviour present
    in the search results listing.
    """
    prod = get_object_or_404(Product, pk=product_id)

    # find all products that share the same name (different stores)
    stores = list(Product.objects.filter(name=prod.name))

    # session cart map
    sess_cart = request.session.get('cart', {})

    # Build name -> quantity map from session cart. Support old numeric-id keys and name keys.
    name_qty = {}
    if sess_cart:
        for key, val in sess_cart.items():
            try:
                kpid = int(key)
                try:
                    p = Product.objects.get(pk=kpid)
                    name = p.name
                except Exception:
                    name = str(key)
            except Exception:
                name = str(key)

            try:
                qty = int(val or 0)
            except Exception:
                qty = 0
            name_qty[name] = name_qty.get(name, 0) + qty

    in_cart_qty = int(name_qty.get(prod.name, 0)) if name_qty.get(prod.name, 0) > 0 else 0

    return render(request, 'shop/product_detail.html', {
        'product': prod,
        'stores': stores,
        'in_cart_qty': in_cart_qty,
        'cart': sess_cart,
    })


@require_http_methods(["POST"])
def add_to_cart(request):
    """Add a product to session cart.

    Expects `product_id` and `quantity` in POST body (form or JSON).
    Ensures quantity is between 1 and 10. Adds to existing quantity up to 10.
    Returns JSON with the resulting quantity.
    """
    import json

    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    pid = data.get('product_id') or data.get('id') or data.get('product')
    qty = data.get('quantity') or data.get('qty')

    try:
        pid = int(pid)
        qty = int(qty)
    except Exception:
        return JsonResponse({'error': 'invalid input'}, status=400)

    if qty < 1:
        qty = 1
    if qty > 10:
        qty = 10

    # verify product exists and normalize cart key by product name
    try:
        prod = Product.objects.get(pk=pid)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'product not found'}, status=404)

    cart = request.session.get('cart', {})
    key_name = prod.name

    # detect if an entry for this product name already exists (either by name or by numeric id mapping)
    existed = False
    keys_to_remove = []
    for k, v in list(cart.items()):
        try:
            kpid = int(k)
            try:
                kprod = Product.objects.get(pk=kpid)
                if kprod.name == key_name:
                    existed = int(v or 0) > 0
                    keys_to_remove.append(k)
            except Exception:
                # leave unknown numeric key
                pass
        except Exception:
            # k is not numeric; treat as name
            if k == key_name:
                existed = int(v or 0) > 0

    # set/replace aggregated quantity under product name
    new_qty = qty
    cart[key_name] = new_qty
    # remove any old numeric-keyed entries for same product
    for k in keys_to_remove:
        cart.pop(k, None)

    request.session['cart'] = cart
    request.session.modified = True

    action = 'updated' if existed else 'added'
    return JsonResponse({'success': True, 'product_id': pid, 'quantity': new_qty, 'action': action})
