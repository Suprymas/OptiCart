from django.urls import path

from .views import home_view, search_view, basket_comparison, template_compare, demo_save_template, demo_chart_data, add_to_cart, search_api, product_detail, product_compare

app_name = 'shop'

urlpatterns = [
    path('', home_view, name='home'),
    path('product/<str:product_name>/compare/', product_compare, name='product_compare'),
    path('search/', search_view, name='search'),
    path('api/search/', search_api, name='search_api'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('compare/', basket_comparison, name='compare'),
    path('compare/demo/', demo_save_template, name='compare_demo'),
    path('compare/demo/chart-data/', demo_chart_data, name='compare_demo_chart'),
    path('template/<int:template_id>/compare/', template_compare, name='template_compare'),
    path('add-to-cart/', add_to_cart, name='add_to_cart'),
]
