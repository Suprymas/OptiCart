from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    STORE_CHOICES = [
        ('barbora', 'Barbora'),
        ('rimi', 'Rimi'),
    ]

    name = models.CharField(max_length=255)
    store = models.CharField(max_length=50, choices=STORE_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.store}) - {self.price}€"


class BasketItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class BasketTemplate(models.Model):
    """Krepšelio šablonas: turi Id (auto), naudotojo id ir pavadinimą."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="basket_templates")
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"Template: {self.name} (user_id={self.user_id})"


class BasketTemplateItem(models.Model):
    """Krepšelio šablono prekė: turi šablono id, produkto id, kiekį."""

    template = models.ForeignKey(BasketTemplate, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="template_items")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("template", "product")

    def __str__(self):
        return f"{self.product.name} x{self.quantity} (template={self.template_id})"


class PriceHistory(models.Model):
    """Historical prices for a Product.

    Fields:
      - product: FK to Product
      - date_from: when this price becomes valid (inclusive)
      - date_until: when this price stops being valid (exclusive). Nullable when open-ended.
      - price: the price value

    Indexes are added to speed up queries by product and by date ranges.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    date_from = models.DateField()
    date_until = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['product', 'date_from']),
            models.Index(fields=['product', 'date_until']),
            models.Index(fields=['date_from', 'date_until']),
        ]
        ordering = ['-date_from']

    def __str__(self) -> str:
        until = self.date_until.isoformat() if self.date_until else 'ongoing'
        return f"PriceHistory: {self.product.name} {self.price} from {self.date_from.isoformat()} until {until}"
