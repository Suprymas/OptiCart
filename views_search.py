from .search import search_products, has_search_results


def search_view(request):
    from django.shortcuts import render
    query = request.GET.get('q', '')
    results = search_products(query)
    no_results = query != '' and not has_search_results(results)

    return render(request, 'shop/search_results.html', {
        'results': results,
        'query': query,
        'no_results': no_results,
    })
