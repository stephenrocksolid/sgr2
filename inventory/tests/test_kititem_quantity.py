from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from inventory.models import Kit, KitItem, Part, Vendor, Engine, BuildList
from inventory.forms import KitItemForm
from decimal import Decimal


class KitItemQuantityTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        
        # Create test data
        self.engine = Engine.objects.create(
            engine_make='Test Make',
            engine_model='Test Model'
        )
        self.build_list = BuildList.objects.create(
            engine=self.engine,
            name='Test Build List'
        )
        self.kit = Kit.objects.create(
            build_list=self.build_list,
            name='Test Kit'
        )
        self.part = Part.objects.create(
            part_number='TEST-001',
            name='Test Part'
        )
        self.vendor = Vendor.objects.create(
            name='Test Vendor'
        )
    
    def test_kititem_form_accepts_integer_quantity(self):
        """Test that KitItemForm accepts integer quantities."""
        form_data = {
            'part': self.part.id,
            'vendor': self.vendor.id,
            'quantity': '5',
            'unit_cost': '10.00',
            'notes': 'Test notes'
        }
        form = KitItemForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['quantity'], 5)
    
    def test_kititem_form_rejects_decimal_quantity(self):
        """Test that KitItemForm rejects decimal quantities."""
        form_data = {
            'part': self.part.id,
            'vendor': self.vendor.id,
            'quantity': '5.5',
            'unit_cost': '10.00',
            'notes': 'Test notes'
        }
        form = KitItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Quantity must be a whole number.', str(form.errors))
    
    def test_kititem_form_rejects_zero_quantity(self):
        """Test that KitItemForm rejects zero quantities."""
        form_data = {
            'part': self.part.id,
            'vendor': self.vendor.id,
            'quantity': '0',
            'unit_cost': '10.00',
            'notes': 'Test notes'
        }
        form = KitItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Quantity must be at least 1.', str(form.errors))
    
    def test_kititem_form_rejects_negative_quantity(self):
        """Test that KitItemForm rejects negative quantities."""
        form_data = {
            'part': self.part.id,
            'vendor': self.vendor.id,
            'quantity': '-1',
            'unit_cost': '10.00',
            'notes': 'Test notes'
        }
        form = KitItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Quantity must be at least 1.', str(form.errors))
    
    def test_kititem_add_endpoint_rejects_decimal(self):
        """Test that the kit_item_add endpoint rejects decimal quantities."""
        url = reverse('inventory:kit_item_add', args=[self.kit.id])
        response = self.client.post(url, {
            'part_id': self.part.id,
            'vendor_id': self.vendor.id,
            'quantity': '1.5',
            'unit_cost': '10.00',
            'notes': 'Test notes'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('whole number', response.content.decode())
    
    def test_kititem_add_endpoint_accepts_integer(self):
        """Test that the kit_item_add endpoint accepts integer quantities."""
        url = reverse('inventory:kit_item_add', args=[self.kit.id])
        response = self.client.post(url, {
            'part_id': self.part.id,
            'vendor_id': self.vendor.id,
            'quantity': '3',
            'unit_cost': '10.00',
            'notes': 'Test notes'
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify the item was created with integer quantity
        kit_item = KitItem.objects.get(kit=self.kit, part=self.part, vendor=self.vendor)
        self.assertEqual(kit_item.quantity, Decimal('3'))
