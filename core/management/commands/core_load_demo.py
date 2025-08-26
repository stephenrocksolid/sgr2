from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import (
    SGEngine, Engine, Machine, MachineEngine,
    Vendor, Part, EnginePart, PartVendor
)


class Command(BaseCommand):
    help = 'Load demo data for the SGR Part Manager system'

    def handle(self, *args, **options):
        self.stdout.write('Loading demo data...')
        
        # Get or create a superuser for audit fields
        user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@sgr.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write('Created demo user')
        else:
            self.stdout.write('Using existing demo user')
        
        # Create SGEngines
        self.stdout.write('Creating SGEngines...')
        sg_engines = []
        
        sg_engine1, created = SGEngine.objects.get_or_create(
            sg_make='John Deere',
            sg_model='4020',
            defaults={
                'identifier': 'JD-4020-001',
                'notes': 'Classic John Deere tractor engine',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            sg_engines.append(sg_engine1)
        
        sg_engine2, created = SGEngine.objects.get_or_create(
            sg_make='Ford',
            sg_model='8N',
            defaults={
                'identifier': 'FORD-8N-001',
                'notes': 'Ford 8N tractor engine',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            sg_engines.append(sg_engine2)
        
        # Create Engines
        self.stdout.write('Creating Engines...')
        engines = []
        
        engine1, created = Engine.objects.get_or_create(
            engine_make='John Deere',
            engine_model='4020',
            defaults={
                'sg_engine': sg_engine1,
                'cpl_number': 'CPL-4020-001',
                'cylinder': 4,
                'valves_per_cyl': 2,
                'bore_stroke': '4.25 x 4.75',
                'compression_ratio': 16.5,
                'firing_order': '1-3-4-2',
                'price': 2500.00,
                'status': 'Available',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            engines.append(engine1)
        
        engine2, created = Engine.objects.get_or_create(
            engine_make='Ford',
            engine_model='8N',
            defaults={
                'sg_engine': sg_engine2,
                'cpl_number': 'CPL-8N-001',
                'cylinder': 4,
                'valves_per_cyl': 2,
                'bore_stroke': '3.19 x 3.75',
                'compression_ratio': 6.6,
                'firing_order': '1-2-4-3',
                'price': 1800.00,
                'status': 'Available',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            engines.append(engine2)
        
        engine3, created = Engine.objects.get_or_create(
            engine_make='International Harvester',
            engine_model='1066',
            defaults={
                'cpl_number': 'CPL-1066-001',
                'cylinder': 6,
                'valves_per_cyl': 2,
                'bore_stroke': '4.56 x 5.00',
                'compression_ratio': 17.5,
                'firing_order': '1-5-3-6-2-4',
                'price': 3200.00,
                'status': 'Available',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            engines.append(engine3)
        
        # Create Machines
        self.stdout.write('Creating Machines...')
        machines = []
        
        machine1, created = Machine.objects.get_or_create(
            make='John Deere',
            model='4020',
            year=1965,
            machine_type='Tractor',
            market_type='Agricultural',
            defaults={
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            machines.append(machine1)
        
        machine2, created = Machine.objects.get_or_create(
            make='Ford',
            model='8N',
            year=1952,
            machine_type='Tractor',
            market_type='Agricultural',
            defaults={
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            machines.append(machine2)
        
        # Create Vendors
        self.stdout.write('Creating Vendors...')
        vendors = []
        
        vendor1, created = Vendor.objects.get_or_create(
            name='Tractor Supply Co.',
            defaults={
                'contact_name': 'John Smith',
                'email': 'john@tractorsupply.com',
                'phone': '555-123-4567',
                'address': '123 Main St, Farmville, PA',
                'notes': 'Primary supplier for tractor parts',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            vendors.append(vendor1)
        
        vendor2, created = Vendor.objects.get_or_create(
            name='AgriParts Plus',
            defaults={
                'contact_name': 'Mary Johnson',
                'email': 'mary@agriparts.com',
                'phone': '555-987-6543',
                'address': '456 Rural Rd, Countryside, PA',
                'notes': 'Specialized in vintage tractor parts',
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            vendors.append(vendor2)
        
        # Create Parts
        self.stdout.write('Creating Parts...')
        parts = []
        
        part1, created = Part.objects.get_or_create(
            part_number='JD-4020-PISTON',
            name='Piston Set - John Deere 4020',
            defaults={
                'category': 'Engine Components',
                'manufacturer': 'John Deere',
                'unit': 'Set',
                'type': 'Piston',
                'manufacturer_type': 'OEM',
                'preferred_vendor': vendor1,
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            parts.append(part1)
        
        part2, created = Part.objects.get_or_create(
            part_number='FORD-8N-CRANK',
            name='Crankshaft - Ford 8N',
            defaults={
                'category': 'Engine Components',
                'manufacturer': 'Ford',
                'unit': 'Each',
                'type': 'Crankshaft',
                'manufacturer_type': 'OEM',
                'preferred_vendor': vendor2,
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            parts.append(part2)
        
        part3, created = Part.objects.get_or_create(
            part_number='IH-1066-GASKET',
            name='Head Gasket - International 1066',
            defaults={
                'category': 'Gaskets',
                'manufacturer': 'International Harvester',
                'unit': 'Each',
                'type': 'Gasket',
                'manufacturer_type': 'OEM',
                'preferred_vendor': vendor1,
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            parts.append(part3)
        
        part4, created = Part.objects.get_or_create(
            part_number='UNIVERSAL-OIL',
            name='Engine Oil - 15W-40',
            defaults={
                'category': 'Lubricants',
                'manufacturer': 'Universal Lubricants',
                'unit': 'Gallon',
                'type': 'Oil',
                'manufacturer_type': 'Aftermarket',
                'preferred_vendor': vendor1,
                'created_by': user,
                'updated_by': user
            }
        )
        if created:
            parts.append(part4)
        
        # Create MachineEngine relationships
        self.stdout.write('Creating Machine-Engine relationships...')
        
        MachineEngine.objects.get_or_create(
            machine=machine1,
            engine=engine1,
            defaults={
                'notes': 'Primary engine for John Deere 4020',
                'is_primary': True,
                'created_by': user,
                'updated_by': user
            }
        )
        
        MachineEngine.objects.get_or_create(
            machine=machine2,
            engine=engine2,
            defaults={
                'notes': 'Primary engine for Ford 8N',
                'is_primary': True,
                'created_by': user,
                'updated_by': user
            }
        )
        
        # Create EnginePart relationships
        self.stdout.write('Creating Engine-Part relationships...')
        
        EnginePart.objects.get_or_create(
            engine=engine1,
            part=part1,
            defaults={
                'notes': 'Pistons compatible with John Deere 4020',
                'created_by': user,
                'updated_by': user
            }
        )
        
        EnginePart.objects.get_or_create(
            engine=engine1,
            part=part4,
            defaults={
                'notes': 'Recommended oil for John Deere 4020',
                'created_by': user,
                'updated_by': user
            }
        )
        
        EnginePart.objects.get_or_create(
            engine=engine2,
            part=part2,
            defaults={
                'notes': 'Crankshaft for Ford 8N engine',
                'created_by': user,
                'updated_by': user
            }
        )
        
        EnginePart.objects.get_or_create(
            engine=engine3,
            part=part3,
            defaults={
                'notes': 'Head gasket for International 1066',
                'created_by': user,
                'updated_by': user
            }
        )
        
        # Create PartVendor relationships with stock quantities
        self.stdout.write('Creating Part-Vendor relationships...')
        
        PartVendor.objects.get_or_create(
            part=part1,
            vendor=vendor1,
            defaults={
                'vendor_sku': 'TS-JD4020-PISTON',
                'cost': 450.00,
                'stock_qty': 5,
                'lead_time_days': 7,
                'created_by': user,
                'updated_by': user
            }
        )
        
        PartVendor.objects.get_or_create(
            part=part1,
            vendor=vendor2,
            defaults={
                'vendor_sku': 'APP-JD4020-PISTON',
                'cost': 425.00,
                'stock_qty': 3,
                'lead_time_days': 14,
                'created_by': user,
                'updated_by': user
            }
        )
        
        PartVendor.objects.get_or_create(
            part=part2,
            vendor=vendor2,
            defaults={
                'vendor_sku': 'APP-FORD8N-CRANK',
                'cost': 650.00,
                'stock_qty': 2,
                'lead_time_days': 21,
                'created_by': user,
                'updated_by': user
            }
        )
        
        PartVendor.objects.get_or_create(
            part=part3,
            vendor=vendor1,
            defaults={
                'vendor_sku': 'TS-IH1066-GASKET',
                'cost': 85.00,
                'stock_qty': 12,
                'lead_time_days': 3,
                'created_by': user,
                'updated_by': user
            }
        )
        
        PartVendor.objects.get_or_create(
            part=part4,
            vendor=vendor1,
            defaults={
                'vendor_sku': 'TS-OIL-15W40',
                'cost': 25.00,
                'stock_qty': 50,
                'lead_time_days': 1,
                'created_by': user,
                'updated_by': user
            }
        )
        
        PartVendor.objects.get_or_create(
            part=part4,
            vendor=vendor2,
            defaults={
                'vendor_sku': 'APP-OIL-15W40',
                'cost': 23.00,
                'stock_qty': 25,
                'lead_time_days': 5,
                'created_by': user,
                'updated_by': user
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded demo data:\n'
                f'- {len(sg_engines)} SGEngines\n'
                f'- {len(engines)} Engines\n'
                f'- {len(machines)} Machines\n'
                f'- {len(vendors)} Vendors\n'
                f'- {len(parts)} Parts\n'
                f'- Machine-Engine relationships\n'
                f'- Engine-Part relationships\n'
                f'- Part-Vendor relationships with stock quantities'
            )
        )
        
        self.stdout.write(
            self.style.WARNING(
                'Demo user created with username: demo_user, password: demo123'
            )
        )
