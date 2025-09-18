"""
Tests for the Machines and Parts search functionality.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from inventory.models import Machine, Part, PartCategory, Vendor


class MachinesSearchTestCase(TestCase):
    """Test cases for the Machines search functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test machines
        self.machine1 = Machine.objects.create(
            make='Case',
            model='Skid Steer',
            year=2015,
            machine_type='Crawler',
            market_type='US'
        )
        
        self.machine2 = Machine.objects.create(
            make='Caterpillar',
            model='Excavator',
            year=2020,
            machine_type='Track',
            market_type='EU'
        )
        
        self.machine3 = Machine.objects.create(
            make='John Deere',
            model='Tractor',
            year=2018,
            machine_type='Wheel',
            market_type='US'
        )
        
        # Create client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_machines_list_view_loads(self):
        """Test that the machines list view loads correctly."""
        response = self.client.get(reverse('inventory:machines_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Machines')
        self.assertContains(response, 'Search machines')
    
    def test_generic_search(self):
        """Test generic search terms (no fielded queries)."""
        # Search for "Case" - should find machine1
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'Case'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_fielded_search_make(self):
        """Test fielded search for make."""
        # Search for make:Case
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'make:Case'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_fielded_search_model(self):
        """Test fielded search for model."""
        # Search for model:"Skid Steer"
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'model:"Skid Steer"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Skid Steer')
        self.assertNotContains(response, 'Excavator')
        self.assertNotContains(response, 'Tractor')
    
    def test_fielded_search_year(self):
        """Test fielded search for year."""
        # Search for year:2015
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'year:2015'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2015')
        self.assertNotContains(response, '2020')
        self.assertNotContains(response, '2018')
    
    def test_fielded_search_type(self):
        """Test fielded search for machine type."""
        # Search for type:Crawler
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'type:Crawler'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crawler')
        self.assertNotContains(response, 'Track')
        self.assertNotContains(response, 'Wheel')
    
    def test_fielded_search_market(self):
        """Test fielded search for market type."""
        # Search for market:US
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'market:US'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'US')
        self.assertNotContains(response, 'EU')
    
    def test_multiple_fielded_search(self):
        """Test multiple fielded search terms (AND logic)."""
        # Search for make:Case AND market:US
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'make:Case market:US'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case')
        self.assertContains(response, 'US')
        # Should not contain Caterpillar (different make) or John Deere (different make)
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_mixed_search_terms(self):
        """Test mixed fielded and generic search terms."""
        # Search for make:Case AND generic term "2015"
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'make:Case 2015'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case')
        self.assertContains(response, '2015')
        # Should find machine1 (Case 2015)
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        # Search for "case" (lowercase)
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'make:case'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case')
    
    def test_empty_search(self):
        """Test that empty search returns all machines."""
        response = self.client.get(reverse('inventory:machines_list'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case')
        self.assertContains(response, 'Caterpillar')
        self.assertContains(response, 'John Deere')
    
    def test_no_results_search(self):
        """Test search that returns no results."""
        response = self.client.get(reverse('inventory:machines_list'), {'q': 'make:NonExistent'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No machines found matching your criteria')
        self.assertNotContains(response, 'Case')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')


class PartsSearchTestCase(TestCase):
    """Test cases for the Parts search functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test category and vendor
        self.category = PartCategory.objects.create(name='Filters', slug='filters')
        self.vendor = Vendor.objects.create(name='SG Supply')
        
        # Create test parts
        self.part1 = Part.objects.create(
            part_number='AB1071',
            name='Valve Kit',
            category=self.category,
            manufacturer='Cummins',
            unit='EA',
            type='Hydraulic',
            primary_vendor=self.vendor
        )
        
        self.part2 = Part.objects.create(
            part_number='CD2055',
            name='Filter Element',
            category=self.category,
            manufacturer='Caterpillar',
            unit='EA',
            type='Air Filter',
            primary_vendor=self.vendor
        )
        
        self.part3 = Part.objects.create(
            part_number='EF3099',
            name='Gasket Set',
            category=None,
            manufacturer='John Deere',
            unit='SET',
            type='Seal',
            primary_vendor=None
        )
        
        # Create client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_parts_list_view_loads(self):
        """Test that the parts list view loads correctly."""
        response = self.client.get(reverse('inventory:parts_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Parts')
        self.assertContains(response, 'Search parts')
    
    def test_generic_search(self):
        """Test generic search terms (no fielded queries)."""
        # Search for "Cummins" - should find part1
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'Cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_fielded_search_number(self):
        """Test fielded search for part number."""
        # Search for number:AB1071
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'number:AB1071'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AB1071')
        self.assertNotContains(response, 'CD2055')
        self.assertNotContains(response, 'EF3099')
    
    def test_fielded_search_name(self):
        """Test fielded search for part name."""
        # Search for name:"Valve Kit"
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'name:"Valve Kit"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Valve Kit')
        self.assertNotContains(response, 'Filter Element')
        self.assertNotContains(response, 'Gasket Set')
    
    def test_fielded_search_manufacturer(self):
        """Test fielded search for manufacturer."""
        # Search for mfr:Cummins
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'mfr:Cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_fielded_search_category(self):
        """Test fielded search for category."""
        # Search for category:Filters
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'category:Filters'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filters')
        # Should find parts with this category
        self.assertContains(response, 'AB1071')
        self.assertContains(response, 'CD2055')
        self.assertNotContains(response, 'EF3099')  # No category
    
    def test_fielded_search_vendor(self):
        """Test fielded search for vendor."""
        # Search for vendor:"SG Supply"
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'vendor:"SG Supply"'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SG Supply')
        # Should find parts with this vendor
        self.assertContains(response, 'AB1071')
        self.assertContains(response, 'CD2055')
        self.assertNotContains(response, 'EF3099')  # No vendor
    
    def test_multiple_fielded_search(self):
        """Test multiple fielded search terms (AND logic)."""
        # Search for mfr:Cummins AND category:Filters
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'mfr:Cummins category:Filters'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertContains(response, 'Filters')
        # Should find part1 (Cummins with Filters category)
        self.assertContains(response, 'AB1071')
        self.assertNotContains(response, 'CD2055')  # Different manufacturer
        self.assertNotContains(response, 'EF3099')  # No category
    
    def test_mixed_search_terms(self):
        """Test mixed fielded and generic search terms."""
        # Search for mfr:Cummins AND generic term "valve"
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'mfr:Cummins valve'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
        self.assertContains(response, 'valve')
        # Should find part1 (Cummins Valve Kit)
        self.assertNotContains(response, 'Caterpillar')
        self.assertNotContains(response, 'John Deere')
    
    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        # Search for "cummins" (lowercase)
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'mfr:cummins'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
    
    def test_empty_search(self):
        """Test that empty search returns all parts."""
        response = self.client.get(reverse('inventory:parts_list'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AB1071')
        self.assertContains(response, 'CD2055')
        self.assertContains(response, 'EF3099')
    
    def test_no_results_search(self):
        """Test search that returns no results."""
        response = self.client.get(reverse('inventory:parts_list'), {'q': 'mfr:NonExistent'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No parts found matching your criteria')
        # Check that the table body doesn't contain the part numbers (they might appear in JS)
        self.assertNotContains(response, '<td>AB1071</td>')
        self.assertNotContains(response, '<td>CD2055</td>')
        self.assertNotContains(response, '<td>EF3099</td>')
    
    def test_csv_export_with_search(self):
        """Test CSV export with search filters."""
        response = self.client.get(reverse('inventory:parts_list'), {
            'q': 'mfr:Cummins',
            'export': 'csv'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('Cummins', response.content.decode())
        self.assertNotIn('Caterpillar', response.content.decode())
