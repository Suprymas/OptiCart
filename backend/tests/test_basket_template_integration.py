from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from shop.models import Product, BasketTemplate, BasketTemplateItem
import json


class BasketTemplateIntegrationTests(TestCase):
    """Integration tests for basket and template workflow."""

    def setUp(self):
        """Set up test client, user, and products."""
        self.client = Client()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test products
        self.product1 = Product.objects.create(
            name='Pienas',
            store='barbora',
            price=1.50,
            image_url='http://example.com/pienas.jpg'
        )
        self.product2 = Product.objects.create(
            name='Duona',
            store='barbora',
            price=2.00,
            image_url='http://example.com/duona.jpg'
        )
        self.product3 = Product.objects.create(
            name='Sviestas',
            store='barbora',
            price=3.50,
            image_url='http://example.com/sviestas.jpg'
        )

    def test_add_product_to_basket(self):
        """Test adding a product to basket."""
        resp = self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 2
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['quantity'], 2)
        
        # Verify session
        self.assertEqual(
            self.client.session.get('cart', {}).get('Pienas'),
            2
        )

    def test_save_basket_as_template(self):
        """Test saving basket as template."""
        # Add products to basket
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 2
            }),
            content_type='application/json'
        )
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product2.id,
                'quantity': 1
            }),
            content_type='application/json'
        )
        
        # Save basket as template
        resp = self.client.post(
            '/save-basket-as-template/',
            data=json.dumps({'template_name': 'Savaitės pirkiniai'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['template_name'], 'Savaitės pirkiniai')
        
        # Verify template created
        template = BasketTemplate.objects.get(id=data['template_id'])
        self.assertEqual(template.name, 'Savaitės pirkiniai')
        self.assertEqual(template.user, self.user)
        self.assertEqual(template.items.count(), 2)

    def test_load_template_into_basket(self):
        """Test loading template into basket."""
        # Create template
        template = BasketTemplate.objects.create(
            user=self.user,
            name='Test template'
        )
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product1,
            quantity=3
        )
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product2,
            quantity=2
        )
        
        # Load template
        resp = self.client.post(
            '/load-template/',
            data=json.dumps({'template_id': template.id}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        
        # Verify basket contains template items
        session_cart = self.client.session.get('cart', {})
        self.assertEqual(session_cart.get('Pienas'), 3)
        self.assertEqual(session_cart.get('Duona'), 2)

    def test_add_product_to_template(self):
        """Test adding product to existing template."""
        template = BasketTemplate.objects.create(
            user=self.user,
            name='Test template'
        )
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product1,
            quantity=1
        )
        
        # Add product to template
        resp = self.client.post(
            '/add-to-template/',
            data=json.dumps({
                'template_id': template.id,
                'product_id': self.product2.id,
                'quantity': 2
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        
        # Verify template updated
        self.assertEqual(template.items.count(), 2)
        item = BasketTemplateItem.objects.get(product=self.product2)
        self.assertEqual(item.quantity, 2)

    def test_remove_product_from_template(self):
        """Test removing product from template."""
        template = BasketTemplate.objects.create(
            user=self.user,
            name='Test template'
        )
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product1,
            quantity=1
        )
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product2,
            quantity=2
        )
        
        # Remove product from template
        resp = self.client.post(
            '/remove-from-template/',
            data=json.dumps({
                'template_id': template.id,
                'product_id': self.product1.id
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        
        # Verify item removed
        self.assertEqual(template.items.count(), 1)
        self.assertTrue(
            template.items.filter(product=self.product2).exists()
        )

    def test_delete_template(self):
        """Test deleting a template."""
        template = BasketTemplate.objects.create(
            user=self.user,
            name='Test template'
        )
        template_id = template.id
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product1,
            quantity=1
        )
        
        # Delete template
        resp = self.client.post(
            '/delete-template/',
            data=json.dumps({'template_id': template_id}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        
        # Verify template deleted
        self.assertFalse(
            BasketTemplate.objects.filter(id=template_id).exists()
        )

    def test_full_workflow(self):
        """Test complete workflow: add → save → load → edit → delete."""
        # 1. Add products to basket
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 2
            }),
            content_type='application/json'
        )
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product2.id,
                'quantity': 1
            }),
            content_type='application/json'
        )
        
        # 2. Save as template
        save_resp = self.client.post(
            '/save-basket-as-template/',
            data=json.dumps({'template_name': 'Mano šablonas'}),
            content_type='application/json'
        )
        template_id = save_resp.json()['template_id']
        
        # 3. Clear basket by loading a new one (verify it replaces)
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product3.id,
                'quantity': 5
            }),
            content_type='application/json'
        )
        
        # 4. Load template (should replace basket)
        load_resp = self.client.post(
            '/load-template/',
            data=json.dumps({'template_id': template_id}),
            content_type='application/json'
        )
        self.assertTrue(load_resp.json()['success'])
        
        # Verify basket is from template, not product3
        session_cart = self.client.session.get('cart', {})
        self.assertEqual(session_cart.get('Pienas'), 2)
        self.assertEqual(session_cart.get('Duona'), 1)
        self.assertNotIn('Sviestas', session_cart)
        
        # 5. Add new product to template
        add_resp = self.client.post(
            '/add-to-template/',
            data=json.dumps({
                'template_id': template_id,
                'product_id': self.product3.id,
                'quantity': 3
            }),
            content_type='application/json'
        )
        self.assertTrue(add_resp.json()['success'])
        
        # 6. Verify template has 3 items now
        template = BasketTemplate.objects.get(id=template_id)
        self.assertEqual(template.items.count(), 3)
        
        # 7. Delete template
        delete_resp = self.client.post(
            '/delete-template/',
            data=json.dumps({'template_id': template_id}),
            content_type='application/json'
        )
        self.assertTrue(delete_resp.json()['success'])
        
        # 8. Verify deleted
        self.assertFalse(
            BasketTemplate.objects.filter(id=template_id).exists()
        )

    # ===== ERROR CASE TESTS =====

    def test_save_template_empty_name(self):
        """Test saving template with empty name fails."""
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 1
            }),
            content_type='application/json'
        )
        
        resp = self.client.post(
            '/save-basket-as-template/',
            data=json.dumps({'template_name': ''}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_save_template_name_too_short(self):
        """Test saving template with name < 5 chars fails."""
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 1
            }),
            content_type='application/json'
        )
        
        resp = self.client.post(
            '/save-basket-as-template/',
            data=json.dumps({'template_name': 'abc'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('5 characters', resp.json()['error'])

    def test_save_template_name_too_long(self):
        """Test saving template with name > 30 chars fails."""
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 1
            }),
            content_type='application/json'
        )
        
        resp = self.client.post(
            '/save-basket-as-template/',
            data=json.dumps({
                'template_name': 'a' * 31
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('30 characters', resp.json()['error'])

    def test_save_empty_basket_fails(self):
        """Test saving empty basket as template fails."""
        resp = self.client.post(
            '/save-basket-as-template/',
            data=json.dumps({'template_name': 'Empty basket'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('empty', resp.json()['error'])

    def test_load_nonexistent_template_fails(self):
        """Test loading non-existent template fails."""
        resp = self.client.post(
            '/load-template/',
            data=json.dumps({'template_id': 99999}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 404)
        self.assertIn('error', resp.json())

    def test_remove_product_not_in_template_fails(self):
        """Test removing product not in template fails."""
        template = BasketTemplate.objects.create(
            user=self.user,
            name='Test template'
        )
        
        resp = self.client.post(
            '/remove-from-template/',
            data=json.dumps({
                'template_id': template.id,
                'product_id': self.product1.id
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 404)
        self.assertIn('not found', resp.json()['error'])

    def test_delete_nonexistent_template_fails(self):
        """Test deleting non-existent template fails."""
        resp = self.client.post(
            '/delete-template/',
            data=json.dumps({'template_id': 99999}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 404)
        self.assertIn('error', resp.json())

    def test_user_cannot_access_other_users_template(self):
        """Test user cannot load other user's template."""
        other_user = get_user_model().objects.create_user(
            username='otheruser',
            password='pass123'
        )
        template = BasketTemplate.objects.create(
            user=other_user,
            name='Other user template'
        )
        BasketTemplateItem.objects.create(
            template=template,
            product=self.product1,
            quantity=1
        )
        
        # Try to load other user's template
        resp = self.client.post(
            '/load-template/',
            data=json.dumps({'template_id': template.id}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 404)

    def test_remove_from_basket(self):
        """Test removing product from basket."""
        # Add product
        self.client.post(
            '/add-to-cart/',
            data=json.dumps({
                'product_id': self.product1.id,
                'quantity': 2
            }),
            content_type='application/json'
        )
        
        # Remove from basket
        resp = self.client.post(
            '/remove-from-basket/',
            data=json.dumps({'product_name': 'Pienas'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])
        
        # Verify removed from session
        self.assertNotIn('Pienas', self.client.session.get('cart', {}))
