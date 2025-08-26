from django.test import TestCase
from django.contrib.auth.models import User
from inventory.models import Engine, EngineSupercession


class EngineRelationshipTests(TestCase):
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create test engines
        self.engine1 = Engine.objects.create(
            engine_make='CATERPILLAR',
            engine_model='3046',
            cpl_number='CPL001'
        )
        
        self.engine2 = Engine.objects.create(
            engine_make='CATERPILLAR',
            engine_model='3046T',
            cpl_number='CPL002'
        )
        
        self.engine3 = Engine.objects.create(
            engine_make='CUMMINS',
            engine_model='6BT 5.9',
            cpl_number='CPL003'
        )
    
    def test_interchange_relationship(self):
        """Test symmetrical interchange relationships."""
        # Add interchange relationship
        self.engine1.interchanges.add(self.engine2)
        
        # Verify symmetrical relationship
        self.assertIn(self.engine2, self.engine1.interchanges.all())
        self.assertIn(self.engine1, self.engine2.interchanges.all())
        
        # Remove relationship
        self.engine1.interchanges.remove(self.engine2)
        
        # Verify both sides are removed
        self.assertNotIn(self.engine2, self.engine1.interchanges.all())
        self.assertNotIn(self.engine1, self.engine2.interchanges.all())
    
    def test_compatible_relationship(self):
        """Test symmetrical compatible relationships."""
        # Add compatible relationship
        self.engine1.compatibles.add(self.engine3)
        
        # Verify symmetrical relationship
        self.assertIn(self.engine3, self.engine1.compatibles.all())
        self.assertIn(self.engine1, self.engine3.compatibles.all())
        
        # Remove relationship
        self.engine1.compatibles.remove(self.engine3)
        
        # Verify both sides are removed
        self.assertNotIn(self.engine3, self.engine1.compatibles.all())
        self.assertNotIn(self.engine1, self.engine3.compatibles.all())
    
    def test_supercession_relationship(self):
        """Test directional supercession relationships."""
        # Create supercession (engine2 supersedes engine1)
        supercession = EngineSupercession.objects.create(
            from_engine=self.engine1,
            to_engine=self.engine2,
            notes='Test supercession',
            effective_date='2024-01-01'
        )
        
        # Verify directional relationship
        self.assertIn(self.engine1, self.engine2.supersedes.all())
        self.assertIn(self.engine2, self.engine1.superseded_by.all())
        
        # Verify reverse relationship doesn't exist
        self.assertNotIn(self.engine2, self.engine1.supersedes.all())
        self.assertNotIn(self.engine1, self.engine2.superseded_by.all())
        
        # Test uniqueness constraint
        with self.assertRaises(Exception):
            EngineSupercession.objects.create(
                from_engine=self.engine1,
                to_engine=self.engine2,
                notes='Duplicate supercession'
            )
    
    def test_self_link_prevention(self):
        """Test that self-links are prevented."""
        # Test interchange self-link
        with self.assertRaises(Exception):
            self.engine1.interchanges.add(self.engine1)
        
        # Test compatible self-link
        with self.assertRaises(Exception):
            self.engine1.compatibles.add(self.engine1)
        
        # Test supercession self-link
        with self.assertRaises(Exception):
            EngineSupercession.objects.create(
                from_engine=self.engine1,
                to_engine=self.engine1
            )
