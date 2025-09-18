import json
import tempfile
import os
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from .models import ImportBatch, SavedImportMapping, ImportRow
from inventory.models import Machine, Engine, Part, SGEngine, Vendor, PartVendor
from .tasks import (
    normalize_row_data, process_machine_row, process_engine_row, 
    process_part_row, create_relationships
)

class ImportTaskTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test mapping
        self.mapping = SavedImportMapping.objects.create(
            name='Test Mapping',
            description='Test mapping for unit tests',
            machine_mapping={
                'make': 'make',
                'model': 'model',
                'year': 'year',
                'machine_type': 'machine_type',
                'market_type': 'market_type'
            },
            engine_mapping={
                'engine_make': 'engine_make',
                'engine_model': 'engine_model',
                'sg_make': 'sg_make',
                'sg_model': 'sg_model',
                'cpl_number': 'cpl_number'
            },
            part_mapping={
                'part_number': 'part_number',
                'name': 'name',
                'category': 'category',
                'manufacturer': 'manufacturer'
            },
            chunk_size=1000,
            skip_duplicates=True,
            update_existing=False
        )
        
        # Create test batch
        self.batch = ImportBatch.objects.create(
            original_filename='test.csv',
            file_type='csv',
            file_size=1024,  # Add required file_size
            encoding='utf-8',
            delimiter=',',
            total_rows=1,
            status='mapped',
            mapping=self.mapping,
            created_by=self.user
        )

    def test_normalize_row_data(self):
        """Test data normalization functionality."""
        row_data = {
            'make': '  Honda  ',
            'model': 'Civic  ',
            'year': '2020',
            'part_number': 'ABC123',
            'name': 'Test Part',
            'engine_make': 'Honda',
            'engine_model': 'K20',
            'vendor_name': 'Test Vendor',
            'vendor_cost': '25.50',
            'vendor_stock_qty': '100'
        }
        
        normalized = normalize_row_data(row_data, self.mapping)
        
        # Test string normalization (trim/collapse spaces)
        self.assertEqual(normalized['machine']['make'], 'Honda')
        self.assertEqual(normalized['machine']['model'], 'Civic')
        
        # Test integer normalization
        self.assertEqual(normalized['machine']['year'], 2020)
        
        # Test uppercase part_number
        self.assertEqual(normalized['part']['part_number'], 'ABC123')
        
        # Test decimal normalization
        self.assertEqual(normalized['vendor']['vendor_cost'], Decimal('25.50'))
        self.assertEqual(normalized['vendor']['vendor_stock_qty'], 100)

    def test_process_machine_row(self):
        """Test machine row processing with deduplication."""
        # Create ImportRow
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={}
        )
        
        normalized_data = {
            'machine': {
                'make': 'Honda',
                'model': 'Civic',
                'year': 2020,
                'machine_type': 'Sedan',
                'market_type': 'Consumer'
            }
        }
        
        # Process machine row
        process_machine_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Verify machine was created
        self.assertTrue(import_row.machine_created)
        self.assertIsNotNone(import_row.machine_id)
        
        # Verify machine exists in database
        machine = Machine.objects.get(id=import_row.machine_id)
        self.assertEqual(machine.make, 'Honda')
        self.assertEqual(machine.model, 'Civic')
        self.assertEqual(machine.year, 2020)
        
        # Test deduplication - should not create duplicate
        import_row2 = ImportRow.objects.create(
            batch=self.batch,
            row_number=2,
            original_data={}
        )
        
        process_machine_row(self.batch, self.mapping, normalized_data, import_row2)
        
        # Should not create new machine, should reference existing
        self.assertFalse(import_row2.machine_created)
        self.assertEqual(import_row2.machine_id, import_row.machine_id)

    def test_process_engine_row(self):
        """Test engine row processing with SG Engine mapping."""
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={}
        )
        
        normalized_data = {
            'engine': {
                'engine_make': 'Honda',
                'engine_model': 'K20',
                'sg_make': 'Honda',
                'sg_model': 'K20',
                'cpl_number': 'K20A1'
            }
        }
        
        # Process engine row
        process_engine_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Verify engine was created
        self.assertTrue(import_row.engine_created)
        self.assertIsNotNone(import_row.engine_id)
        
        # Verify engine exists in database
        engine = Engine.objects.get(id=import_row.engine_id)
        self.assertEqual(engine.engine_make, 'Honda')
        self.assertEqual(engine.engine_model, 'K20')
        self.assertEqual(engine.cpl_number, 'K20A1')
        
        # Verify SG Engine was created and linked
        self.assertIsNotNone(engine.sg_engine)
        self.assertEqual(engine.sg_engine.sg_make, 'Honda')
        self.assertEqual(engine.sg_engine.sg_model, 'K20')

    def test_process_part_row(self):
        """Test part row processing."""
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={}
        )
        
        normalized_data = {
            'part': {
                'part_number': 'ABC123',
                'name': 'Test Part',
                'category': 'Engine',
                'manufacturer': 'Honda'
            }
        }
        
        # Process part row
        process_part_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Verify part was created
        self.assertTrue(import_row.part_created)
        self.assertIsNotNone(import_row.part_id)
        
        # Verify part exists in database
        part = Part.objects.get(id=import_row.part_id)
        self.assertEqual(part.part_number, 'ABC123')
        self.assertEqual(part.name, 'Test Part')
        self.assertEqual(part.category, 'Engine')
        self.assertEqual(part.manufacturer, 'Honda')

    def test_process_part_row_with_weight_and_vendor_pricing(self):
        """Test part row processing with weight and vendor pricing."""
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={}
        )
        
        normalized_data = {
            'part': {
                'part_number': 'ABC123',
                'name': 'Test Part',
                'manufacturer': 'Honda',
                'weight': Decimal('2.5')
            },
            'vendor': {
                'vendor_name': 'Test Vendor',
                'vendor_part_number': 'TV-ABC123',
                'vendor_price': Decimal('25.99'),
                'vendor_stock_qty': 10
            }
        }
        
        # Process part row
        process_part_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Verify part was created
        self.assertTrue(import_row.part_created)
        self.assertIsNotNone(import_row.part_id)
        
        # Verify part exists in database with weight
        part = Part.objects.get(id=import_row.part_id)
        self.assertEqual(part.part_number, 'ABC123')
        self.assertEqual(part.name, 'Test Part')
        self.assertEqual(part.weight, 2.5)
        
        # Verify vendor was created
        vendor = Vendor.objects.get(name='Test Vendor')
        self.assertEqual(part.vendor, vendor)
        
        # Verify PartVendor relationship was created
        part_vendor = PartVendor.objects.get(part=part, vendor=vendor)
        self.assertEqual(part_vendor.vendor_part_number, 'TV-ABC123')
        self.assertEqual(part_vendor.price, Decimal('25.99'))
        self.assertEqual(part_vendor.stock_qty, 10)
        
        # Verify tracking
        self.assertTrue(import_row.part_vendor_created)

    def test_update_existing_part_with_vendor_pricing(self):
        """Test updating existing part with vendor pricing."""
        # Create existing part
        part = Part.objects.create(
            part_number='ABC123',
            name='Test Part',
            manufacturer='Honda'
        )
        
        # Create existing vendor
        vendor = Vendor.objects.create(name='Test Vendor')
        
        # Create import row
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={}
        )
        
        normalized_data = {
            'part': {
                'part_number': 'ABC123',
                'name': 'Test Part',
                'manufacturer': 'Honda',
                'weight': Decimal('2.5')
            },
            'vendor': {
                'vendor_name': 'Test Vendor',
                'vendor_part_number': 'TV-ABC123',
                'vendor_price': Decimal('25.99'),
                'vendor_stock_qty': 10
            }
        }
        
        # Process part row with update_existing=True
        self.mapping.skip_duplicates = False
        self.mapping.update_existing = True
        self.mapping.save()
        process_part_row(self.batch, self.mapping, normalized_data, import_row)
        
        # Verify part was updated
        part.refresh_from_db()
        self.assertEqual(part.weight, Decimal('2.5'))
        
        # Verify PartVendor relationship was created
        part_vendor = PartVendor.objects.get(part=part, vendor=vendor)
        self.assertEqual(part_vendor.vendor_part_number, 'TV-ABC123')
        self.assertEqual(part_vendor.price, Decimal('25.99'))
        self.assertEqual(part_vendor.stock_qty, 10)
        
        # Verify tracking
        self.assertTrue(import_row.part_vendor_created)

    def test_create_relationships(self):
        """Test relationship creation between entities."""
        # Create test entities
        machine = Machine.objects.create(
            make='Honda',
            model='Civic',
            year=2020,
            machine_type='Sedan',
            market_type='Consumer'
        )
        
        engine = Engine.objects.create(
            engine_make='Honda',
            engine_model='K20'
        )
        
        part = Part.objects.create(
            part_number='ABC123',
            name='Test Part'
        )
        
        # Create ImportRow with IDs
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={},
            machine_id=machine.id,
            engine_id=engine.id,
            part_id=part.id
        )
        
        # Create relationships
        create_relationships(self.batch, self.mapping, {}, import_row)
        
        # Verify relationships were created
        self.assertTrue(import_row.machine_engine_created)
        self.assertTrue(import_row.engine_part_created)
        
        # Verify relationships exist in database
        from inventory.models import MachineEngine, EnginePart
        self.assertTrue(MachineEngine.objects.filter(machine=machine, engine=engine).exists())
        self.assertTrue(EnginePart.objects.filter(engine=engine, part=part).exists())

    def test_vendor_relationship_creation(self):
        """Test vendor relationship creation."""
        part = Part.objects.create(
            part_number='ABC123',
            name='Test Part'
        )
        
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={},
            part_id=part.id
        )
        
        normalized_data = {
            'vendor': {
                'vendor_name': 'Test Vendor',
                'vendor_sku': 'TV-001',
                'vendor_cost': Decimal('25.50'),
                'vendor_stock_qty': 100,
                'vendor_lead_time_days': 5
            }
        }
        
        # Create relationships
        create_relationships(self.batch, self.mapping, normalized_data, import_row)
        
        # Verify vendor was created
        vendor = Vendor.objects.get(name='Test Vendor')
        
        # Verify PartVendor relationship was created
        from inventory.models import PartVendor
        part_vendor = PartVendor.objects.get(part=part, vendor=vendor)
        self.assertEqual(part_vendor.vendor_sku, 'TV-001')
        self.assertEqual(part_vendor.cost, Decimal('25.50'))
        self.assertEqual(part_vendor.stock_qty, 100)
        self.assertEqual(part_vendor.lead_time_days, 5)
        
        self.assertTrue(import_row.part_vendor_created)

    def test_error_handling(self):
        """Test error handling in row processing."""
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={}
        )
        
        # Test missing required fields
        normalized_data = {
            'machine': {
                'make': 'Honda'
                # Missing 'model' - should cause error
            }
        }
        
        with self.assertRaises(Exception) as context:
            process_machine_row(self.batch, self.mapping, normalized_data, import_row)
        
        self.assertIn('Machine requires: model', str(context.exception))
        
        # Verify error was recorded
        import_row.refresh_from_db()
        self.assertTrue(import_row.has_errors)
        self.assertIn('Machine requires: model', import_row.error_messages[0])

    def test_empty_string_handling(self):
        """Test that empty strings are converted to None."""
        row_data = {
            'make': '',
            'model': '   ',
            'year': '',
            'part_number': 'ABC123',
            'name': 'Test Part'
        }
        
        normalized = normalize_row_data(row_data, self.mapping)
        
        # Empty strings should be None
        self.assertNotIn('make', normalized['machine'])
        self.assertNotIn('model', normalized['machine'])
        self.assertNotIn('year', normalized['machine'])
        
        # Non-empty strings should be preserved
        self.assertEqual(normalized['part']['part_number'], 'ABC123')
        self.assertEqual(normalized['part']['name'], 'Test Part')
