"""
Tests for vendor linking functionality in the import wizard.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from imports.models import ImportBatch, SavedImportMapping, ImportRow
from inventory.models import Vendor, Engine, SGEngine


class VendorLinkingTestCase(TestCase):
    """Test cases for vendor creation and linking during import."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test CSV content
        self.csv_content = """vendor_name,engine_make,engine_model,vendor_website,vendor_contact_email
Cummins,6BTA,5.9,https://cummins.com,contact@cummins.com
Caterpillar,C7,6.6,https://cat.com,sales@cat.com
Cummins,6BTA,5.9,https://cummins.com,contact@cummins.com"""
        
        # Create test batch
        self.batch = ImportBatch.objects.create(
            file=SimpleUploadedFile(
                "test.csv",
                self.csv_content.encode('utf-8'),
                content_type="text/csv"
            ),
            original_filename="test.csv",
            file_size=len(self.csv_content),
            file_type="csv",
            encoding="utf-8",
            delimiter=",",
            total_rows=3,
            discovered_headers=["vendor_name", "engine_make", "engine_model", "vendor_website", "vendor_contact_email"],
            preview_data=[
                ["Cummins", "6BTA", "5.9", "https://cummins.com", "contact@cummins.com"],
                ["Caterpillar", "C7", "6.6", "https://cat.com", "sales@cat.com"],
                ["Cummins", "6BTA", "5.9", "https://cummins.com", "contact@cummins.com"]
            ],
            created_by=self.user
        )
        
        # Create mapping with vendor fields
        self.mapping = SavedImportMapping.objects.create(
            name="Test Vendor Mapping",
            description="Test mapping for vendor import",
            engine_mapping={
                "engine_make": "engine_make",
                "engine_model": "engine_model"
            },
            vendor_mapping={
                "vendor_name": "vendor_name",
                "vendor_website": "vendor_website",
                "vendor_contact_email": "vendor_contact_email"
            },
            created_by=self.user
        )
        
        self.batch.mapping = self.mapping
        self.batch.save()
    
    def test_vendor_case_insensitive_constraint(self):
        """Test that vendor names are case-insensitive unique."""
        # Create first vendor
        vendor1 = Vendor.objects.create(name="Cummins")
        
        # Try to create vendor with different case - should fail
        with self.assertRaises(IntegrityError):
            Vendor.objects.create(name="CUMMINS")
    
    def test_vendor_creation_from_import(self):
        """Test that vendors are created correctly from import data."""
        from imports.tasks import process_vendor_row, normalize_row_data
        
        # Test first row
        row_data = {
            "vendor_name": "Cummins",
            "engine_make": "6BTA",
            "engine_model": "5.9",
            "vendor_website": "https://cummins.com",
            "vendor_contact_email": "contact@cummins.com"
        }
        
        # Create import row
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data=row_data
        )
        
        # Normalize data
        normalized_data = normalize_row_data(row_data, self.mapping)
        
        # Process vendor row
        process_vendor_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Check vendor was created
        self.assertTrue(import_row.vendor_created)
        self.assertIsNotNone(import_row.vendor_id)
        
        vendor = Vendor.objects.get(id=import_row.vendor_id)
        self.assertEqual(vendor.name, "Cummins")
        self.assertEqual(vendor.website, "https://cummins.com")
        self.assertEqual(vendor.email, "contact@cummins.com")
    
    def test_vendor_deduplication(self):
        """Test that duplicate vendors are handled correctly."""
        from imports.tasks import process_vendor_row, normalize_row_data
        
        # Create existing vendor
        existing_vendor = Vendor.objects.create(
            name="Cummins",
            website="https://cummins.com",
            email="contact@cummins.com"
        )
        
        # Test row with same vendor name (different case)
        row_data = {
            "vendor_name": "cummins",  # lowercase
            "engine_make": "6BTA",
            "engine_model": "5.9",
            "vendor_website": "https://cummins.com",
            "vendor_contact_email": "contact@cummins.com"
        }
        
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data=row_data
        )
        
        normalized_data = normalize_row_data(row_data, self.mapping)
        
        # Process with skip_duplicates=True (default)
        process_vendor_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Should link to existing vendor, not create new one
        self.assertFalse(import_row.vendor_created)
        self.assertEqual(import_row.vendor_id, existing_vendor.id)
        
        # Should still be only one vendor
        self.assertEqual(Vendor.objects.count(), 1)
    
    def test_engine_vendor_linking(self):
        """Test that engines are linked to vendors correctly."""
        from imports.tasks import process_engine_row, process_vendor_row, create_relationships, normalize_row_data
        
        # Test data with both engine and vendor
        row_data = {
            "vendor_name": "Cummins",
            "engine_make": "6BTA",
            "engine_model": "5.9",
            "vendor_website": "https://cummins.com",
            "vendor_contact_email": "contact@cummins.com"
        }
        
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data=row_data
        )
        
        normalized_data = normalize_row_data(row_data, self.mapping)
        
        # Process engine first
        process_engine_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Process vendor
        process_vendor_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Create relationships
        create_relationships(self.batch, self.mapping, normalized_data, import_row)
        
        # Check that engine is linked to vendor
        self.assertTrue(import_row.engine_vendor_linked)
        
        engine = Engine.objects.get(id=import_row.engine_id)
        vendor = Vendor.objects.get(id=import_row.vendor_id)
        
        self.assertEqual(engine.vendor, vendor)
        self.assertIn(engine, vendor.engines.all())
    
    def test_vendor_mapping_form(self):
        """Test that vendor mapping form works correctly."""
        from imports.forms import VendorMappingForm
        
        discovered_headers = ["vendor_name", "vendor_website", "vendor_contact_email"]
        form = VendorMappingForm(discovered_headers=discovered_headers)
        
        # Check that all vendor fields are present
        self.assertIn('map_vendors_vendor_name', form.fields)
        self.assertIn('map_vendors_vendor_website', form.fields)
        self.assertIn('map_vendors_vendor_contact_email', form.fields)
        self.assertIn('create_missing_vendors', form.fields)
        
        # Check that header choices are populated
        vendor_name_field = form.fields['map_vendors_vendor_name']
        self.assertIn(('vendor_name', 'vendor_name'), vendor_name_field.choices)
        self.assertIn(('vendor_website', 'vendor_website'), vendor_name_field.choices)
    
    def test_vendor_statistics(self):
        """Test that vendor statistics are included in import results."""
        from imports.tasks import process_vendor_row, normalize_row_data
        
        # Create some import rows with vendors
        for i, vendor_name in enumerate(["Cummins", "Caterpillar", "Cummins"], 1):
            row_data = {
                "vendor_name": vendor_name,
                "engine_make": f"Engine{i}",
                "engine_model": f"Model{i}",
                "vendor_website": f"https://{vendor_name.lower()}.com",
                "vendor_contact_email": f"contact@{vendor_name.lower()}.com"
            }
            
            import_row = ImportRow.objects.create(
                batch=self.batch,
                row_number=i,
                original_data=row_data
            )
            
            normalized_data = normalize_row_data(row_data, self.mapping)
            process_vendor_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Check statistics
        from django.db.models import Count, Q
        stats = self.batch.rows.aggregate(
            vendor_created=Count('id', filter=Q(vendor_created=True)),
            vendor_updated=Count('id', filter=Q(vendor_updated=True))
        )
        
        # Should have 2 vendors created (Cummins and Caterpillar, with Cummins deduplicated)
        self.assertEqual(stats['vendor_created'], 2)
        self.assertEqual(stats['vendor_updated'], 0)
        
        # Should have 2 unique vendors in database
        self.assertEqual(Vendor.objects.count(), 2)
