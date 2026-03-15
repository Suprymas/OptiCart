from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .search import search_products, has_search_results
from .comparison import compare_basket_prices
from .models import BasketItem
from .services import compare_template_prices


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
