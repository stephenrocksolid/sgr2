from django.core.management.base import BaseCommand
from inventory.models import PartCategory, PartAttribute, PartAttributeChoice


class Command(BaseCommand):
    help = 'Create sample PartCategory and PartAttribute data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample custom field data...')
        
        # Create Filter category
        filter_category, created = PartCategory.objects.get_or_create(
            name='Filters',
            defaults={'slug': 'filters'}
        )
        if created:
            self.stdout.write(f'Created category: {filter_category.name}')
        
        # Create Filter attributes
        thread_size_attr, created = PartAttribute.objects.get_or_create(
            category=filter_category,
            code='thread_size',
            defaults={
                'name': 'Thread Size',
                'data_type': 'choice',
                'unit': '',
                'is_required': True,
                'sort_order': 1,
                'help_text': 'The thread size specification for the filter'
            }
        )
        if created:
            self.stdout.write(f'Created attribute: {thread_size_attr.name}')
            
            # Create choices for thread size
            choices = [
                ('M12x1.25', 'M12x1.25'),
                ('M14x1.5', 'M14x1.5'),
                ('M16x1.5', 'M16x1.5'),
                ('M18x1.5', 'M18x1.5'),
                ('M20x1.5', 'M20x1.5'),
                ('M22x1.5', 'M22x1.5'),
                ('M24x1.5', 'M24x1.5'),
            ]
            
            for value, label in choices:
                choice, created = PartAttributeChoice.objects.get_or_create(
                    attribute=thread_size_attr,
                    value=value,
                    defaults={'label': label, 'sort_order': len(choices)}
                )
                if created:
                    self.stdout.write(f'  Created choice: {choice.label}')
        
        # Create another attribute for filters
        filter_type_attr, created = PartAttribute.objects.get_or_create(
            category=filter_category,
            code='filter_type',
            defaults={
                'name': 'Filter Type',
                'data_type': 'choice',
                'unit': '',
                'is_required': True,
                'sort_order': 2,
                'help_text': 'The type of filter'
            }
        )
        if created:
            self.stdout.write(f'Created attribute: {filter_type_attr.name}')
            
            # Create choices for filter type
            choices = [
                ('oil', 'Oil Filter'),
                ('air', 'Air Filter'),
                ('fuel', 'Fuel Filter'),
                ('hydraulic', 'Hydraulic Filter'),
            ]
            
            for value, label in choices:
                choice, created = PartAttributeChoice.objects.get_or_create(
                    attribute=filter_type_attr,
                    value=value,
                    defaults={'label': label, 'sort_order': len(choices)}
                )
                if created:
                    self.stdout.write(f'  Created choice: {choice.label}')
        
        # Create Engine Components category
        engine_category, created = PartCategory.objects.get_or_create(
            name='Engine Components',
            defaults={'slug': 'engine-components'}
        )
        if created:
            self.stdout.write(f'Created category: {engine_category.name}')
        
        # Create Engine Components attributes
        bore_size_attr, created = PartAttribute.objects.get_or_create(
            category=engine_category,
            code='bore_size',
            defaults={
                'name': 'Bore Size',
                'data_type': 'dec',
                'unit': 'mm',
                'is_required': False,
                'sort_order': 1,
                'help_text': 'The bore size in millimeters'
            }
        )
        if created:
            self.stdout.write(f'Created attribute: {bore_size_attr.name}')
        
        stroke_length_attr, created = PartAttribute.objects.get_or_create(
            category=engine_category,
            code='stroke_length',
            defaults={
                'name': 'Stroke Length',
                'data_type': 'dec',
                'unit': 'mm',
                'is_required': False,
                'sort_order': 2,
                'help_text': 'The stroke length in millimeters'
            }
        )
        if created:
            self.stdout.write(f'Created attribute: {stroke_length_attr.name}')
        
        is_interference_attr, created = PartAttribute.objects.get_or_create(
            category=engine_category,
            code='is_interference',
            defaults={
                'name': 'Interference Engine',
                'data_type': 'bool',
                'unit': '',
                'is_required': False,
                'sort_order': 3,
                'help_text': 'Whether this is an interference engine'
            }
        )
        if created:
            self.stdout.write(f'Created attribute: {is_interference_attr.name}')
        
        self.stdout.write(self.style.SUCCESS('Successfully created sample custom field data'))
