from .models import Product


def process_search_query(raw_query):
    """
    KAN-39: Paruošia paieškos užklausą apdorojimui.
    Pašalina tarpus ir konvertuoja į mažąsias raides.
    """
    return raw_query.strip().lower()


def search_products(raw_query):
    """
    KAN-37: Vykdo paiešką ir grąžina rezultatus.
    Jei užklausa tuščia – grąžina tuščią QuerySet.
    """
    query = process_search_query(raw_query)

    if not query:
        return Product.objects.none()

    return Product.objects.filter(name__icontains=query)


def has_search_results(results):
    """
    KAN-37: Patikrina ar paieška grąžino bent vieną rezultatą.
    """
    return results.exists()
