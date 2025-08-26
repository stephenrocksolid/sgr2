from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from inventory.models import Engine, BuildList, Kit, KitItem, Part, Vendor, PartVendor


class BuildListsTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        
        # Create test engine
        self.engine = Engine.objects.create(
            engine_make='Test Make',
            engine_model='Test Model'
        )
        
        # Create test parts and vendors
        self.part1 = Part.objects.create(
            part_number='TEST001',
            name='Test Part 1'
        )
        self.part2 = Part.objects.create(
            part_number='TEST002',
            name='Test Part 2'
        )
        
        self.vendor1 = Vendor.objects.create(name='Test Vendor 1')
        self.vendor2 = Vendor.objects.create(name='Test Vendor 2')
        
        # Create PartVendor relationships
        self.part_vendor1 = PartVendor.objects.create(
            part=self.part1,
            vendor=self.vendor1,
            cost=Decimal('10.00')
        )
        self.part_vendor2 = PartVendor.objects.create(
            part=self.part2,
            vendor=self.vendor2,
            cost=Decimal('20.00')
        )
    
    def test_create_build_list(self):
        """Test creating a build list."""
        response = self.client.post(
            reverse('inventory:build_list_create', args=[self.engine.id]),
            {
                'name': 'Test Build List',
                'notes': 'Test notes'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(BuildList.objects.filter(name='Test Build List').exists())
    
    def test_create_kit(self):
        """Test creating a kit."""
        build_list = BuildList.objects.create(
            engine=self.engine,
            name='Test Build List'
        )
        
        response = self.client.post(
            reverse('inventory:kit_create', args=[build_list.id]),
            {
                'name': 'Test Kit',
                'notes': 'Test kit notes',
                'margin_pct': '25.00'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        kit = Kit.objects.filter(name='Test Kit').first()
        self.assertIsNotNone(kit)
        self.assertEqual(kit.margin_pct, Decimal('25.00'))
    
    def test_add_kit_item(self):
        """Test adding an item to a kit."""
        build_list = BuildList.objects.create(
            engine=self.engine,
            name='Test Build List'
        )
        kit = Kit.objects.create(
            build_list=build_list,
            name='Test Kit',
            margin_pct=Decimal('25.00')
        )
        
        response = self.client.post(
            reverse('inventory:kit_item_add', args=[kit.id]),
            {
                'part_id': self.part1.id,
                'vendor_id': self.vendor1.id,
                'quantity': '2.00',
                'unit_cost': '10.00',
                'notes': 'Test item notes'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        item = KitItem.objects.filter(kit=kit, part=self.part1, vendor=self.vendor1).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal('2.00'))
        self.assertEqual(item.unit_cost, Decimal('10.00'))
    
    def test_kit_totals_calculation(self):
        """Test that kit totals are calculated correctly."""
        build_list = BuildList.objects.create(
            engine=self.engine,
            name='Test Build List'
        )
        kit = Kit.objects.create(
            build_list=build_list,
            name='Test Kit',
            margin_pct=Decimal('25.00')
        )
        
        # Add items
        KitItem.objects.create(
            kit=kit,
            part=self.part1,
            vendor=self.vendor1,
            quantity=Decimal('2.00'),
            unit_cost=Decimal('10.00')
        )
        KitItem.objects.create(
            kit=kit,
            part=self.part2,
            vendor=self.vendor2,
            quantity=Decimal('1.00'),
            unit_cost=Decimal('20.00')
        )
        
        # Recalculate totals
        kit.recalc_totals()
        
        # Cost total should be (2 * 10) + (1 * 20) = 40
        self.assertEqual(kit.cost_total, Decimal('40.00'))
        # Sale price should be 40 * 1.25 = 50
        self.assertEqual(kit.sale_price, Decimal('50.00'))
    
    def test_duplicate_kit(self):
        """Test duplicating a kit."""
        build_list = BuildList.objects.create(
            engine=self.engine,
            name='Test Build List'
        )
        kit = Kit.objects.create(
            build_list=build_list,
            name='Test Kit',
            margin_pct=Decimal('25.00')
        )
        
        # Add an item
        KitItem.objects.create(
            kit=kit,
            part=self.part1,
            vendor=self.vendor1,
            quantity=Decimal('1.00'),
            unit_cost=Decimal('10.00')
        )
        
        response = self.client.post(
            reverse('inventory:kit_duplicate', args=[kit.id])
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that a new kit was created
        new_kit = Kit.objects.filter(name='Test Kit (Copy)').first()
        self.assertIsNotNone(new_kit)
        self.assertEqual(new_kit.margin_pct, Decimal('25.00'))
        
        # Check that the item was copied
        new_item = KitItem.objects.filter(kit=new_kit).first()
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item.part, self.part1)
        self.assertEqual(new_item.vendor, self.vendor1)
