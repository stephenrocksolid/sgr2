from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import (
    Machine, Engine, BuildList, Kit, KitItem, Part, Vendor, PartCategory, PartVendor
)
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add demo Build Lists, Kits, and Kit Items to showcase the feature'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo build lists before adding new ones',
        )

    def handle(self, *args, **options):
        # Get or create a user for audit fields
        user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
            }
        )
        
        if options['clear']:
            self.stdout.write('Clearing existing demo build lists...')
            # Clear build lists with "DEMO" in their name
            demo_build_lists = BuildList.objects.filter(name__icontains='DEMO')
            count = demo_build_lists.count()
            demo_build_lists.delete()
            self.stdout.write(f'Deleted {count} existing demo build lists')

        # Get some demo machines and their engines
        demo_machines = Machine.objects.filter(model__icontains='DEMO')
        
        if not demo_machines.exists():
            self.stdout.write('No demo machines found. Please run add_demo_machines first.')
            return

        # Create demo parts and vendors if they don't exist
        self.create_demo_parts_and_vendors(user)

        # Get the created parts and vendors
        parts = Part.objects.filter(part_number__startswith='DEMO-')
        vendors = Vendor.objects.filter(name__icontains='Demo')

        if not parts.exists():
            self.stdout.write('No demo parts found. Please run add_demo_machines first.')
            return

        # Create build lists for different demo machines
        build_list_data = [
            {
                'machine': demo_machines.filter(model__icontains='4020').first(),
                'name': 'DEMO-4020-Standard-Build',
                'notes': 'Standard build configuration for John Deere 4020 tractor',
                'kits': [
                    {
                        'name': 'Engine Rebuild Kit',
                        'notes': 'Complete engine rebuild kit with all necessary parts',
                        'margin_pct': Decimal('25.00'),
                        'items': [
                            {'part_number': 'DEMO-001', 'vendor_name': 'Demo Parts Supplier', 'quantity': 2, 'unit_cost': Decimal('15.50')},
                            {'part_number': 'DEMO-002', 'vendor_name': 'Demo Parts Supplier', 'quantity': 1, 'unit_cost': Decimal('45.00')},
                            {'part_number': 'DEMO-003', 'vendor_name': 'Demo Parts Supplier', 'quantity': 1, 'unit_cost': Decimal('22.75')},
                        ]
                    },
                    {
                        'name': 'Hydraulic System Kit',
                        'notes': 'Hydraulic system maintenance and repair kit',
                        'margin_pct': Decimal('30.00'),
                        'items': [
                            {'part_number': 'DEMO-001', 'vendor_name': 'Demo Parts Supplier', 'quantity': 1, 'unit_cost': Decimal('15.50')},
                            {'part_number': 'DEMO-002', 'vendor_name': 'Demo Parts Supplier', 'quantity': 2, 'unit_cost': Decimal('45.00')},
                        ]
                    }
                ]
            },
            {
                'machine': demo_machines.filter(model__icontains='D3C').first(),
                'name': 'DEMO-D3C-Maintenance-Build',
                'notes': 'Regular maintenance build for CAT D3C bulldozer',
                'kits': [
                    {
                        'name': 'Preventive Maintenance Kit',
                        'notes': 'Scheduled maintenance kit for D3C bulldozer',
                        'margin_pct': Decimal('20.00'),
                        'items': [
                            {'part_number': 'DEMO-001', 'vendor_name': 'Demo Parts Supplier', 'quantity': 3, 'unit_cost': Decimal('15.50')},
                            {'part_number': 'DEMO-002', 'vendor_name': 'Demo Parts Supplier', 'quantity': 2, 'unit_cost': Decimal('45.00')},
                            {'part_number': 'DEMO-003', 'vendor_name': 'Demo Parts Supplier', 'quantity': 2, 'unit_cost': Decimal('22.75')},
                        ]
                    }
                ]
            },
            {
                'machine': demo_machines.filter(model__icontains='988H').first(),
                'name': 'DEMO-988H-Complete-Build',
                'notes': 'Complete rebuild package for large CAT 988H loader',
                'kits': [
                    {
                        'name': 'Engine Overhaul Kit',
                        'notes': 'Complete engine overhaul with premium parts',
                        'margin_pct': Decimal('35.00'),
                        'items': [
                            {'part_number': 'DEMO-001', 'vendor_name': 'Demo Parts Supplier', 'quantity': 4, 'unit_cost': Decimal('15.50')},
                            {'part_number': 'DEMO-002', 'vendor_name': 'Demo Parts Supplier', 'quantity': 3, 'unit_cost': Decimal('45.00')},
                            {'part_number': 'DEMO-003', 'vendor_name': 'Demo Parts Supplier', 'quantity': 3, 'unit_cost': Decimal('22.75')},
                        ]
                    },
                    {
                        'name': 'Transmission Kit',
                        'notes': 'Transmission rebuild kit for 988H',
                        'margin_pct': Decimal('40.00'),
                        'items': [
                            {'part_number': 'DEMO-001', 'vendor_name': 'Demo Parts Supplier', 'quantity': 2, 'unit_cost': Decimal('15.50')},
                            {'part_number': 'DEMO-002', 'vendor_name': 'Demo Parts Supplier', 'quantity': 1, 'unit_cost': Decimal('45.00')},
                        ]
                    },
                    {
                        'name': 'Hydraulic System Kit',
                        'notes': 'Complete hydraulic system rebuild',
                        'margin_pct': Decimal('25.00'),
                        'items': [
                            {'part_number': 'DEMO-003', 'vendor_name': 'Demo Parts Supplier', 'quantity': 2, 'unit_cost': Decimal('22.75')},
                        ]
                    }
                ]
            }
        ]

        created_build_lists = []
        created_kits = []
        created_kit_items = []

        for build_list_info in build_list_data:
            if not build_list_info['machine']:
                continue

            # Get the primary engine for this machine
            primary_engine = build_list_info['machine'].engines.filter(machineengine__is_primary=True).first()
            if not primary_engine:
                primary_engine = build_list_info['machine'].engines.first()

            if not primary_engine:
                self.stdout.write(f'No engine found for machine {build_list_info["machine"]}')
                continue

            # Create build list
            build_list, created = BuildList.objects.get_or_create(
                engine=primary_engine,
                name=build_list_info['name'],
                defaults={
                    'notes': build_list_info['notes'],
                }
            )
            
            if created:
                created_build_lists.append(build_list)
                self.stdout.write(f'Created build list: {build_list}')

            # Create kits for this build list
            for kit_info in build_list_info['kits']:
                kit, created = Kit.objects.get_or_create(
                    build_list=build_list,
                    name=kit_info['name'],
                    defaults={
                        'notes': kit_info['notes'],
                        'margin_pct': kit_info['margin_pct'],
                    }
                )
                
                if created:
                    created_kits.append(kit)
                    self.stdout.write(f'Created kit: {kit}')

                # Create kit items
                for item_info in kit_info['items']:
                    part = Part.objects.filter(part_number=item_info['part_number']).first()
                    vendor = Vendor.objects.filter(name=item_info['vendor_name']).first()
                    
                    if part and vendor:
                        kit_item, created = KitItem.objects.get_or_create(
                            kit=kit,
                            part=part,
                            vendor=vendor,
                            defaults={
                                'quantity': item_info['quantity'],
                                'unit_cost': item_info['unit_cost'],
                                'notes': f'Demo item for {kit.name}',
                            }
                        )
                        
                        if created:
                            created_kit_items.append(kit_item)
                            self.stdout.write(f'Created kit item: {kit_item}')

        # Recalculate totals for all created kits
        from inventory.models import recalc_kit_totals
        for kit in created_kits:
            recalc_kit_totals(kit)
            self.stdout.write(f'Recalculated totals for kit: {kit} (Cost: ${kit.cost_total}, Sale: ${kit.sale_price})')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(created_build_lists)} build lists, {len(created_kits)} kits, and {len(created_kit_items)} kit items'
            )
        )

    def create_demo_parts_and_vendors(self, user):
        """Create demo parts and vendors if they don't exist."""
        
        # Get or create a category
        category, created = PartCategory.objects.get_or_create(
            name='Engine Parts',
            defaults={'slug': 'engine-parts'}
        )
        
        # Get or create vendors
        vendors_data = [
            {
                'name': 'Demo Parts Supplier',
                'contact_name': 'Demo Contact',
                'email': 'demo@partssupplier.com',
                'phone': '555-1234',
            },
            {
                'name': 'Demo Premium Parts',
                'contact_name': 'Premium Contact',
                'email': 'premium@demoparts.com',
                'phone': '555-5678',
            }
        ]
        
        vendors = []
        for vendor_data in vendors_data:
            vendor, created = Vendor.objects.get_or_create(
                name=vendor_data['name'],
                defaults={
                    'contact_name': vendor_data['contact_name'],
                    'email': vendor_data['email'],
                    'phone': vendor_data['phone'],
                    'created_by': user,
                    'updated_by': user,
                }
            )
            vendors.append(vendor)

        # Demo parts data
        demo_parts = [
            {
                'part_number': 'DEMO-001',
                'name': 'Engine Oil Filter',
                'category': category,
                'manufacturer': 'Demo Manufacturing',
                'unit': 'Each',
                'type': 'Filter',
                'manufacturer_type': 'OEM',
            },
            {
                'part_number': 'DEMO-002',
                'name': 'Air Filter Element',
                'category': category,
                'manufacturer': 'Demo Manufacturing',
                'unit': 'Each',
                'type': 'Filter',
                'manufacturer_type': 'OEM',
            },
            {
                'part_number': 'DEMO-003',
                'name': 'Fuel Filter',
                'category': category,
                'manufacturer': 'Demo Manufacturing',
                'unit': 'Each',
                'type': 'Filter',
                'manufacturer_type': 'OEM',
            },
        ]

        created_parts = []
        for part_data in demo_parts:
            part, created = Part.objects.get_or_create(
                part_number=part_data['part_number'],
                name=part_data['name'],
                defaults={
                    'category': part_data['category'],
                    'manufacturer': part_data['manufacturer'],
                    'unit': part_data['unit'],
                    'type': part_data['type'],
                    'manufacturer_type': part_data['manufacturer_type'],
                    'primary_vendor': vendors[0],  # Use first vendor as primary
                }
            )
            
            if created:
                created_parts.append(part)
                self.stdout.write(f'Created part: {part}')

        # Create PartVendor relationships
        for part in created_parts:
            for vendor in vendors:
                part_vendor, created = PartVendor.objects.get_or_create(
                    part=part,
                    vendor=vendor,
                    defaults={
                        'vendor_sku': f'{vendor.name[:3].upper()}-{part.part_number}',
                        'cost': Decimal('15.50') if part.part_number == 'DEMO-001' else 
                               Decimal('45.00') if part.part_number == 'DEMO-002' else 
                               Decimal('22.75'),
                        'stock_qty': 100,
                        'lead_time_days': 7,
                    }
                )
                
                if created:
                    self.stdout.write(f'Created PartVendor: {part} - {vendor}')

        self.stdout.write(f'Created {len(created_parts)} demo parts and {len(vendors)} vendors')
