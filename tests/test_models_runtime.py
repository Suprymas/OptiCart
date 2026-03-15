from django.test import SimpleTestCase


class ModelsRuntimeTest(SimpleTestCase):
    def test_import_and_str_methods(self):
        # import inside the test so Django settings and app registry
        # are available (avoids collection-time errors)
        from django.contrib.auth.models import User
        import django
        # ensure Django app registry is ready before importing model classes
        django.setup()
        from shop import models

        # instantiate model-like objects without saving to DB
        p = models.Product(name='Milk', store='barbora', price='1.50')
        self.assertIn('Milk', str(p))

        bi = models.BasketItem(user=User(), product_name='Milk', quantity=2)
        self.assertIn('x2', str(bi))

        bt = models.BasketTemplate(user=User(), name='Weekly')
        self.assertIn('Template: Weekly', str(bt))

        bti = models.BasketTemplateItem(template=bt, product=p, quantity=3)
        self.assertIn('x3', str(bti))
