from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .search import search_products, has_search_results
from .comparison import compare_basket_prices
from .models import BasketItem
from .services import compare_template_prices
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
