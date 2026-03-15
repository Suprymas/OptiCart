from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .search import search_products, has_search_results
from .comparison import compare_basket_prices
from .models import BasketItem


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
