from .models import Product


def compare_basket_prices(basket_items):
    """
    KAN-35: Palygina krepšelio prekių kainas tarp parduotuvių (Barbora ir Rimi).
    Grąžina žodyną su kainomis pagal parduotuvę ir pigiausią variantą.
    """
    stores = ['barbora', 'rimi']

    result = {
        'items': [],
        'totals': {store: 0 for store in stores},
        'cheapest_store': None,
    }

    for item in basket_items:
        item_data = {
            'name': item.product_name,
            'quantity': item.quantity,
            'prices': {},
        }

        for store in stores:
            product = Product.objects.filter(
                name__icontains=item.product_name,
                store=store
            ).first()

            if product:
                item_data['prices'][store] = round(float(product.price) * item.quantity, 2)
            else:
                item_data['prices'][store] = None

        result['items'].append(item_data)

    for store in stores:
        prices = [
            item['prices'][store]
            for item in result['items']
            if item['prices'][store] is not None
        ]
        result['totals'][store] = round(sum(prices), 2)

    if any(result['totals'].values()):
        result['cheapest_store'] = min(result['totals'], key=result['totals'].get)

    return result
