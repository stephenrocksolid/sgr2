from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from inventory.models import (
    Part, PartCategory, PartAttribute, PartAttributeValue, 
    PartAttributeChoice, Vendor
)


class CustomFieldsTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create test data
        self.vendor = Vendor.objects.create(name='Test Vendor')
        
        # Create a category
        self.category = PartCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create attributes
        self.text_attr = PartAttribute.objects.create(
            category=self.category,
            name='Test Text Field',
            code='test_text',
            data_type='text',
            is_required=True,
            sort_order=1
        )
        
        self.choice_attr = PartAttribute.objects.create(
            category=self.category,
            name='Test Choice Field',
            code='test_choice',
            data_type='choice',
            is_required=False,
            sort_order=2
        )
        
        # Create choices for the choice attribute
        self.choice1 = PartAttributeChoice.objects.create(
            attribute=self.choice_attr,
            value='option1',
            label='Option 1',
            sort_order=1
        )
        self.choice2 = PartAttributeChoice.objects.create(
            attribute=self.choice_attr,
            value='option2',
            label='Option 2',
            sort_order=2
        )
        
        # Create a part
        self.part = Part.objects.create(
            part_number='TEST001',
            name='Test Part',
            category=self.category,
            manufacturer='Test Manufacturer'
        )

    def test_part_detail_with_custom_fields(self):
        """Test that part detail page loads with custom fields."""
        url = reverse('inventory:part_detail', args=[self.part.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Category')
        self.assertContains(response, 'Test Text Field')
        self.assertContains(response, 'Test Choice Field')

    def test_part_specs_form_rendering(self):
        """Test that the specs form renders correctly."""
        url = reverse('inventory:part_specs_form', args=[self.part.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Text Field')
        self.assertContains(response, 'Test Choice Field')
        self.assertContains(response, 'Option 1')
        self.assertContains(response, 'Option 2')

    def test_saving_attribute_values(self):
        """Test saving attribute values for a part."""
        url = reverse('inventory:part_specs_save', args=[self.part.id])
        data = {
            f'attr_{self.text_attr.id}': 'Test Value',
            f'attr_{self.choice_attr.id}': 'option1'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        
        # Check that the values were saved
        text_value = PartAttributeValue.objects.get(
            part=self.part,
            attribute=self.text_attr
        )
        self.assertEqual(text_value.value_text, 'Test Value')
        
        choice_value = PartAttributeValue.objects.get(
            part=self.part,
            attribute=self.choice_attr
        )
        self.assertEqual(choice_value.choice, self.choice1)

    def test_filter_value_control(self):
        """Test the filter value control endpoint."""
        url = reverse('inventory:filter_value_control')
        response = self.client.get(url, {'attribute_id': self.text_attr.id})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contains')
        self.assertContains(response, 'Equals')

    def test_parts_list_with_custom_filters(self):
        """Test that parts list page loads with custom filter options."""
        url = reverse('inventory:parts_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom Field Filters')
        self.assertContains(response, 'Add Filter')

    def test_category_change_updates_specs_form(self):
        """Test that changing category updates the specs form."""
        # Create another category
        other_category = PartCategory.objects.create(
            name='Other Category',
            slug='other-category'
        )
        
        url = reverse('inventory:part_specs_form', args=[self.part.id])
        response = self.client.get(url, {'category_id': other_category.id})
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the part's category was updated
        self.part.refresh_from_db()
        self.assertEqual(self.part.category, other_category)
