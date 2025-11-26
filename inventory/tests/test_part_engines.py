from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from inventory.models import Part, Engine, EnginePart, SGEngine


class PartEnginesTest(TestCase):
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
        self.sg_engine1 = SGEngine.objects.create(
            sg_make='Test Make 1',
            sg_model='Test Model 1',
            identifier='TEST-001'
        )
        self.sg_engine2 = SGEngine.objects.create(
            sg_make='Test Make 2',
            sg_model='Test Model 2',
            identifier='TEST-002'
        )
        self.engine1 = Engine.objects.create(
            engine_make='Test Make 1',
            engine_model='Test Model 1',
            sg_engine=self.sg_engine1
        )
        self.engine2 = Engine.objects.create(
            engine_make='Test Make 2',
            engine_model='Test Model 2',
            sg_engine=self.sg_engine2
        )
    
    def test_part_engines_partial_endpoint(self):
        """Test that the part_engines_partial endpoint works."""
        url = reverse('inventory:part_engines_partial', args=[self.part.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('links', response.context)
    
    def test_part_engine_add_endpoint(self):
        """Test that the part_engine_add endpoint works via modal payload."""
        url = reverse('inventory:part_engine_add', args=[self.part.id])
        response = self.client.post(url, {'engine_id': self.engine1.id})
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was created
        link = EnginePart.objects.get(part=self.part, engine=self.engine1)
        self.assertIsNotNone(link)
    
    def test_part_engine_add_requires_engine_id(self):
        """Missing engine_id should return 400."""
        url = reverse('inventory:part_engine_add', args=[self.part.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
    
    def test_part_engine_remove_endpoint(self):
        """Test that the part_engine_remove endpoint works."""
        # Create a link first
        link = EnginePart.objects.create(part=self.part, engine=self.engine1)
        
        url = reverse('inventory:part_engine_remove', args=[self.part.id, link.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was removed
        self.assertFalse(EnginePart.objects.filter(part=self.part, engine=self.engine1).exists())
    