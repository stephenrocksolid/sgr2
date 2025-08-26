from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from inventory.models import Part, Machine, MachinePart
from inventory.forms import PartMachineLinkForm


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
    
    def test_part_machine_form_queryset_excludes_linked_machines(self):
        """Test that PartMachineLinkForm excludes machines already linked to the part."""
        # Initially, both machines should be available
        form = PartMachineLinkForm(part=self.part)
        self.assertEqual(form.fields['machine'].queryset.count(), 2)
        
        # Link machine1 to the part
        MachinePart.objects.create(part=self.part, machine=self.machine1)
        
        # Now only machine2 should be available
        form = PartMachineLinkForm(part=self.part)
        self.assertEqual(form.fields['machine'].queryset.count(), 1)
        self.assertEqual(form.fields['machine'].queryset.first(), self.machine2)
    
    def test_part_machines_partial_endpoint(self):
        """Test that the part_machines_partial endpoint works."""
        url = reverse('inventory:part_machines_partial', args=[self.part.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('links', response.context)
        self.assertIn('show_form', response.context)
        self.assertFalse(response.context['show_form'])  # Form should be collapsed by default
    
    def test_part_machines_partial_show_form(self):
        """Test that the part_machines_partial endpoint shows form when requested."""
        url = reverse('inventory:part_machines_partial', args=[self.part.id]) + '?show_form=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_form'])  # Form should be shown
    
    def test_part_machine_add_endpoint(self):
        """Test that the part_machine_add endpoint works."""
        url = reverse('inventory:part_machine_add', args=[self.part.id])
        response = self.client.post(url, {
            'machine': self.machine1.id,
            'is_primary': True,
            'notes': 'Test notes'
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was created
        link = MachinePart.objects.get(part=self.part, machine=self.machine1)
        self.assertEqual(link.notes, 'Test notes')
        self.assertTrue(link.is_primary)
        
        # Verify form is collapsed after successful add
        self.assertFalse(response.context['show_form'])
    
    def test_part_machine_add_endpoint_validation_error(self):
        """Test that the part_machine_add endpoint keeps form open on validation error."""
        url = reverse('inventory:part_machine_add', args=[self.part.id])
        response = self.client.post(url, {
            # Missing required 'machine' field
            'notes': 'Test notes'
        })
        self.assertEqual(response.status_code, 400)
        
        # Verify form stays open with errors
        self.assertTrue(response.context['show_form'])
        self.assertIn('machine', response.context['form'].errors)
    
    def test_part_machine_remove_endpoint(self):
        """Test that the part_machine_remove endpoint works."""
        # Create a link first
        link = MachinePart.objects.create(part=self.part, machine=self.machine1)
        
        url = reverse('inventory:part_machine_remove', args=[self.part.id, link.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was removed
        self.assertFalse(MachinePart.objects.filter(part=self.part, machine=self.machine1).exists())
    
    def test_form_validation(self):
        """Test that the form validates correctly."""
        # Valid data
        form_data = {
            'machine': self.machine1.id,
            'is_primary': True,
            'notes': 'Test notes'
        }
        form = PartMachineLinkForm(data=form_data, part=self.part)
        self.assertTrue(form.is_valid())
        
        # Invalid data - no machine
        form_data = {
            'notes': 'Test notes'
        }
        form = PartMachineLinkForm(data=form_data, part=self.part)
        self.assertFalse(form.is_valid())
