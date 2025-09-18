from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import transaction
from inventory.models import Vendor, VendorContact
from inventory.forms import VendorForm, VendorContactForm, VendorContactFormSet


class VendorContactModelTest(TestCase):
    """Test the VendorContact model."""
    
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name="Test Vendor",
            website="https://testvendor.com",
            address="123 Test St",
            notes="Test vendor notes"
        )
    
    def test_vendor_contact_creation(self):
        """Test creating a vendor contact."""
        contact = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="John Doe",
            email="john@testvendor.com",
            phone="555-1234",
            title="Sales Manager",
            notes="Primary contact"
        )
        
        self.assertEqual(contact.vendor, self.vendor)
        self.assertEqual(contact.full_name, "John Doe")
        self.assertEqual(contact.email, "john@testvendor.com")
        self.assertEqual(contact.phone, "555-1234")
        self.assertEqual(contact.title, "Sales Manager")
        self.assertEqual(contact.notes, "Primary contact")
    
    def test_vendor_contact_str(self):
        """Test the string representation of VendorContact."""
        contact = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Jane Smith"
        )
        
        expected = "Jane Smith (Test Vendor)"
        self.assertEqual(str(contact), expected)
    
    def test_vendor_contact_ordering(self):
        """Test that contacts are ordered by full_name, then id."""
        contact1 = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Alice Johnson"
        )
        contact2 = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Bob Smith"
        )
        contact3 = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Alice Johnson"  # Same name, different id
        )
        
        contacts = list(VendorContact.objects.all())
        self.assertEqual(contacts[0], contact1)  # Alice Johnson (first)
        self.assertEqual(contacts[1], contact3)  # Alice Johnson (second)
        self.assertEqual(contacts[2], contact2)  # Bob Smith


class VendorContactFormTest(TestCase):
    """Test the VendorContactForm."""
    
    def test_vendor_contact_form_valid(self):
        """Test valid VendorContactForm data."""
        form_data = {
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'phone': '555-1234',
            'title': 'Sales Manager',
            'notes': 'Primary contact'
        }
        
        form = VendorContactForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_vendor_contact_form_required_fields(self):
        """Test that full_name is required."""
        form_data = {
            'email': 'john@example.com',
            'phone': '555-1234'
        }
        
        form = VendorContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('full_name', form.errors)
    
    def test_vendor_contact_form_optional_fields(self):
        """Test that email, phone, title, and notes are optional."""
        form_data = {
            'full_name': 'John Doe'
        }
        
        form = VendorContactForm(data=form_data)
        self.assertTrue(form.is_valid())


class VendorContactFormSetTest(TestCase):
    """Test the VendorContactFormSet."""
    
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name="Test Vendor",
            website="https://testvendor.com"
        )
    
    def test_vendor_contact_formset_valid(self):
        """Test valid VendorContactFormSet data."""
        formset_data = {
            'contacts-TOTAL_FORMS': '2',
            'contacts-INITIAL_FORMS': '0',
            'contacts-MIN_NUM_FORMS': '0',
            'contacts-MAX_NUM_FORMS': '1000',
            'contacts-0-full_name': 'John Doe',
            'contacts-0-email': 'john@example.com',
            'contacts-0-phone': '555-1234',
            'contacts-0-title': 'Sales Manager',
            'contacts-0-notes': 'Primary contact',
            'contacts-1-full_name': 'Jane Smith',
            'contacts-1-email': 'jane@example.com',
            'contacts-1-phone': '555-5678',
            'contacts-1-title': 'Support Manager',
            'contacts-1-notes': 'Secondary contact'
        }
        
        formset = VendorContactFormSet(data=formset_data, instance=self.vendor)
        self.assertTrue(formset.is_valid())
    
    def test_vendor_contact_formset_save(self):
        """Test saving a VendorContactFormSet."""
        formset_data = {
            'contacts-TOTAL_FORMS': '1',
            'contacts-INITIAL_FORMS': '0',
            'contacts-MIN_NUM_FORMS': '0',
            'contacts-MAX_NUM_FORMS': '1000',
            'contacts-0-full_name': 'John Doe',
            'contacts-0-email': 'john@example.com',
            'contacts-0-phone': '555-1234'
        }
        
        formset = VendorContactFormSet(data=formset_data, instance=self.vendor)
        self.assertTrue(formset.is_valid())
        
        formset.save()
        
        # Check that the contact was created
        self.assertEqual(self.vendor.contacts.count(), 1)
        contact = self.vendor.contacts.first()
        self.assertEqual(contact.full_name, 'John Doe')
        self.assertEqual(contact.email, 'john@example.com')
        self.assertEqual(contact.phone, '555-1234')


