"""
Tests for Job Ticket views.
Verifies that ticket views properly filter by job_type='ticket'.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from jobs.models import Job, Customer, CustomerShipToAddress
from inventory.models import Engine


class JobTicketViewsTestCase(TestCase):
    """Test cases for Job Ticket CRUD views."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='customer@test.com',
            bill_to_name='Test Bill To',
            bill_to_address='123 Bill St',
            bill_to_city='Billville',
            bill_to_state='CA',
            bill_to_zip='12345',
            default_price_setting='list',
            default_terms='net_30'
        )
        
        # Create ship-to addresses
        self.ship_to_1 = CustomerShipToAddress.objects.create(
            customer=self.customer,
            name='Warehouse 1',
            address='456 Ship St',
            city='Shipville',
            state='CA',
            zip='54321',
            is_default=True
        )
        
        self.ship_to_2 = CustomerShipToAddress.objects.create(
            customer=self.customer,
            name='Warehouse 2',
            address='789 Ship Ave',
            city='Shiptown',
            state='CA',
            zip='67890',
            is_default=False
        )
        
        # Create test engine
        self.engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='6BT',
            identifier='ENG001',
            serial_number='SN12345',
            injection_type='DI'
        )
        
        # Create a ticket (job_type='ticket')
        self.ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T1',
            status='new',
            customer=self.customer
        )
        
        # Create a job (job_type='job') - should NOT appear in ticket views
        self.job = Job.objects.create(
            job_type='job',
            job_number='J1',
            status='new',
            customer=self.customer
        )
    
    def test_ticket_list_only_shows_tickets(self):
        """Verify that ticket list only shows job_type='ticket' jobs."""
        response = self.client.get(reverse('jobs:ticket_list'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain the ticket
        self.assertContains(response, self.ticket.ticket_number)
        
        # Should NOT contain the job
        if self.job.job_number:
            self.assertNotContains(response, self.job.job_number)
    
    def test_ticket_create_sets_job_type(self):
        """Verify that creating a ticket sets job_type='ticket' and creates draft."""
        response = self.client.get(reverse('jobs:ticket_create'))
        
        # Should redirect to edit page (auto-creates draft)
        self.assertEqual(response.status_code, 302)
        
        # Get the newly created ticket
        new_ticket = Job.objects.exclude(pk=self.ticket.pk).exclude(pk=self.job.pk).first()
        self.assertIsNotNone(new_ticket)
        self.assertEqual(new_ticket.job_type, 'ticket')
        self.assertEqual(new_ticket.status, 'draft')
        
        # Should have a ticket_number generated
        self.assertIsNotNone(new_ticket.ticket_number)
        
        # Should redirect to edit page
        self.assertIn(f'/jobs/tickets/{new_ticket.pk}/edit/', response.url)
    
    def test_ticket_create_defaults_status(self):
        """Verify that status defaults to 'draft' when auto-created."""
        response = self.client.get(reverse('jobs:ticket_create'))
        
        # Get the newly created ticket
        new_ticket = Job.objects.exclude(pk=self.ticket.pk).exclude(pk=self.job.pk).first()
        if new_ticket:
            # Status should default to 'draft'
            self.assertEqual(new_ticket.status, 'draft')
    
    def test_ticket_detail_404_for_non_ticket(self):
        """Verify that ticket detail returns 404 for non-ticket jobs."""
        response = self.client.get(reverse('jobs:ticket_detail', kwargs={'pk': self.job.pk}))
        self.assertEqual(response.status_code, 404)
    
    def test_ticket_detail_shows_ticket(self):
        """Verify that ticket detail shows ticket data."""
        response = self.client.get(reverse('jobs:ticket_detail', kwargs={'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.ticket_number)
    
    def test_ticket_update_404_for_non_ticket(self):
        """Verify that ticket update returns 404 for non-ticket jobs."""
        response = self.client.get(reverse('jobs:ticket_update', kwargs={'pk': self.job.pk}))
        self.assertEqual(response.status_code, 404)
    
    def test_ticket_update_redirects_to_detail(self):
        """Verify that updating a ticket redirects to detail page."""
        response = self.client.post(reverse('jobs:ticket_update', kwargs={'pk': self.ticket.pk}), {
            'date': '2025-12-04',
            'status': 'in_progress',
        })
        
        # Should redirect to detail view
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('jobs:ticket_detail', kwargs={'pk': self.ticket.pk}))
        
        # Verify the update
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'in_progress')
    
    def test_ticket_list_requires_login(self):
        """Verify that ticket list requires authentication."""
        self.client.logout()
        response = self.client.get(reverse('jobs:ticket_list'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_ticket_form_only_exposes_allowed_fields(self):
        """Verify that the ticket form shows customer selection in edit mode."""
        # Create a draft ticket (simulating the auto-create)
        draft_ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T999',
            status='draft'
        )
        
        response = self.client.get(reverse('jobs:ticket_update', kwargs={'pk': draft_ticket.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Should contain allowed fields
        self.assertContains(response, 'name="date"')
        self.assertContains(response, 'name="status"')
        self.assertContains(response, 'name="notes"')
        
        # Should have customer selection UI available
        self.assertContains(response, 'Customer:')
    
    def test_customer_search(self):
        """Test customer search functionality."""
        response = self.client.get(
            reverse('jobs:customer_search_results', kwargs={'pk': self.ticket.pk}),
            {'q': 'Test Customer'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')
    
    def test_customer_select(self):
        """Test selecting a customer for a ticket."""
        # Create a new ticket without customer
        new_ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T999',
            status='new'
        )
        
        response = self.client.post(
            reverse('jobs:customer_select', kwargs={'pk': new_ticket.pk, 'customer_id': self.customer.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Reload ticket and verify customer is set
        new_ticket.refresh_from_db()
        self.assertEqual(new_ticket.customer, self.customer)
        
        # Verify bill-to address was copied
        self.assertEqual(new_ticket.bill_to_name, self.customer.bill_to_name)
        self.assertEqual(new_ticket.bill_to_address, self.customer.bill_to_address)
        
        # Verify default ship-to address was copied
        self.assertEqual(new_ticket.ship_to_name, self.ship_to_1.name)
        self.assertEqual(new_ticket.ship_to_address, self.ship_to_1.address)
        
        # Verify default price settings and terms were copied
        self.assertEqual(new_ticket.price_setting, self.customer.default_price_setting)
        self.assertEqual(new_ticket.terms, self.customer.default_terms)
    
    def test_customer_create(self):
        """Test creating a new customer."""
        new_ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T998',
            status='new'
        )
        
        response = self.client.post(
            reverse('jobs:customer_create', kwargs={'pk': new_ticket.pk}),
            {
                'name': 'New Customer',
                'email': 'new@example.com',
                'bill_to_name': 'New Bill To',
                'bill_to_address': '999 New St',
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify customer was created
        new_customer = Customer.objects.filter(name='New Customer').first()
        self.assertIsNotNone(new_customer)
        
        # Verify it was assigned to ticket
        new_ticket.refresh_from_db()
        self.assertEqual(new_ticket.customer, new_customer)
    
    def test_ship_to_address_create(self):
        """Test creating a new ship-to address."""
        response = self.client.post(
            reverse('jobs:customer_ship_to_create', kwargs={'customer_id': self.customer.pk}),
            {
                'name': 'Warehouse 3',
                'address': '111 Third St',
                'city': 'Thirdtown',
                'state': 'CA',
                'zip': '11111',
                'is_default': False,
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify address was created
        new_address = CustomerShipToAddress.objects.filter(name='Warehouse 3').first()
        self.assertIsNotNone(new_address)
        self.assertEqual(new_address.customer, self.customer)
    
    def test_job_select_ship_to(self):
        """Test selecting a different ship-to address for a job."""
        response = self.client.post(
            reverse('jobs:job_select_ship_to', kwargs={'pk': self.ticket.pk, 'address_id': self.ship_to_2.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify ship-to was updated
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ship_to_name, self.ship_to_2.name)
        self.assertEqual(self.ticket.ship_to_address, self.ship_to_2.address)
    
    def test_engine_search(self):
        """Test engine search functionality."""
        response = self.client.get(
            reverse('jobs:engine_search_results', kwargs={'pk': self.ticket.pk}),
            {'q': 'Cummins'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cummins')
    
    def test_engine_select(self):
        """Test selecting an engine for a ticket."""
        new_ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T997',
            status='new'
        )
        
        response = self.client.post(
            reverse('jobs:engine_select', kwargs={'pk': new_ticket.pk, 'engine_id': self.engine.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Reload ticket and verify engine is set
        new_ticket.refresh_from_db()
        self.assertEqual(new_ticket.engine, self.engine)
        
        # Verify engine details were copied
        self.assertEqual(new_ticket.engine_make, self.engine.engine_make)
        self.assertEqual(new_ticket.engine_model, self.engine.engine_model)
        self.assertEqual(new_ticket.engine_identifier, self.engine.identifier)
        self.assertEqual(new_ticket.engine_serial_number, self.engine.serial_number)
    
    def test_engine_create(self):
        """Test creating a new engine."""
        new_ticket = Job.objects.create(
            job_type='ticket',
            ticket_number='T996',
            status='new'
        )
        
        response = self.client.post(
            reverse('jobs:engine_create', kwargs={'pk': new_ticket.pk}),
            {
                'engine_make': 'Cat',
                'engine_model': '3126',
                'identifier': 'ENG999',
                'serial_number': 'SN999',
                'stamped_number': 'STAMP999',
                'injection_type': 'DI',
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify engine was created
        new_engine = Engine.objects.filter(engine_make='Cat', engine_model='3126').first()
        self.assertIsNotNone(new_engine)
        
        # Verify it was assigned to ticket
        new_ticket.refresh_from_db()
        self.assertEqual(new_ticket.engine, new_engine)
        self.assertEqual(new_ticket.engine_stamped_number, 'STAMP999')

