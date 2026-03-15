from typing import Iterable, Any, Tuple, Optional

from django.contrib.auth.models import User

from .models import BasketTemplate, BasketTemplateItem, Product


def _extract_product_and_quantity(order_item: Any) -> Tuple[Optional[Product], int]:
    """Extract a Product instance and quantity from an order-item-like object.

    Supports objects with attributes or dict-like objects. Returns (product_or_None, quantity).
    """
    # Try attribute access first
    product = getattr(order_item, "product", None)
    if product is None and hasattr(order_item, "get"):
        product = order_item.get("product")

    quantity = getattr(order_item, "quantity", None)
    if quantity is None and hasattr(order_item, "get"):
        quantity = order_item.get("quantity")

    if product:
        return product, int(quantity or 1)

    # try product_id
    pid = getattr(order_item, "product_id", None)
    if pid is None and hasattr(order_item, "get"):
        pid = order_item.get("product_id")

    if pid:
        try:
            p = Product.objects.get(pk=pid)
            return p, int(quantity or 1)
        except Product.DoesNotExist:
            return None, int(quantity or 1)

    # try product_name
    pname = getattr(order_item, "product_name", None)
    if pname is None and hasattr(order_item, "get"):
        pname = order_item.get("product_name")

    if pname:
        p = Product.objects.filter(name__icontains=pname).first()
        return p, int(quantity or 1)

    return None, int(quantity or 1)


def duplicate_template(template_id: int, user: User, new_name: Optional[str] = None) -> BasketTemplate:
    """Duplicate a BasketTemplate (and its items) for the given user.

    Returns the new BasketTemplate.
    """
    template = BasketTemplate.objects.get(pk=template_id)
    name = new_name or f"{template.name} (copy)"
    new = BasketTemplate.objects.create(user=user, name=name)

    for item in template.items.all():
        BasketTemplateItem.objects.create(template=new, product=item.product, quantity=item.quantity)

    return new


def create_template_from_order(user: User, name: str, order_items: Iterable[Any]) -> BasketTemplate:
    """Create a new BasketTemplate from order-like items.

    Items that cannot be resolved to a Product are skipped.
    """
    tpl = BasketTemplate.objects.create(user=user, name=name)

    for oi in order_items:
        product, qty = _extract_product_and_quantity(oi)
        if product is None:
            continue
        BasketTemplateItem.objects.create(template=tpl, product=product, quantity=qty)

    return tpl


def restore_template_from_order(template_id: int, order_items: Iterable[Any]) -> BasketTemplate:
    """Replace the items of an existing BasketTemplate with items from an order."""
    tpl = BasketTemplate.objects.get(pk=template_id)
    tpl.items.all().delete()

    for oi in order_items:
        product, qty = _extract_product_and_quantity(oi)
        if product is None:
            continue
        BasketTemplateItem.objects.create(template=tpl, product=product, quantity=qty)

    return tpl
