"""
Tests for the new engine search functionality.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from inventory.models import Engine, SGEngine


class EngineSearchTestCase(TestCase):
    """Test cases for the advanced engine search functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test SG engines
        self.sg_engine1 = SGEngine.objects.create(
            sg_make='Cummins',
            sg_model='3 Cylinder',
            identifier='SG001',
            notes='Test SG engine 1'
        )
        
        self.sg_engine2 = SGEngine.objects.create(
            sg_make='Caterpillar',
            sg_model='4 Cylinder',
            identifier='SG002',
            notes='Test SG engine 2'
        )
        
        # Create test engines
        self.engine1 = Engine.objects.create(
            engine_make='Cummins',
            engine_model='3 Cylinder',
            sg_engine=self.sg_engine1,
            sg_engine_identifier='ENG001',
            cpl_number='CPL123',
            status='Available',
            serial_number='SN001',
            sg_engine_notes='Test engine 1'
        )
        
        self.engine2 = Engine.objects.create(
            engine_make='Caterpillar',
            engine_model='4 Cylinder',
            sg_engine=self.sg_engine2,
            sg_engine_identifier='ENG002',
            cpl_number='CPL456',
            status='Sold',
            serial_number='SN002',
            sg_engine_notes='Test engine 2'
        )
        
        self.engine3 = Engine.objects.create(
            engine_make='John Deere',
            engine_model='6 Cylinder',
            sg_engine=None,
            sg_engine_identifier='ENG003',
            cpl_number='CPL789',
            status='Available',
            serial_number='SN003',
            sg_engine_notes='Test engine 3'
        )
        
        # Create client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_engines_list_view_loads(self):
        """Test that the engines list view loads correctly."""
        response = self.client.get(reverse('inventory:engines_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Engines')
        self.assertContains(response, 'Search:')
    
    def test_generic_search(self):
        """Test generic search terms (no fielded queries)."""
        # Search for "Cummins" - should find engine1
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'Cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_fielded_search_make(self):
        """Test fielded search for make."""
        # Search for make:Cummins
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'make:Cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_fielded_search_model(self):
        """Test fielded search for model."""
        # Search for model:"3 Cylinder"
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'model:"3 Cylinder"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3 Cylinder')
        self.assertNotContains(response, '4 Cylinder')
        self.assertNotContains(response, '6 Cylinder')
    
    def test_fielded_search_cpl(self):
        """Test fielded search for CPL number."""
        # Search for cpl:CPL123
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'cpl:CPL123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CPL123')
        self.assertNotContains(response, 'CPL456')
        self.assertNotContains(response, 'CPL789')
    
    def test_fielded_search_status(self):
        """Test fielded search for status."""
        # Search for status:Available
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'status:Available'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Available')
        self.assertNotContains(response, 'Sold')
    
    def test_fielded_search_serial_number(self):
        """Test fielded search for serial number."""
        # Search for sn:SN001
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'sn:SN001'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SN001')
        self.assertNotContains(response, 'SN002')
        self.assertNotContains(response, 'SN003')
    
    def test_fielded_search_sg_make(self):
        """Test fielded search for SG make."""
        # Search for sg_make:Cummins
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'sg_make:Cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertNotContains(response, 'Caterpillar')
    
    def test_fielded_search_sg_model(self):
        """Test fielded search for SG model."""
        # Search for sg_model:"3 Cylinder"
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'sg_model:"3 Cylinder"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3 Cylinder')
        self.assertNotContains(response, '4 Cylinder')
    
    def test_fielded_search_identifier(self):
        """Test fielded search for identifier."""
        # Search for id:ENG001
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'id:ENG001'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ENG001')
        self.assertNotContains(response, 'ENG002')
        self.assertNotContains(response, 'ENG003')
    
    def test_fielded_search_notes(self):
        """Test fielded search for notes."""
        # Search for notes:"Test engine 1"
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'notes:"Test engine 1"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test engine 1')
        self.assertNotContains(response, 'Test engine 2')
        self.assertNotContains(response, 'Test engine 3')
    
    def test_multiple_fielded_search(self):
        """Test multiple fielded search terms (AND logic)."""
        # Search for make:Cummins AND status:Available
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'make:Cummins status:Available'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertContains(response, 'Available')
        # Should not contain Caterpillar (different make) or John Deere (different make)
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_mixed_search_terms(self):
        """Test mixed fielded and generic search terms."""
        # Search for make:Cummins AND generic term "3"
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'make:Cummins 3'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertContains(response, '3')
        # Should find engine1 (Cummins 3 Cylinder)
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        # Search for "cummins" (lowercase)
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'make:cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
    
    def test_empty_search(self):
        """Test that empty search returns all engines."""
        response = self.client.get(reverse('inventory:engines_list'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertContains(response, 'Caterpillar')
        self.assertContains(response, 'John Deere')
    
    def test_no_results_search(self):
        """Test search that returns no results."""
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'make:NonExistent'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No engines found matching your criteria')
        self.assertNotContains(response, 'Cummins')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_quoted_values(self):
        """Test search with quoted values containing spaces."""
        # Search for model:"3 Cylinder" with quotes
        response = self.client.get(reverse('inventory:engines_list'), {'q': 'model:"3 Cylinder"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3 Cylinder')
        self.assertNotContains(response, '4 Cylinder')
    
    def test_csv_export_with_search(self):
        """Test CSV export with search filters."""
        response = self.client.get(reverse('inventory:engines_list'), {
            'q': 'make:Cummins',
            'export': 'csv'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('Cummins', response.content.decode())
        self.assertNotIn('Caterpillar', response.content.decode())















