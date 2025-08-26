from django.core.management.base import BaseCommand
from inventory.models import Vendor


class Command(BaseCommand):
    help = 'Add demo vendors for testing'

    def handle(self, *args, **options):
        vendors_data = [
            {
                'name': 'ABC Supply Co.',
                'contact_name': 'John Smith',
                'email': 'john.smith@abcsupply.com',
                'phone': '(555) 123-4567',
                'website': 'https://www.abcsupply.com',
                'address': '123 Main Street\nAnytown, ST 12345',
                'notes': 'Primary supplier for engine parts and accessories.'
            },
            {
                'name': 'XYZ Parts Inc.',
                'contact_name': 'Sarah Johnson',
                'email': 'sarah.j@xyzparts.com',
                'phone': '(555) 987-6543',
                'website': 'https://www.xyzparts.com',
                'address': '456 Industrial Blvd\nManufacturing City, ST 67890',
                'notes': 'Specializes in high-quality replacement parts.'
            },
            {
                'name': 'Quality Engine Parts',
                'contact_name': 'Mike Wilson',
                'email': 'mike.wilson@qualityengine.com',
                'phone': '(555) 456-7890',
                'website': 'https://www.qualityengine.com',
                'address': '789 Engine Lane\nParts Town, ST 11111',
                'notes': 'Premium engine components and rebuild kits.'
            },
            {
                'name': 'Fast Parts Express',
                'contact_name': 'Lisa Davis',
                'email': 'lisa.davis@fastparts.com',
                'phone': '(555) 321-0987',
                'website': 'https://www.fastparts.com',
                'address': '321 Speed Way\nQuick City, ST 22222',
                'notes': 'Fast shipping and competitive pricing.'
            },
            {
                'name': 'Reliable Auto Supply',
                'contact_name': 'Tom Brown',
                'email': 'tom.brown@reliableauto.com',
                'phone': '(555) 654-3210',
                'website': 'https://www.reliableauto.com',
                'address': '654 Auto Drive\nReliable City, ST 33333',
                'notes': 'Trusted supplier for automotive parts and tools.'
            }
        ]

        created_count = 0
        for vendor_data in vendors_data:
            vendor, created = Vendor.objects.get_or_create(
                name=vendor_data['name'],
                defaults=vendor_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created vendor: {vendor.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Vendor already exists: {vendor.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new vendors')
        )

