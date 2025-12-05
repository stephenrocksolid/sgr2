"""Tests for Job Employee Assignment Modal functionality."""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from jobs.models import Job, Employee, JobEmployee

User = get_user_model()


class JobEmployeeModalTestCase(TestCase):
    """Test the employee assignment modal functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create a job
        self.job = Job.objects.create(
            job_type='job',
            job_number='J001',
            status='wo'
        )
        
        # Create employees
        self.emp1 = Employee.objects.create(name='John Doe', department='Machining')
        self.emp2 = Employee.objects.create(name='Jane Smith', department='Assembly')
        self.emp3 = Employee.objects.create(name='Bob Johnson', department='Inspection')
        
        # Assign one employee to the job
        JobEmployee.objects.create(
            job=self.job,
            employee=self.emp1,
            calculated_total_time=5.5
        )
    
    def test_modal_loads_all_employees(self):
        """Test that the modal shows all employees."""
        url = reverse('jobs:job_employee_assign_modal', kwargs={'pk': self.job.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')
        self.assertContains(response, 'Bob Johnson')
        self.assertContains(response, 'Machining')
        self.assertContains(response, 'Assembly')
        self.assertContains(response, 'Inspection')
    
    def test_modal_prechecks_assigned_employees(self):
        """Test that already assigned employees are pre-checked."""
        url = reverse('jobs:job_employee_assign_modal', kwargs={'pk': self.job.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that emp1's ID is in the assigned list
        self.assertIn(self.emp1.id, response.context['assigned_employee_ids'])
        # Check that emp2 and emp3 are not in the assigned list
        self.assertNotIn(self.emp2.id, response.context['assigned_employee_ids'])
        self.assertNotIn(self.emp3.id, response.context['assigned_employee_ids'])
    
    def test_add_multiple_employees(self):
        """Test adding multiple employees at once."""
        url = reverse('jobs:job_employee_assign', kwargs={'pk': self.job.pk})
        
        # Submit with emp1 (already assigned), emp2 (new), and emp3 (new)
        response = self.client.post(url, {
            'employee_ids': [self.emp1.id, self.emp2.id, self.emp3.id]
        })
        
        # Should have 3 employees assigned now
        self.assertEqual(JobEmployee.objects.filter(job=self.job).count(), 3)
        
        # Check that emp2 and emp3 were added with time = 0
        emp2_assignment = JobEmployee.objects.get(job=self.job, employee=self.emp2)
        emp3_assignment = JobEmployee.objects.get(job=self.job, employee=self.emp3)
        
        self.assertEqual(emp2_assignment.calculated_total_time, 0)
        self.assertEqual(emp3_assignment.calculated_total_time, 0)
        
        # Check that emp1's time wasn't changed
        emp1_assignment = JobEmployee.objects.get(job=self.job, employee=self.emp1)
        self.assertEqual(emp1_assignment.calculated_total_time, 5.5)
    
    def test_remove_employees_by_unchecking(self):
        """Test removing employees by unchecking them."""
        # First add emp2 and emp3
        JobEmployee.objects.create(job=self.job, employee=self.emp2, calculated_total_time=3.0)
        JobEmployee.objects.create(job=self.job, employee=self.emp3, calculated_total_time=2.0)
        
        # Should have 3 employees now
        self.assertEqual(JobEmployee.objects.filter(job=self.job).count(), 3)
        
        # Now submit with only emp1 checked (uncheck emp2 and emp3)
        url = reverse('jobs:job_employee_assign', kwargs={'pk': self.job.pk})
        response = self.client.post(url, {
            'employee_ids': [self.emp1.id]
        })
        
        # Should have only 1 employee now
        self.assertEqual(JobEmployee.objects.filter(job=self.job).count(), 1)
        
        # Check that only emp1 remains
        self.assertTrue(JobEmployee.objects.filter(job=self.job, employee=self.emp1).exists())
        self.assertFalse(JobEmployee.objects.filter(job=self.job, employee=self.emp2).exists())
        self.assertFalse(JobEmployee.objects.filter(job=self.job, employee=self.emp3).exists())
    
    def test_uncheck_all_employees(self):
        """Test removing all employees by unchecking all."""
        url = reverse('jobs:job_employee_assign', kwargs={'pk': self.job.pk})
        
        # Submit with no employee_ids (all unchecked)
        response = self.client.post(url, {
            'employee_ids': []
        })
        
        # Should have 0 employees assigned now
        self.assertEqual(JobEmployee.objects.filter(job=self.job).count(), 0)
    
    def test_modal_shows_done_button(self):
        """Test that the modal has a 'Done' button instead of 'Assign'."""
        url = reverse('jobs:job_employee_assign_modal', kwargs={'pk': self.job.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Done')
        self.assertNotContains(response, 'Assign</button>')
    
    def test_preserves_existing_time_data(self):
        """Test that existing time data is preserved when re-assigning."""
        # emp1 already has 5.5 hours
        url = reverse('jobs:job_employee_assign', kwargs={'pk': self.job.pk})
        
        # Re-submit with emp1 and emp2
        response = self.client.post(url, {
            'employee_ids': [self.emp1.id, self.emp2.id]
        })
        
        # emp1's time should still be 5.5
        emp1_assignment = JobEmployee.objects.get(job=self.job, employee=self.emp1)
        self.assertEqual(emp1_assignment.calculated_total_time, 5.5)
        
        # emp2 should have 0
        emp2_assignment = JobEmployee.objects.get(job=self.job, employee=self.emp2)
        self.assertEqual(emp2_assignment.calculated_total_time, 0)






