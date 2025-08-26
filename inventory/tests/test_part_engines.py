from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from inventory.models import Part, Engine, EnginePart, SGEngine
from inventory.forms import PartEngineLinkForm


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
    
    def test_part_engine_form_queryset_excludes_linked_engines(self):
        """Test that PartEngineLinkForm excludes engines already linked to the part."""
        # Initially, both engines should be available
        form = PartEngineLinkForm(part=self.part)
        self.assertEqual(form.fields['engine'].queryset.count(), 2)
        
        # Link engine1 to the part
        EnginePart.objects.create(part=self.part, engine=self.engine1)
        
        # Now only engine2 should be available
        form = PartEngineLinkForm(part=self.part)
        self.assertEqual(form.fields['engine'].queryset.count(), 1)
        self.assertEqual(form.fields['engine'].queryset.first(), self.engine2)
    
    def test_part_engine_form_shows_sg_engine_choices(self):
        """Test that PartEngineLinkForm shows SG Engine information in choices."""
        form = PartEngineLinkForm(part=self.part)
        choices = form.fields['engine'].choices
        
        # Should have 3 choices: empty choice + 2 engines
        self.assertEqual(len(choices), 3)
        
        # Check that choices show SG Engine information
        choice_texts = [choice[1] for choice in choices]
        self.assertIn("Select an SG Engine…", choice_texts)
        self.assertIn("Test Make 1 Test Model 1 (TEST-001)", choice_texts)
        self.assertIn("Test Make 2 Test Model 2 (TEST-002)", choice_texts)
    
    def test_part_engines_partial_endpoint(self):
        """Test that the part_engines_partial endpoint works."""
        url = reverse('inventory:part_engines_partial', args=[self.part.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('links', response.context)
        self.assertIn('show_form', response.context)
        self.assertFalse(response.context['show_form'])  # Form should be collapsed by default
    
    def test_part_engines_partial_show_form(self):
        """Test that the part_engines_partial endpoint shows form when requested."""
        url = reverse('inventory:part_engines_partial', args=[self.part.id]) + '?show_form=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_form'])  # Form should be shown
    
    def test_part_engine_add_endpoint(self):
        """Test that the part_engine_add endpoint works."""
        url = reverse('inventory:part_engine_add', args=[self.part.id])
        response = self.client.post(url, {
            'engine': self.engine1.id,
            'notes': 'Test notes'
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was created
        link = EnginePart.objects.get(part=self.part, engine=self.engine1)
        self.assertEqual(link.notes, 'Test notes')
        
        # Verify form is collapsed after successful add
        self.assertFalse(response.context['show_form'])
    
    def test_part_engine_add_endpoint_validation_error(self):
        """Test that the part_engine_add endpoint keeps form open on validation error."""
        url = reverse('inventory:part_engine_add', args=[self.part.id])
        response = self.client.post(url, {
            # Missing required 'engine' field
            'notes': 'Test notes'
        })
        self.assertEqual(response.status_code, 400)
        
        # Verify form stays open with errors
        self.assertTrue(response.context['show_form'])
        self.assertIn('engine', response.context['form'].errors)
    
    def test_part_engine_remove_endpoint(self):
        """Test that the part_engine_remove endpoint works."""
        # Create a link first
        link = EnginePart.objects.create(part=self.part, engine=self.engine1)
        
        url = reverse('inventory:part_engine_remove', args=[self.part.id, link.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify the link was removed
        self.assertFalse(EnginePart.objects.filter(part=self.part, engine=self.engine1).exists())
    
    def test_form_validation(self):
        """Test that the form validates correctly."""
        # Valid data
        form_data = {
            'engine': self.engine1.id,
            'notes': 'Test notes'
        }
        form = PartEngineLinkForm(data=form_data, part=self.part)
        self.assertTrue(form.is_valid())
        
        # Invalid data - no engine
        form_data = {
            'notes': 'Test notes'
        }
        form = PartEngineLinkForm(data=form_data, part=self.part)
        self.assertFalse(form.is_valid())
