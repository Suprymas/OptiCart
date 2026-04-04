from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Prefetch

from .search import (
    search_products,
    has_search_results,
    CATEGORY_OPTIONS,
    FILTER_UI_SCHEMA,
    get_selected_filters,
)
from .comparison import compare_basket_prices
from shop.models import Product, PriceHistory, BasketTemplate, BasketTemplateItem
from .services import compare_template_prices, _get_price_at_date
from django.db import DatabaseError
from django.urls import reverse
from django.shortcuts import get_object_or_404


@login_required(login_url='shop:login')
def home_view(request):
    """Display all comparable products with their prices from both stores, with search support."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    selected_filters = get_selected_filters(request.GET)
    
    # If search query is provided, use search, otherwise show all
    if query and len(query) >= 3:
        results_qs = search_products(query, category, selected_filters)
        groups_data = list(results_qs)
    else:
        # Get all unique product names
        unique_products = Product.objects.values('name').distinct()
        groups_data = []
        for prod_dict in unique_products:
            name = prod_dict['name']
            stores = list(Product.objects.filter(name=name).order_by('store'))
            if len(stores) == 2:
                groups_data.append({
                    'name': name,
                    'id': stores[0].id,
                    'image_url': stores[0].image_url or stores[1].image_url,
                })
    
    # Build product groups with both store prices
    groups = []
    seen_names = set()
    for item in groups_data:
        # Handle both Product objects and dictionaries
        name = item.name if hasattr(item, 'name') else item.get('name', '')
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        
        stores = list(Product.objects.filter(name=name).order_by('store'))
        if len(stores) == 2:
            image_url = None
            if hasattr(item, 'image_url'):
                image_url = item.image_url
            elif isinstance(item, dict) and 'image_url' in item:
                image_url = item.get('image_url')
            else:
                image_url = stores[0].image_url or stores[1].image_url
            
            groups.append({
                'name': name,
                'stores': stores,
                'rep_id': stores[0].id,
                'image_url': image_url,
            })
    
    # Session cart map
    sess_cart = request.session.get('cart', {})
    name_qty = {}
    if sess_cart:
        for key, val in sess_cart.items():
            try:
                pid = int(key)
                try:
                    prod = Product.objects.get(pk=pid)
                    name = prod.name
                except Exception:
                    name = str(key)
            except Exception:
                name = str(key)
            try:
                qty = int(val or 0)
            except Exception:
                qty = 0
            name_qty[name] = name_qty.get(name, 0) + qty
    
    # Attach cart quantities to groups
    for group in groups:
        group['in_cart_qty'] = int(name_qty.get(group['name'], 0)) if name_qty.get(group['name'], 0) > 0 else 0
    
    return render(request, 'shop/home.html', {
        'groups': groups,
        'cart': sess_cart,
        'query': query,
        'selected_category': category,
        'selected_filters': selected_filters,
        'filter_ui_schema': FILTER_UI_SCHEMA,
        'category_options': CATEGORY_OPTIONS,
    })


@login_required(login_url='shop:login')
def search_view(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    selected_filters = get_selected_filters(request.GET)
    results_qs = search_products(query, category, selected_filters)
    no_results = query != '' and not has_search_results(results_qs)

    # prepare results list and attach current cart quantity (aggregated by product name)
    results = list(results_qs)
    sess_cart = request.session.get('cart', {})

    # Build name -> quantity map from session cart. Support old numeric-id keys and name keys.
    name_qty = {}
    if sess_cart:
        for key, val in sess_cart.items():
            try:
                pid = int(key)
                try:
                    prod = Product.objects.get(pk=pid)
                    name = prod.name
                except Exception:
                    name = str(key)
            except Exception:
                name = str(key)

            try:
                qty = int(val or 0)
            except Exception:
                qty = 0
            name_qty[name] = name_qty.get(name, 0) + qty

    # Group products by name preserving order
    groups = []
    seen_names = {}
    for p in results:
        pname = getattr(p, 'name', '')
        if pname in seen_names:
            groups[seen_names[pname]]['stores'].append(p)
        else:
            idx = len(groups)
            seen_names[pname] = idx
            groups.append({
                'name': pname,
                'stores': [p],
                'in_cart_qty': int(name_qty.get(pname, 0)) if name_qty.get(pname, 0) > 0 else 0,
                'rep_id': getattr(p, 'id', None),
                'image_url': p.image_url if hasattr(p, 'image_url') and p.image_url else None,
            })

    return render(request, 'shop/search_results.html', {
        'groups': groups,
        'query': query,
        'selected_category': category,
        'selected_filters': selected_filters,
        'filter_ui_schema': FILTER_UI_SCHEMA,
        'category_options': CATEGORY_OPTIONS,
        'no_results': no_results,
        'cart': sess_cart,
    })


@login_required
def basket_comparison(request):
    from types import SimpleNamespace

    sess_cart = request.session.get('cart', {})
    basket_items = []
    for product_name, qty in sess_cart.items():
        try:
            quantity = int(qty)
        except Exception:
            continue
        if quantity <= 0:
            continue
        basket_items.append(
            SimpleNamespace(product_name=str(product_name), quantity=quantity)
        )

    comparison = compare_basket_prices(basket_items)
    return render(request, 'shop/comparison.html', {'comparison': comparison})


@login_required(login_url='shop:login')
def product_compare(request, product_name):
    """Display product comparison page with image and prices - only cheapest option."""
    from decimal import Decimal
    
    # Get all products with this name
    products = Product.objects.filter(name=product_name).order_by('store')
    
    if not products.exists():
        return render(request, 'shop/product_not_found.html', {'product_name': product_name})
    
    # Get image from the first product that has one
    image_url = None
    for p in products:
        if p.image_url:
            image_url = p.image_url
            break
    
    # Find the cheapest product and price difference
    cheapest_product = None
    price_difference = Decimal('0')
    other_price = None
    
    products_list = list(products)
    
    if len(products_list) == 2:
        if products_list[0].price <= products_list[1].price:
            cheapest_product = products_list[0]
            other_price = products_list[1].price
        else:
            cheapest_product = products_list[1]
            other_price = products_list[0].price
        
        price_difference = abs(other_price - cheapest_product.price)
    else:
        # If only one product exists, use it
        cheapest_product = products_list[0] if products_list else None
    
    # Session cart
    sess_cart = request.session.get('cart', {})
    
    return render(request, 'shop/product_compare.html', {
        'product_name': product_name,
        'all_products': products_list,
        'cheapest_product': cheapest_product,
        'image_url': image_url,
        'cart': sess_cart,
        'price_difference': price_difference,
        'has_comparison': len(products_list) == 2,
    })


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


def _synthetic_history_for_key(key: str, days: int = 30):
    """Return a deterministic synthetic daily price series for the last `days` days.

    Produces `days` points ending at today.
    """
    from datetime import date, timedelta

    today = date.today()
    series = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        # deterministic price based on hash of key and day
        base = 1.0 + (abs(hash(key + str(d.toordinal()))) % 200) / 100.0
        # add a smooth trend so the chart looks plausible
        price = round(base + ((i % 7) - 3) * 0.02, 2)
        series.append({'date': d.isoformat(), 'price': price})
    return series


def demo_chart_data(request):
    """Return JSON price history for a demo product.

    Query params:
      - product: product key (matches our demo product ids) or product name
    If PriceHistory exists for a matched real Product, return those rows. Otherwise
    return synthetic demo data.
    """
    from django.http import JsonResponse
    prod = request.GET.get('product')
    if not prod:
        return JsonResponse({'error': 'missing product'}, status=400)

    stores_param = request.GET.get('stores') or 'barbora,rimi,lidl'
    stores = [s.strip() for s in stores_param.split(',') if s.strip()]
    try:
        days = int(request.GET.get('interval', '30'))
    except ValueError:
        days = 30
    if days not in (7, 30, 90):
        days = 30

    result = {}
    for store in stores:
        # try to find a real product for this store; if DB isn't ready, fall back to synthetic
        try:
            p = Product.objects.filter(name__icontains=prod, store=store).first()
        except DatabaseError:
            p = None

        if p:
            try:
                # build daily series over the requested range
                from datetime import date, timedelta

                today = date.today()
                series = []
                for i in range(days - 1, -1, -1):
                    d = today - timedelta(days=i)
                    price = _get_price_at_date(p.id, d)
                    series.append({'date': d.isoformat(), 'price': float(price) if price is not None else None})
                result[store] = series
            except DatabaseError:
                # fallback to synthetic if any DB error occurs while fetching history
                result[store] = _synthetic_history_for_key(prod + '|' + store, days)
        else:
            # synthetic per-store
            result[store] = _synthetic_history_for_key(prod + '|' + store, days)

    return JsonResponse({'series': result})


def search_api(request):
    """Return JSON list of matching product groups for client-side live search."""
    q = request.GET.get('q', '')
    category = request.GET.get('category', '')
    selected_filters = get_selected_filters(request.GET)
    q_normalized = (q or '').strip()

    if not q_normalized:
        # Return all comparable products (available in both stores) for clear-search restore.
        groups = []
        for name in Product.objects.values_list('name', flat=True).distinct():
            stores = list(Product.objects.filter(name=name).order_by('store'))
            if len(stores) != 2:
                continue
            image_url = stores[0].image_url or stores[1].image_url
            groups.append({
                'name': name,
                'rep_id': stores[0].id,
                'image_url': image_url,
            })

        return JsonResponse({
            'query': q,
            'category': category,
            'selected_filters': selected_filters,
            'results': groups,
            'no_results': False,
        })

    results_qs = search_products(q, category, selected_filters)

    # build unique-name groups (name + representative id + image_url)
    groups = []
    seen = set()
    for p in results_qs:
        name = getattr(p, 'name', '')
        if name in seen:
            continue
        seen.add(name)
        image_url = p.image_url if hasattr(p, 'image_url') and p.image_url else None
        groups.append({
            'name': name,
            'rep_id': getattr(p, 'id', None),
            'image_url': image_url,
        })

    return JsonResponse({
        'query': q,
        'category': category,
        'selected_filters': selected_filters,
        'results': groups,
        'no_results': q != '' and len(groups) == 0,
    })


@login_required(login_url='shop:login')
def product_detail(request, product_id: int):
    """Render product detail using the same product-group UI as search results.

    This preserves the quantity controls and add/update behaviour present
    in the search results listing.
    """
    prod = get_object_or_404(Product, pk=product_id)

    # find all products that share the same name (different stores)
    stores = list(Product.objects.filter(name=prod.name))

    # session cart map
    sess_cart = request.session.get('cart', {})

    # Build name -> quantity map from session cart. Support old numeric-id keys and name keys.
    name_qty = {}
    if sess_cart:
        for key, val in sess_cart.items():
            try:
                kpid = int(key)
                try:
                    p = Product.objects.get(pk=kpid)
                    name = p.name
                except Exception:
                    name = str(key)
            except Exception:
                name = str(key)

            try:
                qty = int(val or 0)
            except Exception:
                qty = 0
            name_qty[name] = name_qty.get(name, 0) + qty

    in_cart_qty = int(name_qty.get(prod.name, 0)) if name_qty.get(prod.name, 0) > 0 else 0

    return render(request, 'shop/product_detail.html', {
        'product': prod,
        'stores': stores,
        'in_cart_qty': in_cart_qty,
        'cart': sess_cart,
    })


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def add_to_cart(request):
    """Add a product to session cart.

    Expects `product_id` and `quantity` in POST body (form or JSON).
    Ensures quantity is between 1 and 10. Adds to existing quantity up to 10.
    Returns JSON with the resulting quantity.
    """
    import json

    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    pid = data.get('product_id') or data.get('id') or data.get('product')
    qty = data.get('quantity') or data.get('qty')

    try:
        pid = int(pid)
        qty = int(qty)
    except Exception:
        return JsonResponse({'error': 'invalid input'}, status=400)

    if qty < 1:
        qty = 1
    if qty > 10:
        qty = 10

    # verify product exists and normalize cart key by product name
    try:
        prod = Product.objects.get(pk=pid)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'product not found'}, status=404)

    cart = request.session.get('cart', {})
    key_name = prod.name

    # detect if an entry for this product name already exists (either by name or by numeric id mapping)
    existed = False
    keys_to_remove = []
    for k, v in list(cart.items()):
        try:
            kpid = int(k)
            try:
                kprod = Product.objects.get(pk=kpid)
                if kprod.name == key_name:
                    existed = int(v or 0) > 0
                    keys_to_remove.append(k)
            except Exception:
                # leave unknown numeric key
                pass
        except Exception:
            # k is not numeric; treat as name
            if k == key_name:
                existed = int(v or 0) > 0

    # set/replace aggregated quantity under product name
    new_qty = qty
    cart[key_name] = new_qty
    # remove any old numeric-keyed entries for same product
    for k in keys_to_remove:
        cart.pop(k, None)

    request.session['cart'] = cart
    request.session.modified = True

    action = 'updated' if existed else 'added'
    return JsonResponse({'success': True, 'product_id': pid, 'quantity': new_qty, 'action': action})


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def remove_from_basket(request):
    """Remove a product from session cart.

    Expects `product_name` in POST body (form or JSON).
    Returns JSON with success status.
    """
    import json

    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    product_name = data.get('product_name')
    
    if not product_name:
        return JsonResponse({'error': 'product_name required'}, status=400)

    cart = request.session.get('cart', {})
    
    # Remove by exact name match
    if product_name in cart:
        del cart[product_name]
        request.session['cart'] = cart
        request.session.modified = True
        return JsonResponse({'success': True, 'product_name': product_name})
    
    return JsonResponse({'error': 'product not in cart'}, status=404)


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def save_basket_as_template(request):
    """Save current session basket as a named template.

    Expects `template_name` in POST body (form or JSON).
    Returns JSON with success status and template ID.
    """
    import json

    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    template_name = data.get('template_name', '').strip()
    
    if not template_name:
        return JsonResponse({'error': 'template_name required'}, status=400)

    if len(template_name) < 5:
        return JsonResponse({'error': 'template name must be at least 5 characters'}, status=400)

    if len(template_name) > 30:
        return JsonResponse({'error': 'template name cannot exceed 30 characters'}, status=400)

    cart = request.session.get('cart', {})
    
    if not cart:
        return JsonResponse({'error': 'basket is empty'}, status=400)

    try:
        # Create the template
        template = BasketTemplate.objects.create(
            user=request.user,
            name=template_name
        )
        
        # Add items to template
        for product_name, quantity in cart.items():
            # Find product by name (prefer first match, typically from Barbora)
            product = Product.objects.filter(name=product_name).first()
            if product:
                BasketTemplateItem.objects.create(
                    template=template,
                    product=product,
                    quantity=int(quantity)
                )
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'template_name': template.name
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def login_view(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Redirect to next page or home
            next_page = request.GET.get('next', '')
            if next_page:
                return redirect(next_page)
            return redirect('shop:home')
        else:
            # Authentication failed
            return render(request, 'shop/login.html', {
                'error': 'Neteisingas naudotojo vardas arba slaptažodis.'
            })
    
    return render(request, 'shop/login.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    return redirect('shop:home')


@login_required(login_url='shop:login')
def basket_view(request):
    """Display current basket items from session."""
    sess_cart = request.session.get('cart', {})
    
    # Build list of items with product details
    items = []
    total_price = 0
    
    for product_name, qty in sess_cart.items():
        try:
            qty = int(qty)
            if qty <= 0:
                continue
            
            # Get product info (use any store version)
            product = Product.objects.filter(name=product_name).first()
            if not product:
                continue
            
            # Get all versions of this product (from different stores)
            stores = list(Product.objects.filter(name=product_name).order_by('store'))
            
            
            items.append({
                'name': product_name,
                'quantity': qty,
                'stores': stores,
                'image_url': product.image_url,
            })
            
        except (ValueError, Exception):
            continue
    
    return render(request, 'shop/basket.html', {
        'items': items,
        'total_items': sum(item['quantity'] for item in items),
        'empty': len(items) == 0,
    })


@login_required(login_url='shop:login')
def templates_view(request):
    """Display list of user's saved basket templates."""
    from shop.models import BasketTemplate
    
    templates = BasketTemplate.objects.filter(user=request.user).prefetch_related('items__product').order_by('-id')
    
    # Add item count to each template
    template_list = []
    for template in templates:
        items_count = template.items.count()
        template_list.append({
            'id': template.id,
            'name': template.name,
            'items_count': items_count,
            'template': template,
        })
    
    return render(request, 'shop/templates.html', {
        'templates': template_list,
        'empty': len(template_list) == 0,
    })


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def load_template(request):
    """Load a saved template into the session cart.

    Expects `template_id` in POST body (form or JSON).
    Clears current cart and replaces with template items.
    Returns JSON with success status.
    """
    import json

    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    template_id = data.get('template_id')
    
    if not template_id:
        return JsonResponse({'error': 'template_id required'}, status=400)

    try:
        template_id = int(template_id)
    except Exception:
        return JsonResponse({'error': 'invalid template_id'}, status=400)

    try:
        # Verify template belongs to user
        template = BasketTemplate.objects.get(id=template_id, user=request.user)
        
        # Build new cart from template items
        cart = {}
        for item in template.items.all():
            product_name = item.product.name
            cart[product_name] = item.quantity
        
        # Replace session cart
        request.session['cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'template_name': template.name,
            'items_count': template.items.count()
        })
    except BasketTemplate.DoesNotExist:
        return JsonResponse({'error': 'template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def delete_template(request):
    """Delete a saved basket template.

    Expects `template_id` in POST body (form or JSON).
    Only allows deletion of user's own templates.
    Returns JSON with success status.
    """
    import json


    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    template_id = data.get('template_id')
    
    if not template_id:
        return JsonResponse({'error': 'template_id required'}, status=400)

    try:
        template_id = int(template_id)
    except Exception:
        return JsonResponse({'error': 'invalid template_id'}, status=400)

    try:
        # Verify template belongs to user
        template = BasketTemplate.objects.get(id=template_id, user=request.user)
        template_name = template.name
        
        # Delete the template (cascades to items)
        template.delete()
        
        return JsonResponse({
            'success': True,
            'template_id': template_id,
            'template_name': template_name
        })
    except BasketTemplate.DoesNotExist:
        return JsonResponse({'error': 'template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='shop:login')
def edit_template(request, template_id):
    """Display template editor with ability to add/remove products."""

    
    try:
        template_id = int(template_id)
    except Exception:
        return redirect('shop:templates')
    
    try:
        template = BasketTemplate.objects.get(id=template_id, user=request.user)
    except BasketTemplate.DoesNotExist:
        return redirect('shop:templates')
    
    # Get template items with product details
    items = []
    for item in template.items.all():
        product = item.product
        # Get all versions of this product (from different stores)
        stores = list(Product.objects.filter(name=product.name).order_by('store'))
        
        items.append({
            'id': item.id,
            'product_id': product.id,
            'product_name': product.name,
            'quantity': item.quantity,
            'stores': stores,
            'image_url': product.image_url,
        })
    
    return render(request, 'shop/edit_template.html', {
        'template': template,
        'items': items,
        'empty': len(items) == 0,
    })


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def add_to_template(request):
    """Add a product to a saved template.

    Expects `template_id`, `product_id`, and `quantity` in POST body (form or JSON).
    Returns JSON with success status.
    """
    import json


    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    template_id = data.get('template_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not template_id or not product_id:
        return JsonResponse({'error': 'template_id and product_id required'}, status=400)

    try:
        template_id = int(template_id)
        product_id = int(product_id)
        quantity = int(quantity)
    except Exception:
        return JsonResponse({'error': 'invalid parameters'}, status=400)

    if quantity < 1 or quantity > 10:
        quantity = 1

    try:
        # Verify template belongs to user
        template = BasketTemplate.objects.get(id=template_id, user=request.user)
        
        # Verify product exists
        product = Product.objects.get(pk=product_id)
        
        # Add or update template item
        item, created = BasketTemplateItem.objects.update_or_create(
            template=template,
            product=product,
            defaults={'quantity': quantity}
        )
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'product_id': product.id,
            'product_name': product.name,
            'quantity': quantity
        })
    except BasketTemplate.DoesNotExist:
        return JsonResponse({'error': 'template not found'}, status=404)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='shop:login')
@require_http_methods(["POST"])
def remove_from_template(request):
    """Remove a product from a saved template.

    Expects `template_id` and `product_id` in POST body (form or JSON).
    Returns JSON with success status.
    """
    import json


    # try POST (form) first, otherwise parse JSON body
    data = request.POST if request.POST else {}
    if not data:
        try:
            data = json.loads(request.body.decode() or '{}')
        except Exception:
            data = {}

    template_id = data.get('template_id')
    product_id = data.get('product_id')
    
    if not template_id or not product_id:
        return JsonResponse({'error': 'template_id and product_id required'}, status=400)

    try:
        template_id = int(template_id)
        product_id = int(product_id)
    except Exception:
        return JsonResponse({'error': 'invalid parameters'}, status=400)

    try:
        # Verify template belongs to user
        template = BasketTemplate.objects.get(id=template_id, user=request.user)
        
        # Delete template item
        deleted_count, _ = BasketTemplateItem.objects.filter(
            template=template,
            product_id=product_id
        ).delete()
        
        if deleted_count == 0:
            return JsonResponse({'error': 'item not found in template'}, status=404)
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'product_id': product_id
        })
    except BasketTemplate.DoesNotExist:
        return JsonResponse({'error': 'template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

