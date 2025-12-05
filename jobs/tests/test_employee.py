from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from jobs.models import Employee, Job, JobEmployee
from django.utils import timezone

User = get_user_model()


class EmployeeModelTest(TestCase):
    """Test the Employee model."""
    
    def setUp(self):
        self.employee = Employee.objects.create(
            name="John Doe",
            department="Engineering"
        )
    
    def test_employee_creation(self):
        """Test that an employee can be created."""
        self.assertEqual(self.employee.name, "John Doe")
        self.assertEqual(self.employee.department, "Engineering")
    
    def test_employee_str(self):
        """Test the employee string representation."""
        self.assertEqual(str(self.employee), "John Doe")
    
    def test_employee_ordering(self):
        """Test that employees are ordered by name."""
        Employee.objects.create(name="Alice Smith", department="Sales")
        Employee.objects.create(name="Bob Jones", department="HR")
        employees = Employee.objects.all()
        self.assertEqual(employees[0].name, "Alice Smith")
        self.assertEqual(employees[1].name, "Bob Jones")
        self.assertEqual(employees[2].name, "John Doe")


class JobEmployeeModelTest(TestCase):
    """Test the JobEmployee relationship model."""
    
    def setUp(self):
        self.employee = Employee.objects.create(name="Test Employee", department="Test")
        self.job = Job.objects.create(
            job_type='job',
            job_number='J001',
            status='quote',
            date=timezone.now().date()
        )
    
    def test_job_employee_creation(self):
        """Test that a JobEmployee relationship can be created."""
        job_emp = JobEmployee.objects.create(
            job=self.job,
            employee=self.employee,
            calculated_total_time=10.5
        )
        self.assertEqual(job_emp.job, self.job)
        self.assertEqual(job_emp.employee, self.employee)
        self.assertEqual(float(job_emp.calculated_total_time), 10.5)
    
    def test_job_employee_default_time(self):
        """Test that JobEmployee has default time of 0."""
        job_emp = JobEmployee.objects.create(
            job=self.job,
            employee=self.employee
        )
        self.assertEqual(float(job_emp.calculated_total_time), 0.0)


class EmployeeViewsTest(TestCase):
    """Test the Employee CRUD views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.employee = Employee.objects.create(
            name="Test Employee",
            department="Test Department"
        )
    
    def test_employee_list_view(self):
        """Test the employee list view loads correctly."""
        response = self.client.get(reverse('jobs:employee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Employee")
        self.assertContains(response, "Test Department")
    
    def test_employee_list_view_requires_login(self):
        """Test that employee list requires authentication."""
        self.client.logout()
        response = self.client.get(reverse('jobs:employee_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_employee_create_modal(self):
        """Test the employee create modal loads."""
        response = self.client.get(reverse('jobs:employee_create_modal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Employee")
    
    def test_employee_create(self):
        """Test creating a new employee via POST."""
        data = {
            'name': 'New Employee',
            'department': 'New Department'
        }
        response = self.client.post(reverse('jobs:employee_create'), data)
        self.assertEqual(response.status_code, 204)  # Success with HX-Refresh
        self.assertTrue(Employee.objects.filter(name='New Employee').exists())
    
    def test_employee_create_invalid_data(self):
        """Test creating employee with missing required field."""
        data = {
            'department': 'New Department'
            # Missing name field
        }
        response = self.client.post(reverse('jobs:employee_create'), data)
        self.assertEqual(response.status_code, 400)  # Bad request
    
    def test_employee_update_modal(self):
        """Test the employee update modal loads."""
        response = self.client.get(
            reverse('jobs:employee_update_modal', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Employee")
        self.assertContains(response, self.employee.name)
    
    def test_employee_update(self):
        """Test updating an employee via POST."""
        data = {
            'name': 'Updated Employee',
            'department': 'Updated Department'
        }
        response = self.client.post(
            reverse('jobs:employee_update', kwargs={'pk': self.employee.pk}),
            data
        )
        self.assertEqual(response.status_code, 204)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.name, 'Updated Employee')
        self.assertEqual(self.employee.department, 'Updated Department')
    
    def test_employee_delete(self):
        """Test deleting an employee."""
        response = self.client.post(
            reverse('jobs:employee_delete', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to list
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())


class EmployeeSearchAndSortTest(TestCase):
    """Test employee list search and sort functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        
        # Create multiple employees
        Employee.objects.create(name="Alice Johnson", department="Engineering")
        Employee.objects.create(name="Bob Smith", department="Sales")
        Employee.objects.create(name="Charlie Brown", department="Engineering")
    
    def test_employee_search_by_name(self):
        """Test searching employees by name."""
        response = self.client.get(reverse('jobs:employee_list') + '?search=Alice')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice Johnson")
        self.assertNotContains(response, "Bob Smith")
    
    def test_employee_search_by_department(self):
        """Test searching employees by department."""
        response = self.client.get(reverse('jobs:employee_list') + '?search=Sales')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bob Smith")
        self.assertNotContains(response, "Alice Johnson")
    
    def test_employee_list_default_ordering(self):
        """Test that employees are ordered by name by default."""
        response = self.client.get(reverse('jobs:employee_list'))
        self.assertEqual(response.status_code, 200)
        # Check that employees appear in alphabetical order
        content = response.content.decode()
        alice_pos = content.find("Alice Johnson")
        bob_pos = content.find("Bob Smith")
        charlie_pos = content.find("Charlie Brown")
        self.assertLess(alice_pos, bob_pos)
        self.assertLess(bob_pos, charlie_pos)


class EmployeeIntegrationTest(TestCase):
    """Integration tests for the complete employee workflow."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
    
    def test_complete_employee_workflow(self):
        """Test creating, viewing, updating, and deleting an employee."""
        # Create employee
        data = {'name': 'Integration Test Employee', 'department': 'Test Dept'}
        response = self.client.post(reverse('jobs:employee_create'), data)
        self.assertEqual(response.status_code, 204)
        
        # Verify employee exists
        employee = Employee.objects.get(name='Integration Test Employee')
        self.assertIsNotNone(employee)
        
        # View employee in list
        response = self.client.get(reverse('jobs:employee_list'))
        self.assertContains(response, 'Integration Test Employee')
        
        # Update employee
        update_data = {'name': 'Updated Employee', 'department': 'Updated Dept'}
        response = self.client.post(
            reverse('jobs:employee_update', kwargs={'pk': employee.pk}),
            update_data
        )
        self.assertEqual(response.status_code, 204)
        employee.refresh_from_db()
        self.assertEqual(employee.name, 'Updated Employee')
        
        # Delete employee
        response = self.client.post(
            reverse('jobs:employee_delete', kwargs={'pk': employee.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Employee.objects.filter(pk=employee.pk).exists())







