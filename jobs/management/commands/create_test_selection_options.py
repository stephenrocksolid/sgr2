from django.core.management.base import BaseCommand
from jobs.models import JobSelectionOption


class Command(BaseCommand):
    help = 'Creates test job selection options (25 per category)'

    def handle(self, *args, **options):
        # Parts Selection options
        parts_names = [
            "Standard Piston Set", "Performance Piston Kit", "Economy Pistons",
            "Racing Pistons", "Forged Pistons", "Cast Pistons", "Hypereutectic Pistons",
            "Dome Top Pistons", "Flat Top Pistons", "Dish Pistons",
            "Standard Ring Set", "Moly Ring Set", "Chrome Ring Set",
            "File Fit Rings", "Gapless Rings", "Standard Bearings",
            "Performance Bearings", "Coated Bearings", "Clevite Bearings",
            "King Bearings", "ACL Bearings", "Mahle Bearings",
            "Federal Mogul Bearings", "OEM Bearings", "Premium Bearings"
        ]
        
        # Block Build Lists options
        block_names = [
            "Standard Block Rebuild", "Performance Block Build", "Racing Block Prep",
            "Economy Block Service", "Complete Block Overhaul", "Block Machining Only",
            "Deck Surface", "Line Bore", "Bore & Hone",
            "Sleeve Install", "Block Clean & Inspect", "Main Cap Install",
            "Freeze Plug Install", "Oil Gallery Service", "Cam Bearing Install",
            "Block Assembly", "Short Block Assembly", "Basic Block Prep",
            "Street Performance Block", "Competition Block Build", "Diesel Block Service",
            "Marine Block Prep", "Industrial Block Build", "Agricultural Engine Block",
            "Vintage Block Restoration"
        ]
        
        # Head Build Lists options
        head_names = [
            "Standard Head Rebuild", "Performance Head Work", "Racing Head Prep",
            "Economy Head Service", "Valve Job Standard", "Valve Job Performance",
            "3-Angle Valve Job", "5-Angle Valve Job", "Competition Valve Job",
            "Head Resurface", "Head Crack Repair", "Seat Replacement",
            "Guide Replacement", "Bronze Guide Install", "Valve Seal Install",
            "Spring Install", "Retainer Install", "Head Assembly",
            "Port & Polish", "CNC Porting", "Hand Porting",
            "Combustion Chamber Work", "Head Flow Testing", "Diesel Head Service",
            "Aluminum Head Repair"
        ]
        
        # Item Selection options
        item_names = [
            "Timing Chain Kit", "Timing Belt Kit", "Water Pump Kit",
            "Oil Pump Kit", "Gasket Set - Full", "Gasket Set - Upper",
            "Gasket Set - Lower", "Head Gasket Set", "Intake Gasket Set",
            "Exhaust Gasket Set", "Valve Cover Gasket", "Oil Pan Gasket",
            "Rear Main Seal", "Front Cover Seal", "Cam Seal",
            "Harmonic Balancer", "Flexplate", "Flywheel",
            "Clutch Kit", "Starter", "Alternator",
            "Fuel Pump", "Oil Filter", "Air Filter",
            "Complete Engine Kit"
        ]
        
        created_count = 0
        
        # Create Parts Selection options
        for i, name in enumerate(parts_names):
            obj, created = JobSelectionOption.objects.get_or_create(
                name=name,
                group='parts_selection',
                defaults={
                    'sort_order': i + 1,
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {name} (parts_selection)')
        
        # Create Block Build Lists options
        for i, name in enumerate(block_names):
            obj, created = JobSelectionOption.objects.get_or_create(
                name=name,
                group='block_build_lists',
                defaults={
                    'sort_order': i + 1,
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {name} (block_build_lists)')
        
        # Create Head Build Lists options
        for i, name in enumerate(head_names):
            obj, created = JobSelectionOption.objects.get_or_create(
                name=name,
                group='head_build_lists',
                defaults={
                    'sort_order': i + 1,
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {name} (head_build_lists)')
        
        # Create Item Selection options
        for i, name in enumerate(item_names):
            obj, created = JobSelectionOption.objects.get_or_create(
                name=name,
                group='item_selection',
                defaults={
                    'sort_order': i + 1,
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {name} (item_selection)')
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} test selection options'))


