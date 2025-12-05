import os
import sys
import django

# Force unbuffered output
sys.stdout = sys.stderr

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgr_manager.settings')
django.setup()

from jobs.models import PurchaseOrder
from django.contrib.auth.models import User
from inventory.models import Vendor
from datetime import date, timedelta
import random

# Write output to a file as well
with open('create_pos_log.txt', 'w') as log:
    # Get a user for requested_by
    user = User.objects.first()
    log.write(f"Using user: {user}\n")

    # Get some vendors if available
    vendors = list(Vendor.objects.all()[:10])
    log.write(f"Found {len(vendors)} vendors\n")

    # Status choices
    statuses = ['draft', 'submitted', 'partially_received', 'received']

    # Create 250 POs
    created = 0
    for i in range(250):
        po_number = f'PO-TEST-{i+1:04d}'
        
        # Check if already exists
        if PurchaseOrder.objects.filter(po_number=po_number).exists():
            log.write(f"Skipping {po_number} - already exists\n")
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
            log.write(f"Created {created} POs...\n")

    log.write(f'\nCreated {created} test purchase orders\n')
    log.write(f'Total POs now: {PurchaseOrder.objects.count()}\n')
    
print("Done! Check create_pos_log.txt for details")


