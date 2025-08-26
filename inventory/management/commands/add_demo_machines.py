from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Machine, Engine, SGEngine, MachineEngine, Part, Vendor, PartCategory
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add demo machines with various types, engines, and relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo machines before adding new ones',
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
            self.stdout.write('Clearing existing demo machines...')
            # Clear machines with "DEMO" in their model name
            demo_machines = Machine.objects.filter(model__icontains='DEMO')
            count = demo_machines.count()
            demo_machines.delete()
            self.stdout.write(f'Deleted {count} existing demo machines')

        # Demo machine data - showcasing different types and relationships
        demo_machines_data = [
            # Agricultural Tractors
            {
                'make': 'John Deere',
                'model': 'DEMO-4020-Tractor',
                'year': 1965,
                'machine_type': 'Tractor',
                'market_type': 'Agricultural',
                'engines': ['John Deere 4020'],
                'description': 'Classic John Deere tractor with 4020 engine'
            },
            {
                'make': 'Ford',
                'model': 'DEMO-8N-Tractor',
                'year': 1952,
                'machine_type': 'Tractor',
                'market_type': 'Agricultural',
                'engines': ['Ford 8N'],
                'description': 'Vintage Ford tractor with 8N engine'
            },
            {
                'make': 'International Harvester',
                'model': 'DEMO-1066-Tractor',
                'year': 1971,
                'machine_type': 'Tractor',
                'market_type': 'Agricultural',
                'engines': ['International Harvester 1066'],
                'description': 'IH tractor with 1066 engine'
            },
            
            # Construction Equipment
            {
                'make': 'CATERPILLAR',
                'model': 'DEMO-D3C-Dozer',
                'year': 1985,
                'machine_type': 'LOADER',
                'market_type': 'CONSTRUCTION',
                'engines': ['CATERPILLAR 3054'],
                'description': 'CAT D3C bulldozer with 3054 engine'
            },
            {
                'make': 'CATERPILLAR',
                'model': 'DEMO-933C-Loader',
                'year': 1990,
                'machine_type': 'LOADER',
                'market_type': 'CONSTRUCTION',
                'engines': ['CATERPILLAR 3046'],
                'description': 'CAT 933C wheel loader with 3046 engine'
            },
            {
                'make': 'CATERPILLAR',
                'model': 'DEMO-D5C-Dozer',
                'year': 1995,
                'machine_type': 'LOADER',
                'market_type': 'CONSTRUCTION',
                'engines': ['CATERPILLAR 3056'],
                'description': 'CAT D5C bulldozer with 3056 engine'
            },
            
            # Skid Steers
            {
                'make': 'Bobcat',
                'model': 'DEMO-S185-SkidSteer',
                'year': 2005,
                'machine_type': 'SKID STEER',
                'market_type': 'CONSTRUCTION',
                'engines': ['KUBOTA V2203'],
                'description': 'Bobcat S185 skid steer with Kubota engine'
            },
            {
                'make': 'CATERPILLAR',
                'model': 'DEMO-236B-SkidSteer',
                'year': 2008,
                'machine_type': 'SKID STEER',
                'market_type': 'CONSTRUCTION',
                'engines': ['PERKINS 1104D-44T'],
                'description': 'CAT 236B skid steer with Perkins engine'
            },
            
            # Power Units
            {
                'make': 'CATERPILLAR',
                'model': 'DEMO-C15-PowerUnit',
                'year': 2000,
                'machine_type': 'POWER UNIT',
                'market_type': 'INDUSTRIAL',
                'engines': ['CATERPILLAR C15'],
                'description': 'CAT C15 power unit for industrial applications'
            },
            {
                'make': 'Cummins',
                'model': 'DEMO-QSK19-PowerUnit',
                'year': 2002,
                'machine_type': 'POWER UNIT',
                'market_type': 'INDUSTRIAL',
                'engines': ['CUMMINS QSK19'],
                'description': 'Cummins QSK19 power unit'
            },
            
            # Multi-engine machines (showcasing relationships)
            {
                'make': 'CATERPILLAR',
                'model': 'DEMO-988H-Loader',
                'year': 2010,
                'machine_type': 'LOADER',
                'market_type': 'CONSTRUCTION',
                'engines': ['CATERPILLAR C32', 'CATERPILLAR 3054'],
                'description': 'CAT 988H large wheel loader with dual engines'
            },
        ]

        created_machines = []
        created_engines = []

        for machine_data in demo_machines_data:
            # Create or get the machine
            machine, created = Machine.objects.get_or_create(
                make=machine_data['make'],
                model=machine_data['model'],
                year=machine_data['year'],
                machine_type=machine_data['machine_type'],
                market_type=machine_data['market_type'],
                defaults={
                    'created_by': user,
                    'updated_by': user,
                }
            )
            
            if created:
                created_machines.append(machine)
                self.stdout.write(f'Created machine: {machine}')
            else:
                self.stdout.write(f'Machine already exists: {machine}')

            # Create or get engines and link them
            for engine_name in machine_data['engines']:
                # Try to find existing engine first
                engine = Engine.objects.filter(
                    engine_make__icontains=engine_name.split()[0],
                    engine_model__icontains=' '.join(engine_name.split()[1:])
                ).first()
                
                if not engine:
                    # Create new engine if not found
                    engine_make = engine_name.split()[0]
                    engine_model = ' '.join(engine_name.split()[1:])
                    
                    engine = Engine.objects.create(
                        engine_make=engine_make,
                        engine_model=engine_model,
                        status='Active',
                        price=Decimal('5000.00'),
                        created_by=user,
                        updated_by=user,
                    )
                    created_engines.append(engine)
                    self.stdout.write(f'Created engine: {engine}')

                # Link machine and engine
                machine_engine, created = MachineEngine.objects.get_or_create(
                    machine=machine,
                    engine=engine,
                    defaults={
                        'notes': machine_data['description'],
                        'is_primary': True,
                        'created_by': user,
                        'updated_by': user,
                    }
                )
                
                if created:
                    self.stdout.write(f'Linked {machine} to {engine}')

        # Create some demo parts and link them to machines
        self.create_demo_parts(user)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(created_machines)} demo machines and {len(created_engines)} engines'
            )
        )

    def create_demo_parts(self, user):
        """Create some demo parts and link them to machines."""
        
        # Get or create a category
        category, created = PartCategory.objects.get_or_create(
            name='Engine Parts',
            defaults={'slug': 'engine-parts'}
        )
        
        # Get or create a vendor
        vendor, created = Vendor.objects.get_or_create(
            name='Demo Parts Supplier',
            defaults={
                'contact_name': 'Demo Contact',
                'email': 'demo@partssupplier.com',
                'phone': '555-1234',
                'created_by': user,
                'updated_by': user,
            }
        )

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
                    'primary_vendor': vendor,
                    'created_by': user,
                    'updated_by': user,
                }
            )
            
            if created:
                created_parts.append(part)
                self.stdout.write(f'Created part: {part}')

        self.stdout.write(f'Created {len(created_parts)} demo parts')
