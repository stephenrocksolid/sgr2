from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from jobs.models import Job, JobComponent, Employee, JobEmployee
from inventory.models import Engine

User = get_user_model()


class JobModelTest(TestCase):
    """Test Job model enhancements."""
    
    def test_job_status_choices_include_job_statuses(self):
        """Test that status choices include quote, wo, invoice."""
        status_values = [choice[0] for choice in Job.STATUS_CHOICES]
        self.assertIn('quote', status_values)
        self.assertIn('wo', status_values)
        self.assertIn('invoice', status_values)
    
    def test_can_create_job_with_quote_status(self):
        """Test creating a job with quote status."""
        job = Job.objects.create(
            job_type='job',
            job_number='J999',
            status='quote',
            date=timezone.now().date()
        )
        self.assertEqual(job.status, 'quote')
        self.assertEqual(job.job_type, 'job')
    
    def test_can_create_job_with_wo_status(self):
        """Test creating a job with WO status."""
        job = Job.objects.create(
            job_type='job',
            job_number='J998',
            status='wo',
            date=timezone.now().date()
        )
        self.assertEqual(job.status, 'wo')
    
    def test_can_create_job_with_invoice_status(self):
        """Test creating a job with invoice status."""
        job = Job.objects.create(
            job_type='job',
            job_number='J997',
            status='invoice',
            date=timezone.now().date()
        )
        self.assertEqual(job.status, 'invoice')


class JobViewsTest(TestCase):
    """Test the Job views."""
    
    def setUp(self):
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
            status='quote',
            date=timezone.now().date()
        )
        
        # Create component info
        self.component = JobComponent.objects.create(
            job=self.job,
            block=True,
            head=True,
            pistons=True
        )
    
    def test_job_list_view(self):
        """Test the job list view loads correctly."""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.job_number)
    
    def test_job_list_view_requires_login(self):
        """Test that job list requires authentication."""
        self.client.logout()
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_job_list_only_shows_jobs_not_tickets(self):
        """Test that job list only shows jobs, not tickets."""
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T001',
            status='new',
            date=timezone.now().date()
        )
        
        response = self.client.get(reverse('jobs:job_list'))
        self.assertContains(response, self.job.job_number)
        self.assertNotContains(response, ticket.ticket_number)
    
    def test_job_detail_view(self):
        """Test the job detail view loads correctly."""
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.job_number)
        self.assertContains(response, "Status & Dates")
        self.assertContains(response, "Engine Information")
    
    def test_job_detail_shows_progress_section(self):
        """Test that job detail shows progress section."""
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        self.assertContains(response, "Progress")
    
    def test_job_detail_shows_assigned_employees(self):
        """Test that job detail shows assigned employees section."""
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        self.assertContains(response, "Assigned To")
        self.assertContains(response, "Employee Name")
        self.assertContains(response, "Calculated Total Time")
    
    def test_job_create_redirects(self):
        """Test that job create creates a job and redirects to edit."""
        initial_count = Job.objects.filter(job_type='job').count()
        response = self.client.get(reverse('jobs:job_create'))
        self.assertEqual(response.status_code, 302)  # Redirect to edit
        # Check that a new job was created
        new_count = Job.objects.filter(job_type='job').count()
        self.assertEqual(new_count, initial_count + 1)
    
    def test_job_create_assigns_job_number(self):
        """Test that job create assigns a job number."""
        response = self.client.get(reverse('jobs:job_create'))
        # Get the newest job
        job = Job.objects.filter(job_type='job').latest('created_at')
        self.assertIsNotNone(job.job_number)
        self.assertTrue(job.job_number.startswith('J'))


