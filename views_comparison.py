from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import BasketItem
from .comparison import compare_basket_prices


@login_required
def basket_comparison(request):
    basket_items = BasketItem.objects.filter(user=request.user)
    comparison = compare_basket_prices(basket_items)
    return render(request, 'shop/comparison.html', {'comparison': comparison})
