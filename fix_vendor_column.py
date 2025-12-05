import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgr_manager.settings')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        # Alter the vendor_id column to allow NULL
        cursor.execute("ALTER TABLE jobs_purchaseorder ALTER COLUMN vendor_id DROP NOT NULL;")
        print("Successfully altered vendor_id column to allow NULL")
    # Commit the transaction
    connection.commit()
    print("Transaction committed")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()


