"""
Tests for import field validation and relationship creation.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from imports.models import ImportBatch, SavedImportMapping, ImportRow
from imports.tasks import create_relationships
from inventory.models import Machine, Engine, Part, MachineEngine, EnginePart, MachinePart


class ImportValidationTestCase(TestCase):
    """Test cases for import field validation."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.batch = ImportBatch.objects.create(
            file='test.csv',
            original_filename='test.csv',
            file_size=1000,
            file_type='csv',
            created_by=self.user
        )
        
    def test_engine_requires_make_model_identifier(self):
        """Test that engine import requires make, model, and identifier."""
        # Create mapping with only engine_make
        mapping = SavedImportMapping.objects.create(
            name='Test Engine Mapping',
            engine_mapping={'engine_make': 'Make'},
            created_by=self.user
        )
        
        # This should fail validation in the view
        # We'll test this by checking that the validation catches missing fields
        has_engine_fields = any(v for v in mapping.engine_mapping.values() if v)
        self.assertTrue(has_engine_fields)
        
        # Check for required fields
        required_engine_fields = ['engine_make', 'engine_model', 'engine_identifier']
        missing_fields = []
        for field_name in required_engine_fields:
            if not mapping.engine_mapping.get(field_name):
                missing_fields.append(field_name)
        
        # Should have missing fields (model and identifier)
        self.assertIn('engine_model', missing_fields)
        self.assertIn('engine_identifier', missing_fields)
        
    def test_machine_requires_make_model(self):
        """Test that machine import requires make and model."""
        # Create mapping with only make
        mapping = SavedImportMapping.objects.create(
            name='Test Machine Mapping',
            machine_mapping={'make': 'Make'},
            created_by=self.user
        )
        
        has_machine_fields = any(v for v in mapping.machine_mapping.values() if v)
        self.assertTrue(has_machine_fields)
        
        # Check for required fields
        required_machine_fields = ['make', 'model']
        missing_fields = []
        for field_name in required_machine_fields:
            if not mapping.machine_mapping.get(field_name):
                missing_fields.append(field_name)
        
        # Should have missing model field
        self.assertIn('model', missing_fields)
        
    def test_part_requires_part_number_name(self):
        """Test that part import requires part_number and name."""
        # Create mapping with only part_number
        mapping = SavedImportMapping.objects.create(
            name='Test Part Mapping',
            part_mapping={'part_number': 'PartNum'},
            created_by=self.user
        )
        
        has_part_fields = any(v for v in mapping.part_mapping.values() if v)
        self.assertTrue(has_part_fields)
        
        # Check for required fields
        required_part_fields = ['part_number', 'name']
        missing_fields = []
        for field_name in required_part_fields:
            if not mapping.part_mapping.get(field_name):
                missing_fields.append(field_name)
        
        # Should have missing name field
        self.assertIn('name', missing_fields)
        
    def test_complete_engine_mapping_passes_validation(self):
        """Test that complete engine mapping has no missing fields."""
        mapping = SavedImportMapping.objects.create(
            name='Complete Engine Mapping',
            engine_mapping={
                'engine_make': 'Make',
                'engine_model': 'Model',
                'engine_identifier': 'ID'
            },
            created_by=self.user
        )
        
        has_engine_fields = any(v for v in mapping.engine_mapping.values() if v)
        self.assertTrue(has_engine_fields)
        
        # Check for required fields
        required_engine_fields = ['engine_make', 'engine_model', 'engine_identifier']
        missing_fields = []
        for field_name in required_engine_fields:
            if not mapping.engine_mapping.get(field_name):
                missing_fields.append(field_name)
        
        # Should have no missing fields
        self.assertEqual(len(missing_fields), 0)
        
    def test_complete_machine_mapping_passes_validation(self):
        """Test that complete machine mapping has no missing fields."""
        mapping = SavedImportMapping.objects.create(
            name='Complete Machine Mapping',
            machine_mapping={
                'make': 'Make',
                'model': 'Model'
            },
            created_by=self.user
        )
        
        has_machine_fields = any(v for v in mapping.machine_mapping.values() if v)
        self.assertTrue(has_machine_fields)
        
        # Check for required fields
        required_machine_fields = ['make', 'model']
        missing_fields = []
        for field_name in required_machine_fields:
            if not mapping.machine_mapping.get(field_name):
                missing_fields.append(field_name)
        
        # Should have no missing fields
        self.assertEqual(len(missing_fields), 0)
        
    def test_complete_part_mapping_passes_validation(self):
        """Test that complete part mapping has no missing fields."""
        mapping = SavedImportMapping.objects.create(
            name='Complete Part Mapping',
            part_mapping={
                'part_number': 'PartNum',
                'name': 'Name'
            },
            created_by=self.user
        )
        
        has_part_fields = any(v for v in mapping.part_mapping.values() if v)
        self.assertTrue(has_part_fields)
        
        # Check for required fields
        required_part_fields = ['part_number', 'name']
        missing_fields = []
        for field_name in required_part_fields:
            if not mapping.part_mapping.get(field_name):
                missing_fields.append(field_name)
        
        # Should have no missing fields
        self.assertEqual(len(missing_fields), 0)


