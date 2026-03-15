from django.urls import path

from .views import search_view, basket_comparison

app_name = 'shop'

urlpatterns = [
    path('', search_view, name='search'),
    path('compare/', basket_comparison, name='compare'),
]
