"""
Tests for SG Vendors functionality.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from inventory.models import SGVendor, Vendor, Engine, Part


class SGVendorTestCase(TestCase):
    """Test cases for SG Vendor functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create test SG Vendor
        self.sg_vendor = SGVendor.objects.create(
            name='Test SG Vendor',
            website='https://testsgvendor.com',
            notes='Test SG Vendor notes'
        )
        
        # Create test vendor
        self.vendor = Vendor.objects.create(
            name='Test Vendor',
            website='https://testvendor.com',
            contact_name='John Doe',
            email='john@testvendor.com'
        )
    
    def test_sg_vendor_creation(self):
        """Test SG Vendor creation."""
        sg_vendor = SGVendor.objects.create(
            name='New SG Vendor',
            website='https://newsgvendor.com'
        )
        
        self.assertEqual(sg_vendor.name, 'New SG Vendor')
        self.assertEqual(sg_vendor.website, 'https://newsgvendor.com')
        self.assertIsNotNone(sg_vendor.created)
        self.assertIsNotNone(sg_vendor.updated)
    
    def test_sg_vendor_case_insensitive_uniqueness(self):
        """Test that SG Vendor names are case-insensitive unique."""
        # Create first SG Vendor
        SGVendor.objects.create(name='Cummins')
        
        # Try to create another with different case
        with self.assertRaises(Exception):  # Should raise IntegrityError
            SGVendor.objects.create(name='CUMMINS')
    
    def test_vendor_sg_vendor_linking(self):
        """Test linking a vendor to an SG Vendor."""
        # Initially vendor should have no SG Vendor
        self.assertIsNone(self.vendor.sg_vendor)
        
        # Link vendor to SG Vendor
        self.vendor.sg_vendor = self.sg_vendor
        self.vendor.save()
        
        # Check the link
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.sg_vendor, self.sg_vendor)
        self.assertIn(self.vendor, self.sg_vendor.vendors.all())
    
    def test_sg_vendor_index_view(self):
        """Test SG Vendor index view."""
        response = self.client.get(reverse('sgvendors:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test SG Vendor')
        self.assertContains(response, 'https://testsgvendor.com')
    
    def test_sg_vendor_create_view(self):
        """Test SG Vendor create view."""
        response = self.client.get(reverse('sgvendors:create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create SG Vendor')
    
    def test_sg_vendor_create_post(self):
        """Test creating SG Vendor via POST."""
        data = {
            'name': 'New SG Vendor',
            'website': 'https://newsgvendor.com',
            'notes': 'New SG Vendor notes'
        }
        
        response = self.client.post(reverse('sgvendors:create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Check that SG Vendor was created
        sg_vendor = SGVendor.objects.get(name='New SG Vendor')
        self.assertEqual(sg_vendor.website, 'https://newsgvendor.com')
        self.assertEqual(sg_vendor.notes, 'New SG Vendor notes')
    
    def test_sg_vendor_edit_view(self):
        """Test SG Vendor edit view."""
        response = self.client.get(reverse('sgvendors:edit', args=[self.sg_vendor.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test SG Vendor')
    
    def test_sg_vendor_edit_post(self):
        """Test editing SG Vendor via POST."""
        data = {
            'name': 'Updated SG Vendor',
            'website': 'https://updatedsgvendor.com',
            'notes': 'Updated notes'
        }
        
        response = self.client.post(reverse('sgvendors:edit', args=[self.sg_vendor.id]), data)
        self.assertEqual(response.status_code, 302)  # Redirect after update
        
        # Check that SG Vendor was updated
        self.sg_vendor.refresh_from_db()
        self.assertEqual(self.sg_vendor.name, 'Updated SG Vendor')
        self.assertEqual(self.sg_vendor.website, 'https://updatedsgvendor.com')
        self.assertEqual(self.sg_vendor.notes, 'Updated notes')
    
    def test_sg_vendor_detail_view(self):
        """Test SG Vendor detail view."""
        # Link vendor to SG Vendor for testing
        self.vendor.sg_vendor = self.sg_vendor
        self.vendor.save()
        
        response = self.client.get(reverse('sgvendors:detail', args=[self.sg_vendor.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test SG Vendor')
        self.assertContains(response, 'Test Vendor')  # Linked vendor should appear
    
    def test_sg_vendor_search_ajax(self):
        """Test SG Vendor search AJAX endpoint."""
        response = self.client.get(reverse('sgvendors:search'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test SG Vendor')
    
    def test_sg_vendor_create_ajax(self):
        """Test SG Vendor creation via AJAX."""
        data = {
            'name': 'AJAX SG Vendor',
            'website': 'https://ajaxsgvendor.com',
            'notes': 'Created via AJAX'
        }
        
        response = self.client.post(reverse('sgvendors:create_ajax'), data)
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertTrue(result['success'])
        self.assertEqual(result['name'], 'AJAX SG Vendor')
        
        # Check that SG Vendor was created
        sg_vendor = SGVendor.objects.get(name='AJAX SG Vendor')
        self.assertEqual(sg_vendor.website, 'https://ajaxsgvendor.com')


class VendorMatchingTestCase(TestCase):
    """Test cases for vendor matching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create test SG Vendor
        self.sg_vendor = SGVendor.objects.create(
            name='Cummins',
            website='https://cummins.com'
        )
        
        # Create unmatched vendor
        self.vendor = Vendor.objects.create(
            name='Cummins Inc',
            website='https://cumminsinc.com'
        )
    
    def test_unmatched_vendors_view(self):
        """Test unmatched vendors view."""
        response = self.client.get(reverse('imports:unmatched_vendors'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins Inc')
        self.assertContains(response, 'Unmatched Vendors')
    
    def test_match_vendor_view(self):
        """Test matching vendor to SG Vendor."""
        data = {
            'vendor_id': self.vendor.id,
            'sg_vendor_id': self.sg_vendor.id
        }
        
        response = self.client.post(reverse('imports:match_vendor'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after matching
        
        # Check that vendor was linked
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.sg_vendor, self.sg_vendor)
    
    def test_match_vendor_invalid_data(self):
        """Test matching vendor with invalid data."""
        data = {
            'vendor_id': 999,  # Non-existent vendor
            'sg_vendor_id': self.sg_vendor.id
        }
        
        response = self.client.post(reverse('imports:match_vendor'), data)
        self.assertEqual(response.status_code, 302)  # Redirect with error message
    
    def test_vendor_no_longer_unmatched_after_matching(self):
        """Test that vendor disappears from unmatched list after matching."""
        # Initially should appear in unmatched
        response = self.client.get(reverse('imports:unmatched_vendors'))
        self.assertContains(response, 'Cummins Inc')
        
        # Verify vendor is initially unmatched
        self.assertIsNone(self.vendor.sg_vendor)
        
        # Match the vendor
        data = {
            'vendor_id': self.vendor.id,
            'sg_vendor_id': self.sg_vendor.id
        }
        response = self.client.post(reverse('imports:match_vendor'), data)
        self.assertEqual(response.status_code, 302)  # Should redirect
        
        # Refresh vendor from database to ensure the link was saved
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.sg_vendor, self.sg_vendor)
        
        # Verify vendor is no longer in unmatched query
        from inventory.models import Vendor
        unmatched_vendors = Vendor.objects.filter(sg_vendor__isnull=True)
        self.assertNotIn(self.vendor, unmatched_vendors)
        
        # Should no longer appear in unmatched page
        response = self.client.get(reverse('imports:unmatched_vendors'))
        self.assertNotContains(response, 'Cummins Inc')


class ImportVendorLinkingTestCase(TestCase):
    """Test cases for vendor linking during import."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_ci_get_or_create_vendor(self):
        """Test case-insensitive vendor creation/getting."""
        from imports.tasks import ci_get_or_create_vendor
        
        # Create vendor with lowercase
        vendor1 = ci_get_or_create_vendor('cummins')
        self.assertEqual(vendor1.name, 'cummins')
        
        # Get same vendor with uppercase
        vendor2 = ci_get_or_create_vendor('CUMMINS')
        self.assertEqual(vendor1.id, vendor2.id)
        
        # Get same vendor with mixed case
        vendor3 = ci_get_or_create_vendor('Cummins')
        self.assertEqual(vendor1.id, vendor3.id)
    
    def test_engine_vendor_linking_during_import(self):
        """Test that engines get linked to vendors during import processing."""
        from imports.tasks import ci_get_or_create_vendor
        
        # Create vendor
        vendor = ci_get_or_create_vendor('Cummins')
        
        # Create engine
        engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='6BTA'
        )
        
        # Simulate import processing - attach vendor
        engine.vendor = vendor
        engine.save()
        
        # Check the link
        engine.refresh_from_db()
        self.assertEqual(engine.vendor, vendor)
        self.assertIn(engine, vendor.engines.all())
    
    def test_part_vendor_linking_during_import(self):
        """Test that parts get linked to vendors during import processing."""
        from imports.tasks import ci_get_or_create_vendor
        
        # Create vendor
        vendor = ci_get_or_create_vendor('Cummins')
        
        # Create part
        part = Part.objects.create(
            part_number='12345',
            name='Test Part',
            manufacturer='Cummins'
        )
        
        # Simulate import processing - attach vendor
        part.vendor = vendor
        part.save()
        
        # Check the link
        part.refresh_from_db()
        self.assertEqual(part.vendor, vendor)
        self.assertIn(part, vendor.parts.all())
