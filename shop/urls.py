from django.urls import path

from .views import search_view, basket_comparison, template_compare

app_name = 'shop'

urlpatterns = [
    path('', search_view, name='search'),
    path('compare/', basket_comparison, name='compare'),
    path('template/<int:template_id>/compare/', template_compare, name='template_compare'),
]