class VendorContactViewsTest(TestCase):
    """Test views that handle vendor contacts."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        self.vendor = Vendor.objects.create(
            name="Test Vendor",
            website="https://testvendor.com"
        )
    
    def test_vendor_create_with_contacts(self):
        """Test creating a vendor with contacts."""
        form_data = {
            'name': 'New Vendor',
            'website': 'https://newvendor.com',
            'address': '456 New St',
            'notes': 'New vendor notes',
            'contacts-TOTAL_FORMS': '2',
            'contacts-INITIAL_FORMS': '0',
            'contacts-MIN_NUM_FORMS': '0',
            'contacts-MAX_NUM_FORMS': '1000',
            'contacts-0-full_name': 'John Doe',
            'contacts-0-email': 'john@newvendor.com',
            'contacts-0-phone': '555-1234',
            'contacts-0-title': 'Sales Manager',
            'contacts-1-full_name': 'Jane Smith',
            'contacts-1-email': 'jane@newvendor.com',
            'contacts-1-phone': '555-5678',
            'contacts-1-title': 'Support Manager'
        }
        
        response = self.client.post(reverse('inventory:vendor_create'), form_data)
        
        # Should redirect to vendor detail
        self.assertEqual(response.status_code, 302)
        
        # Check that vendor was created
        vendor = Vendor.objects.get(name='New Vendor')
        self.assertEqual(vendor.website, 'https://newvendor.com')
        
        # Check that contacts were created
        self.assertEqual(vendor.contacts.count(), 2)
        
        contact1 = vendor.contacts.get(full_name='John Doe')
        self.assertEqual(contact1.email, 'john@newvendor.com')
        self.assertEqual(contact1.phone, '555-1234')
        self.assertEqual(contact1.title, 'Sales Manager')
        
        contact2 = vendor.contacts.get(full_name='Jane Smith')
        self.assertEqual(contact2.email, 'jane@newvendor.com')
        self.assertEqual(contact2.phone, '555-5678')
        self.assertEqual(contact2.title, 'Support Manager')
    
    def test_vendor_edit_with_contacts(self):
        """Test editing a vendor with contacts."""
        # Create initial contact
        contact = VendorContact.objects.create(
            vendor=self.vendor,
            full_name='Original Contact',
            email='original@testvendor.com',
            phone='555-0000'
        )
        
        form_data = {
            'name': 'Updated Vendor',
            'website': 'https://updatedvendor.com',
            'address': '789 Updated St',
            'notes': 'Updated vendor notes',
            'contacts-TOTAL_FORMS': '2',
            'contacts-INITIAL_FORMS': '1',
            'contacts-MIN_NUM_FORMS': '0',
            'contacts-MAX_NUM_FORMS': '1000',
            'contacts-0-id': str(contact.id),
            'contacts-0-full_name': 'Updated Contact',
            'contacts-0-email': 'updated@testvendor.com',
            'contacts-0-phone': '555-1111',
            'contacts-0-title': 'Updated Title',
            'contacts-1-full_name': 'New Contact',
            'contacts-1-email': 'new@testvendor.com',
            'contacts-1-phone': '555-2222',
            'contacts-1-title': 'New Title'
        }
        
        response = self.client.post(
            reverse('inventory:vendor_edit', args=[self.vendor.id]),
            form_data
        )
        
        # Should redirect to vendor detail
        self.assertEqual(response.status_code, 302)
        
        # Check that vendor was updated
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.name, 'Updated Vendor')
        self.assertEqual(self.vendor.website, 'https://updatedvendor.com')
        
        # Check that contacts were updated
        self.assertEqual(self.vendor.contacts.count(), 2)
        
        # Check updated contact
        contact.refresh_from_db()
        self.assertEqual(contact.full_name, 'Updated Contact')
        self.assertEqual(contact.email, 'updated@testvendor.com')
        self.assertEqual(contact.phone, '555-1111')
        self.assertEqual(contact.title, 'Updated Title')
        
        # Check new contact
        new_contact = self.vendor.contacts.get(full_name='New Contact')
        self.assertEqual(new_contact.email, 'new@testvendor.com')
        self.assertEqual(new_contact.phone, '555-2222')
        self.assertEqual(new_contact.title, 'New Title')
    
    def test_vendor_edit_delete_contact(self):
        """Test deleting a contact when editing a vendor."""
        # Create initial contact
        contact = VendorContact.objects.create(
            vendor=self.vendor,
            full_name='Contact to Delete',
            email='delete@testvendor.com',
            phone='555-9999'
        )
        
        form_data = {
            'name': 'Updated Vendor',
            'website': 'https://updatedvendor.com',
            'address': '',
            'notes': '',
            'contacts-TOTAL_FORMS': '1',
            'contacts-INITIAL_FORMS': '1',
            'contacts-MIN_NUM_FORMS': '0',
            'contacts-MAX_NUM_FORMS': '1000',
            'contacts-0-id': str(contact.id),
            'contacts-0-DELETE': 'on',  # Mark for deletion
            'contacts-0-full_name': 'Contact to Delete',
            'contacts-0-email': 'delete@testvendor.com',
            'contacts-0-phone': '555-9999'
        }
        
        response = self.client.post(
            reverse('inventory:vendor_edit', args=[self.vendor.id]),
            form_data
        )
        
        # Should redirect to vendor detail
        self.assertEqual(response.status_code, 302)
        
        # Check that contact was deleted
        self.assertEqual(self.vendor.contacts.count(), 0)
    
    def test_vendor_search_by_contact(self):
        """Test searching vendors by contact information."""
        # Create vendor with contact
        vendor1 = Vendor.objects.create(name="Vendor One")
        VendorContact.objects.create(
            vendor=vendor1,
            full_name="John Doe",
            email="john@vendorone.com",
            phone="555-1111"
        )
        
        # Create vendor without matching contact
        vendor2 = Vendor.objects.create(name="Vendor Two")
        VendorContact.objects.create(
            vendor=vendor2,
            full_name="Jane Smith",
            email="jane@vendortwo.com",
            phone="555-2222"
        )
        
        # Search by contact name
        response = self.client.get(
            reverse('inventory:vendor_index'),
            {'search': 'John'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendor One')
        self.assertNotContains(response, 'Vendor Two')
        
        # Search by contact email
        response = self.client.get(
            reverse('inventory:vendor_index'),
            {'search': 'john@vendorone.com'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendor One')
        self.assertNotContains(response, 'Vendor Two')
        
        # Search by contact phone
        response = self.client.get(
            reverse('inventory:vendor_index'),
            {'search': '555-1111'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendor One')
        self.assertNotContains(response, 'Vendor Two')
    
    def test_vendor_detail_shows_contacts(self):
        """Test that vendor detail page shows contacts."""
        # Create vendor with contacts
        VendorContact.objects.create(
            vendor=self.vendor,
            full_name="John Doe",
            email="john@testvendor.com",
            phone="555-1234",
            title="Sales Manager",
            notes="Primary contact"
        )
        
        VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Jane Smith",
            email="jane@testvendor.com",
            phone="555-5678",
            title="Support Manager"
        )
        
        response = self.client.get(
            reverse('inventory:vendor_detail', args=[self.vendor.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'john@testvendor.com')
        self.assertContains(response, '555-1234')
        self.assertContains(response, 'Sales Manager')
        self.assertContains(response, 'Primary contact')
        self.assertContains(response, 'Jane Smith')
        self.assertContains(response, 'jane@testvendor.com')
        self.assertContains(response, '555-5678')
        self.assertContains(response, 'Support Manager')
    
    def test_vendor_list_shows_contacts(self):
        """Test that vendor list page shows contact information."""
        # Create vendor with contacts (ordered by full_name)
        contact1 = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Alice Johnson",  # This will be first alphabetically
            email="alice@testvendor.com",
            phone="555-1111"
        )
        
        contact2 = VendorContact.objects.create(
            vendor=self.vendor,
            full_name="Bob Smith",  # This will be second alphabetically
            email="bob@testvendor.com",
            phone="555-2222"
        )
        
        # Check that contacts were created
        self.assertEqual(self.vendor.contacts.count(), 2)
        self.assertEqual(contact1.vendor, self.vendor)
        self.assertEqual(contact2.vendor, self.vendor)
        
        response = self.client.get(reverse('inventory:vendor_index'))
        
        self.assertEqual(response.status_code, 200)
        
        # The template shows the first contact (alphabetically) and count for additional
        self.assertContains(response, 'Alice Johnson')
        self.assertContains(response, 'alice@testvendor.com')
        self.assertContains(response, '555-1111')
        self.assertContains(response, '(+1 more)')  # Should show count for additional contacts
