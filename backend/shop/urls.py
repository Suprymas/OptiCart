from django.urls import path

from .views import home_view, search_view, basket_comparison, template_compare, demo_save_template, demo_chart_data, add_to_cart, remove_from_basket, save_basket_as_template, templates_view, load_template, delete_template, edit_template, add_to_template, remove_from_template, search_api, product_detail, product_compare, login_view, logout_view, basket_view

app_name = 'shop'

urlpatterns = [
    path('', home_view, name='home'),
    path('product/<str:product_name>/compare/', product_compare, name='product_compare'),
    path('search/', search_view, name='search'),
    path('api/search/', search_api, name='search_api'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('basket/', basket_view, name='basket'),
    path('templates/', templates_view, name='templates'),
    path('templates/<int:template_id>/edit/', edit_template, name='edit_template'),
    path('load-template/', load_template, name='load_template'),
    path('delete-template/', delete_template, name='delete_template'),
    path('add-to-template/', add_to_template, name='add_to_template'),
    path('remove-from-template/', remove_from_template, name='remove_from_template'),
    path('compare/', basket_comparison, name='compare'),
    path('compare/demo/', demo_save_template, name='compare_demo'),
    path('compare/demo/chart-data/', demo_chart_data, name='compare_demo_chart'),
    path('template/<int:template_id>/compare/', template_compare, name='template_compare'),
    path('add-to-cart/', add_to_cart, name='add_to_cart'),
    path('remove-from-basket/', remove_from_basket, name='remove_from_basket'),
    path('save-basket-as-template/', save_basket_as_template, name='save_basket_as_template'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
