from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from inventory.models import Part, Machine, MachinePart


class PartMachinesTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        
        # Create test data
        self.part = Part.objects.create(
            part_number='TEST-001',
            name='Test Part'
        )
        self.machine1 = Machine.objects.create(
            make='Test Make 1',
            model='Test Model 1',
            year=2020,
            machine_type='Tractor',
            market_type='Agricultural'
        )
        self.machine2 = Machine.objects.create(
            make='Test Make 2',
            model='Test Model 2',
            year=2021,
            machine_type='Excavator',
            market_type='Construction'
        )
    
    def test_part_machines_partial_endpoint(self):
        """Test that the part_machines_partial endpoint works."""
        url = reverse('inventory:part_machines_partial', args=[self.part.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('links', response.context)
    
    def test_part_machine_add_endpoint(self):
        """Test that the part_machine_add endpoint works via modal payload."""
        url = reverse('inventory:part_machine_add', args=[self.part.id])
        response = self.client.post(url, {'machine_id': self.machine1.id})
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was created
        link = MachinePart.objects.get(part=self.part, machine=self.machine1)
        self.assertIsNotNone(link)
    
    def test_part_machine_add_requires_machine_id(self):
        """Missing machine_id should return 400."""
        url = reverse('inventory:part_machine_add', args=[self.part.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
    
    def test_part_machine_remove_endpoint(self):
        """Test that the part_machine_remove endpoint works."""
        # Create a link first
        link = MachinePart.objects.create(part=self.part, machine=self.machine1)
        
        url = reverse('inventory:part_machine_remove', args=[self.part.id, link.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was removed
        self.assertFalse(MachinePart.objects.filter(part=self.part, machine=self.machine1).exists())
    