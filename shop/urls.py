from django.urls import path

from .views import search_view, basket_comparison, template_compare, demo_save_template

app_name = 'shop'

urlpatterns = [
    path('', search_view, name='search'),
    path('compare/', basket_comparison, name='compare'),
    path('compare/demo/', demo_save_template, name='compare_demo'),
    path('template/<int:template_id>/compare/', template_compare, name='template_compare'),
]