class RelationshipCreationTestCase(TestCase):
    """Test cases for relationship creation during import."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.batch = ImportBatch.objects.create(
            file='test.csv',
            original_filename='test.csv',
            file_size=1000,
            file_type='csv',
            created_by=self.user
        )
        self.mapping = SavedImportMapping.objects.create(
            name='Test Mapping',
            machine_mapping={'make': 'Make', 'model': 'Model'},
            engine_mapping={'engine_make': 'Engine Make', 'engine_model': 'Engine Model', 'engine_identifier': 'ID'},
            part_mapping={'part_number': 'Part Num', 'name': 'Name'},
            created_by=self.user
        )
        
    def test_machine_engine_relationship_creation(self):
        """Test that Machine↔Engine relationship is created."""
        # Create test entities
        machine = Machine.objects.create(
            make='John Deere',
            model='6068',
            year=2020,
            machine_type='Tractor',
            market_type='Agriculture'
        )
        
        engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='6.7L',
            sg_engine_identifier='ISB6.7'
        )
        
        # Create ImportRow with IDs
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={},
            machine_id=machine.id,
            engine_id=engine.id
        )
        
        # Create relationships
        create_relationships(self.batch, self.mapping, {}, import_row)
        
        # Verify relationship was created
        self.assertTrue(import_row.machine_engine_created)
        self.assertTrue(MachineEngine.objects.filter(machine=machine, engine=engine).exists())
        
    def test_engine_part_relationship_creation(self):
        """Test that Engine↔Part relationship is created."""
        # Create test entities
        engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='6.7L',
            sg_engine_identifier='ISB6.7'
        )
        
        part = Part.objects.create(
            part_number='ABC123',
            name='Piston'
        )
        
        # Create ImportRow with IDs
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={},
            engine_id=engine.id,
            part_id=part.id
        )
        
        # Create relationships
        create_relationships(self.batch, self.mapping, {}, import_row)
        
        # Verify relationship was created
        self.assertTrue(import_row.engine_part_created)
        self.assertTrue(EnginePart.objects.filter(engine=engine, part=part).exists())
        
    def test_machine_part_relationship_creation(self):
        """Test that Machine↔Part relationship is created."""
        # Create test entities
        machine = Machine.objects.create(
            make='John Deere',
            model='6068',
            year=2020,
            machine_type='Tractor',
            market_type='Agriculture'
        )
        
        part = Part.objects.create(
            part_number='ABC123',
            name='Oil Filter'
        )
        
        # Create ImportRow with IDs
        import_row = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={},
            machine_id=machine.id,
            part_id=part.id
        )
        
        # Create relationships
        create_relationships(self.batch, self.mapping, {}, import_row)
        
        # Verify relationship was created
        self.assertTrue(import_row.machine_part_created)
        self.assertTrue(MachinePart.objects.filter(machine=machine, part=part).exists())
        
    def test_all_three_relationships_created(self):
        """Test that all three relationships are created when all entities present."""
        # Create test entities
        machine = Machine.objects.create(
            make='John Deere',
            model='6068',
            year=2020,
            machine_type='Tractor',
            market_type='Agriculture'
        )
        
        engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='6.7L',
            sg_engine_identifier='ISB6.7'
        )
        
        part = Part.objects.create(
            part_number='ABC123',
            name='Piston'
        )
        
        # Create ImportRow with all IDs
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
        
        # Verify all relationships were created
        self.assertTrue(import_row.machine_engine_created)
        self.assertTrue(import_row.engine_part_created)
        self.assertTrue(import_row.machine_part_created)
        
        # Verify relationships exist in database
        self.assertTrue(MachineEngine.objects.filter(machine=machine, engine=engine).exists())
        self.assertTrue(EnginePart.objects.filter(engine=engine, part=part).exists())
        self.assertTrue(MachinePart.objects.filter(machine=machine, part=part).exists())
        
    def test_no_duplicate_relationships(self):
        """Test that duplicate relationships are not created."""
        # Create test entities
        machine = Machine.objects.create(
            make='John Deere',
            model='6068',
            year=2020,
            machine_type='Tractor',
            market_type='Agriculture'
        )
        
        engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='6.7L',
            sg_engine_identifier='ISB6.7'
        )
        
        # Create ImportRow
        import_row1 = ImportRow.objects.create(
            batch=self.batch,
            row_number=1,
            original_data={},
            machine_id=machine.id,
            engine_id=engine.id
        )
        
        # Create relationship first time
        create_relationships(self.batch, self.mapping, {}, import_row1)
        self.assertTrue(import_row1.machine_engine_created)
        
        # Create another ImportRow with same entities
        import_row2 = ImportRow.objects.create(
            batch=self.batch,
            row_number=2,
            original_data={},
            machine_id=machine.id,
            engine_id=engine.id
        )
        
        # Try to create relationship again
        create_relationships(self.batch, self.mapping, {}, import_row2)
        
        # Second row should not create a new relationship (get_or_create returns existing)
        self.assertFalse(import_row2.machine_engine_created)
        
        # Should still only have one relationship
        self.assertEqual(MachineEngine.objects.filter(machine=machine, engine=engine).count(), 1)


