from django.core.management.base import BaseCommand
from jobs.models import PurchaseOrder
from django.contrib.auth.models import User
from inventory.models import Vendor
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Create test purchase orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=250,
            help='Number of POs to create (default: 250)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Get a user for requested_by
        user = User.objects.first()
        self.stdout.write(f"Using user: {user}")

        # Get some vendors if available
        vendors = list(Vendor.objects.all()[:10])
        self.stdout.write(f"Found {len(vendors)} vendors")

        # Status choices
        statuses = ['draft', 'submitted', 'partially_received', 'received']

        # Create POs
        created = 0
        for i in range(count):
            po_number = f'PO-TEST-{i+1:04d}'
            
            # Check if already exists
            if PurchaseOrder.objects.filter(po_number=po_number).exists():
                continue
            
            # Random data
            status = random.choice(statuses)
            po_date = date.today() - timedelta(days=random.randint(0, 365))
            expected_date = po_date + timedelta(days=random.randint(7, 60)) if random.random() > 0.3 else None
            vendor = random.choice(vendors) if vendors and random.random() > 0.2 else None
            total = round(random.uniform(50, 5000), 2) if random.random() > 0.3 else 0
            is_urgent = random.random() > 0.85
            
            PurchaseOrder.objects.create(
                po_number=po_number,
                vendor=vendor,
                status=status,
                po_date=po_date,
                expected_delivery_date=expected_date,
                total_amount=total,
                is_urgent=is_urgent,
                requested_by=user,
                notes=f'Test PO #{i+1}' if random.random() > 0.5 else ''
            )
            created += 1
            if created % 50 == 0:
                self.stdout.write(f"Created {created} POs...")

        self.stdout.write(self.style.SUCCESS(f'Created {created} test purchase orders'))
        self.stdout.write(f'Total POs now: {PurchaseOrder.objects.count()}')



