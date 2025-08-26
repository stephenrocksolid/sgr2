from django.core.management.base import BaseCommand
from inventory.models import PartCategory, PartAttribute, PartAttributeChoice


class Command(BaseCommand):
    help = 'Create sample part categories and attributes for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample part categories and attributes...')

        # Create Engine Components category
        engine_cat, created = PartCategory.objects.get_or_create(
            name='Engine Components',
            defaults={'slug': 'engine-components'}
        )
        if created:
            self.stdout.write(f'Created category: {engine_cat.name}')

        # Create attributes for Engine Components
        attributes_data = [
            {
                'name': 'Thread Size',
                'code': 'thread_size',
                'data_type': 'text',
                'unit': 'mm',
                'help_text': 'Thread diameter and pitch (e.g., M8x1.25)',
                'is_required': True,
                'sort_order': 1
            },
            {
                'name': 'Length',
                'code': 'length',
                'data_type': 'dec',
                'unit': 'mm',
                'help_text': 'Overall length of the component',
                'is_required': False,
                'sort_order': 2
            },
            {
                'name': 'Material',
                'code': 'material',
                'data_type': 'choice',
                'unit': '',
                'help_text': 'Primary material composition',
                'is_required': True,
                'sort_order': 3,
                'choices': [
                    ('steel', 'Steel'),
                    ('aluminum', 'Aluminum'),
                    ('brass', 'Brass'),
                    ('plastic', 'Plastic'),
                    ('rubber', 'Rubber')
                ]
            },
            {
                'name': 'Temperature Rating',
                'code': 'temp_rating',
                'data_type': 'int',
                'unit': '°C',
                'help_text': 'Maximum operating temperature',
                'is_required': False,
                'sort_order': 4
            },
            {
                'name': 'Heat Treated',
                'code': 'heat_treated',
                'data_type': 'bool',
                'unit': '',
                'help_text': 'Whether the component has been heat treated',
                'is_required': False,
                'sort_order': 5
            },
            {
                'name': 'Manufacture Date',
                'code': 'mfg_date',
                'data_type': 'date',
                'unit': '',
                'help_text': 'Date of manufacture',
                'is_required': False,
                'sort_order': 6
            }
        ]

        for attr_data in attributes_data:
            choices = attr_data.pop('choices', [])
            attr, created = PartAttribute.objects.get_or_create(
                category=engine_cat,
                code=attr_data['code'],
                defaults=attr_data
            )
            if created:
                self.stdout.write(f'Created attribute: {attr.name}')
                
                # Create choices for choice-type attributes
                if attr.data_type == 'choice':
                    for choice_value, choice_label in choices:
                        choice, choice_created = PartAttributeChoice.objects.get_or_create(
                            attribute=attr,
                            value=choice_value,
                            defaults={'label': choice_label, 'sort_order': len(choices)}
                        )
                        if choice_created:
                            self.stdout.write(f'  Created choice: {choice.label}')

        # Create Electrical Components category
        electrical_cat, created = PartCategory.objects.get_or_create(
            name='Electrical Components',
            defaults={'slug': 'electrical-components'}
        )
        if created:
            self.stdout.write(f'Created category: {electrical_cat.name}')

        # Create attributes for Electrical Components
        electrical_attrs = [
            {
                'name': 'Voltage Rating',
                'code': 'voltage_rating',
                'data_type': 'int',
                'unit': 'V',
                'help_text': 'Maximum voltage rating',
                'is_required': True,
                'sort_order': 1
            },
            {
                'name': 'Current Rating',
                'code': 'current_rating',
                'data_type': 'dec',
                'unit': 'A',
                'help_text': 'Maximum current rating',
                'is_required': True,
                'sort_order': 2
            },
            {
                'name': 'Wire Gauge',
                'code': 'wire_gauge',
                'data_type': 'text',
                'unit': 'AWG',
                'help_text': 'Wire gauge specification',
                'is_required': False,
                'sort_order': 3
            },
            {
                'name': 'Waterproof',
                'code': 'waterproof',
                'data_type': 'bool',
                'unit': '',
                'help_text': 'Whether the component is waterproof',
                'is_required': False,
                'sort_order': 4
            }
        ]

        for attr_data in electrical_attrs:
            attr, created = PartAttribute.objects.get_or_create(
                category=electrical_cat,
                code=attr_data['code'],
                defaults=attr_data
            )
            if created:
                self.stdout.write(f'Created attribute: {attr.name}')

        self.stdout.write(self.style.SUCCESS('Successfully created sample categories and attributes'))
