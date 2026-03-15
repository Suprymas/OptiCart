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