class JobListColumnsTest(TestCase):
    """Test that job list displays all required columns."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        
        # Create engine
        self.engine = Engine.objects.create(
            engine_make="TestMake",
            engine_model="TestModel",
            cylinder=6,
            valves_per_cyl=2
        )
        
        # Create job with engine
        self.job = Job.objects.create(
            job_type='job',
            job_number='J001',
            status='wo',
            date=timezone.now().date(),
            finish_date=timezone.now().date(),
            engine=self.engine,
            engine_make="TestMake",
            engine_model="TestModel"
        )
        
        # Create component
        self.component = JobComponent.objects.create(
            job=self.job,
            block=True,
            head=True,
            crankshaft=True
        )
    
    def test_job_list_displays_required_columns(self):
        """Test that job list displays all required column headers."""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check for column headers
        required_headers = [
            'ID', 'Customer', 'Engine Make & Model', '# of Cyl', '# of Valves',
            'Head', 'Block', 'Rods', 'Crank', 'Main brg.', 'Piston',
            'Size', 'Parts', 'Week', 'Finish', 'Date', 'Complete'
        ]
        for header in required_headers:
            self.assertContains(response, header)
    
    def test_job_list_displays_job_data(self):
        """Test that job list displays job data correctly."""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertContains(response, 'J001')
        self.assertContains(response, 'TestMake')
        self.assertContains(response, 'TestModel')
    
    def test_job_list_displays_checkmarks_for_components(self):
        """Test that job list shows checkmarks for selected components."""
        response = self.client.get(reverse('jobs:job_list'))
        # The checkmark character should appear in the table
        self.assertContains(response, '✓')


class URLPatternTest(TestCase):
    """Test that URL patterns are correctly configured."""
    
    def test_home_url(self):
        """Test that home is at /jobs/home/."""
        url = reverse('jobs:home')
        self.assertEqual(url, '/jobs/home/')
    
    def test_job_list_at_root(self):
        """Test that job list is at /jobs/."""
        url = reverse('jobs:job_list')
        self.assertEqual(url, '/jobs/')
    
    def test_job_ticket_list_url(self):
        """Test that job ticket list is at /jobs/tickets/."""
        url = reverse('jobs:ticket_list')
        self.assertEqual(url, '/jobs/tickets/')
    
    def test_employee_urls_configured(self):
        """Test that all employee URLs are configured."""
        urls = [
            'jobs:employee_list',
            'jobs:employee_create_modal',
            'jobs:employee_create',
        ]
        for url_name in urls:
            url = reverse(url_name)
            self.assertIsNotNone(url)
    
    def test_job_urls_configured(self):
        """Test that all job URLs are configured."""
        url = reverse('jobs:job_list')
        self.assertEqual(url, '/jobs/')
        
        url = reverse('jobs:job_create')
        self.assertEqual(url, '/jobs/new/')
        
        # Test parametrized URLs - job_detail is now the combined view/edit page
        url = reverse('jobs:job_detail', kwargs={'pk': 1})
        self.assertEqual(url, '/jobs/1/')


class JobComponentProgressTest(TestCase):
    """Test that job detail shows progress for selected components."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        
        self.job = Job.objects.create(
            job_type='job',
            job_number='J001',
            status='wo',
            date=timezone.now().date()
        )
        
        # Create component with some selected and some done
        self.component = JobComponent.objects.create(
            job=self.job,
            block=True,
            block_done=True,
            head=True,
            head_done=False,
            pistons=False  # Not selected, should not show
        )
    
    def test_job_detail_shows_progress(self):
        """Test that job detail shows progress section."""
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Progress")
    
    def test_progress_shows_done_checkmark(self):
        """Test that completed components show checkmark."""
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        # Block is done, should show checkmark
        self.assertContains(response, "Block")
        self.assertContains(response, "✓")
    
    def test_progress_shows_incomplete_circle(self):
        """Test that incomplete components show circle."""
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        # Head is not done, should show circle
        self.assertContains(response, "Head")
        self.assertContains(response, "○")


class JobEmployeeIntegrationTest(TestCase):
    """Integration tests for Job with Employees."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        
        self.employee = Employee.objects.create(name="Test Mechanic", department="Shop")
        self.job = Job.objects.create(
            job_type='job',
            job_number='J100',
            status='wo',
            date=timezone.now().date()
        )
    
    def test_assign_employee_to_job(self):
        """Test assigning an employee to a job."""
        job_emp = JobEmployee.objects.create(
            job=self.job,
            employee=self.employee,
            calculated_total_time=5.5
        )
        
        # Check relationship
        self.assertEqual(self.job.job_employees.count(), 1)
        self.assertEqual(self.job.job_employees.first().employee, self.employee)
    
    def test_job_detail_shows_assigned_employee(self):
        """Test that job detail shows assigned employees."""
        JobEmployee.objects.create(
            job=self.job,
            employee=self.employee,
            calculated_total_time=8.0
        )
        
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.job.pk}))
        self.assertContains(response, self.employee.name)
        self.assertContains(response, "8")  # Time worked


class JobIntegrationTest(TestCase):
    """Integration tests for the complete job workflow."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
    
    def test_complete_job_workflow(self):
        """Test creating and viewing a job."""
        # Create job via the create endpoint
        response = self.client.get(reverse('jobs:job_create'))
        self.assertEqual(response.status_code, 302)  # Redirects to edit
        
        # Get the created job
        job = Job.objects.filter(job_type='job').latest('created_at')
        self.assertIsNotNone(job.job_number)
        self.assertEqual(job.status, 'quote')  # Default status
        
        # View job detail
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, job.job_number)
        
        # View job in list
        response = self.client.get(reverse('jobs:job_list'))
        self.assertContains(response, job.job_number)
    
    def test_job_search_functionality(self):
        """Test searching jobs in the list."""
        # Create multiple jobs
        job1 = Job.objects.create(
            job_type='job',
            job_number='J200',
            status='quote',
            date=timezone.now().date()
        )
        job2 = Job.objects.create(
            job_type='job',
            job_number='J201',
            status='wo',
            date=timezone.now().date()
        )
        
        # Search by job number
        response = self.client.get(reverse('jobs:job_list') + '?search=J200')
        self.assertContains(response, 'J200')

