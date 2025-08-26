from django.core.management.base import BaseCommand
from inventory.models import Machine, Engine, BuildList, Kit, KitItem, Part, Vendor


class Command(BaseCommand):
    help = 'Show summary of demo data in the system'

    def handle(self, *args, **options):
        self.stdout.write('=== DEMO DATA SUMMARY ===')
        self.stdout.write('')
        
        # Count demo data
        demo_machines = Machine.objects.filter(model__icontains='DEMO')
        demo_build_lists = BuildList.objects.filter(name__icontains='DEMO')
        demo_kits = Kit.objects.filter(name__icontains='Kit')
        demo_kit_items = KitItem.objects.filter(notes__icontains='Demo')
        demo_parts = Part.objects.filter(part_number__startswith='DEMO-')
        demo_vendors = Vendor.objects.filter(name__icontains='Demo')
        
        self.stdout.write(f'Demo Machines: {demo_machines.count()}')
        self.stdout.write(f'Demo Build Lists: {demo_build_lists.count()}')
        self.stdout.write(f'Demo Kits: {demo_kits.count()}')
        self.stdout.write(f'Demo Kit Items: {demo_kit_items.count()}')
        self.stdout.write(f'Demo Parts: {demo_parts.count()}')
        self.stdout.write(f'Demo Vendors: {demo_vendors.count()}')
        
        self.stdout.write('')
        self.stdout.write('=== SAMPLE DEMO MACHINES ===')
        for machine in demo_machines[:5]:
            self.stdout.write(f'  {machine}')
        
        self.stdout.write('')
        self.stdout.write('=== SAMPLE BUILD LISTS ===')
        for build_list in demo_build_lists[:3]:
            self.stdout.write(f'  {build_list}')
        
        self.stdout.write('')
        self.stdout.write('=== SAMPLE KITS WITH PRICING ===')
        for kit in demo_kits[:3]:
            self.stdout.write(f'  {kit}')
            self.stdout.write(f'    Cost: ${kit.cost_total}, Sale: ${kit.sale_price}, Margin: {kit.margin_pct}%')
        
        self.stdout.write('')
        self.stdout.write('=== DEMO PARTS ===')
        for part in demo_parts:
            self.stdout.write(f'  {part}')
        
        self.stdout.write('')
        self.stdout.write('=== DEMO VENDORS ===')
        for vendor in demo_vendors:
            self.stdout.write(f'  {vendor}')
        
        self.stdout.write('')
        self.stdout.write('=== USAGE INSTRUCTIONS ===')
        self.stdout.write('1. Visit /engines/ to see all engines')
        self.stdout.write('2. Click on any engine to see its Build Lists section')
        self.stdout.write('3. Create or open Build Lists to see Kits')
        self.stdout.write('4. Open Kits to see Kit Items and pricing')
        self.stdout.write('5. Demo machines are prefixed with "DEMO-"')
        self.stdout.write('6. Demo build lists are prefixed with "DEMO-"')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo data is ready for testing!'))
