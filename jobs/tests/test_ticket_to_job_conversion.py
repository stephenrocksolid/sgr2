from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from jobs.models import (
    Job, Customer, JobComponent, JobSelectionOption, JobSelectedOption,
    JobPart, JobKit, JobKitItem, JobBuildList, JobBuildListItem
)
from inventory.models import Engine, Part, Kit, KitItem, BuildList, BuildListItem

User = get_user_model()


class SequentialNumberingTest(TestCase):
    """Test sequential numbering for tickets and jobs."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
    
    def test_sequential_ticket_numbering(self):
        """Test that tickets get sequential numbers T1, T2, T3, etc."""
        # Create three tickets
        response1 = self.client.get(reverse('jobs:ticket_create'), follow=True)
        ticket1 = Job.objects.filter(job_type='ticket').order_by('pk').first()
        self.assertEqual(ticket1.ticket_number, 'T1')
        
        response2 = self.client.get(reverse('jobs:ticket_create'), follow=True)
        tickets = Job.objects.filter(job_type='ticket').order_by('pk')
        self.assertEqual(tickets.count(), 2)
        ticket2 = tickets[1]
        self.assertEqual(ticket2.ticket_number, 'T2')
        
        response3 = self.client.get(reverse('jobs:ticket_create'), follow=True)
        tickets = Job.objects.filter(job_type='ticket').order_by('pk')
        self.assertEqual(tickets.count(), 3)
        ticket3 = tickets[2]
        self.assertEqual(ticket3.ticket_number, 'T3')
    
    def test_sequential_job_numbering(self):
        """Test that jobs get sequential numbers J1, J2, J3, etc."""
        # Create three jobs directly (not from tickets)
        response1 = self.client.get(reverse('jobs:job_create'), follow=True)
        job1 = Job.objects.filter(job_type='job').order_by('pk').first()
        self.assertEqual(job1.job_number, 'J1')
        
        response2 = self.client.get(reverse('jobs:job_create'), follow=True)
        jobs = Job.objects.filter(job_type='job').order_by('pk')
        self.assertEqual(jobs.count(), 2)
        job2 = jobs[1]
        self.assertEqual(job2.job_number, 'J2')
        
        response3 = self.client.get(reverse('jobs:job_create'), follow=True)
        jobs = Job.objects.filter(job_type='job').order_by('pk')
        self.assertEqual(jobs.count(), 3)
        job3 = jobs[2]
        self.assertEqual(job3.job_number, 'J3')
    
    def test_numbering_independent(self):
        """Test that ticket and job numbers are independent."""
        # Create T1
        self.client.get(reverse('jobs:ticket_create'))
        ticket1 = Job.objects.filter(job_type='ticket').order_by('pk').first()
        self.assertEqual(ticket1.ticket_number, 'T1')
        
        # Convert T1 to J1
        response = self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket1.pk})
        )
        ticket1.refresh_from_db()
        self.assertEqual(ticket1.job_type, 'job')
        self.assertEqual(ticket1.ticket_number, 'T1')
        self.assertEqual(ticket1.job_number, 'J1')
        
        # Create T2 (should still be T2 even though T1 was converted)
        self.client.get(reverse('jobs:ticket_create'))
        tickets = Job.objects.filter(job_type='ticket').order_by('pk')
        ticket2 = tickets.first()  # Get the only remaining ticket
        self.assertEqual(ticket2.ticket_number, 'T2')
        
        # Convert T2 to J2
        response = self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket2.pk})
        )
        ticket2.refresh_from_db()
        self.assertEqual(ticket2.job_number, 'J2')


class TicketToJobConversionTest(TestCase):
    """Test converting tickets to jobs."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # Create a customer
        self.customer = Customer.objects.create(name='Test Customer')
        
        # Create an engine
        self.engine = Engine.objects.create(
            engine_make='Cummins',
            engine_model='ISX15'
        )
    
    def test_convert_ticket_to_job_basic(self):
        """Test basic ticket to job conversion."""
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Convert to job
        response = self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk}),
            follow=True
        )
        
        # Refresh from DB
        ticket.refresh_from_db()
        
        # Verify conversion
        self.assertEqual(ticket.job_type, 'job')
        self.assertEqual(ticket.status, 'quote')
        self.assertEqual(ticket.ticket_number, 'T1')
        self.assertEqual(ticket.job_number, 'J1')
        
        # Verify redirect to job edit page
        self.assertRedirects(response, reverse('jobs:job_detail', kwargs={'pk': ticket.pk}))
    
    def test_convert_preserves_ticket_data(self):
        """Test that conversion preserves customer, engine, notes, dates."""
        # Create a ticket with data
        ticket = Job.objects.create(
            job_type='ticket',
            status='new',
            date=timezone.now().date(),
            customer=self.customer,
            engine=self.engine,
            engine_make='Cummins',
            engine_model='ISX15',
            notes='Test notes',
            customer_po='PO123'
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Convert to job
        self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Refresh from DB
        ticket.refresh_from_db()
        
        # Verify data preserved
        self.assertEqual(ticket.customer, self.customer)
        self.assertEqual(ticket.engine, self.engine)
        self.assertEqual(ticket.engine_make, 'Cummins')
        self.assertEqual(ticket.engine_model, 'ISX15')
        self.assertEqual(ticket.notes, 'Test notes')
        self.assertEqual(ticket.customer_po, 'PO123')
    
    def test_convert_copies_part_selections(self):
        """Test that conversion copies Part selections to JobPart."""
        # Create a part
        part = Part.objects.create(
            name='Test Part',
            part_number='P123'
        )
        
        # Create selection option
        option = JobSelectionOption.objects.create(
            name='Part Option',
            group='parts_selection',
            part=part
        )
        
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Select the option
        JobSelectedOption.objects.create(job=ticket, option=option)
        
        # Convert to job
        self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Verify JobPart created
        job_parts = JobPart.objects.filter(job=ticket)
        self.assertEqual(job_parts.count(), 1)
        job_part = job_parts.first()
        self.assertEqual(job_part.source_part, part)
        self.assertEqual(job_part.part_number, 'P123')
        self.assertEqual(job_part.name, 'Test Part')
        self.assertEqual(job_part.quantity, 1)
    
    def test_convert_copies_kit_selections(self):
        """Test that conversion copies Kit selections with all KitItems."""
        # Create a part and kit
        part = Part.objects.create(name='Kit Part', part_number='KP1')
        kit = Kit.objects.create(name='Test Kit')
        kit_item = KitItem.objects.create(
            kit=kit,
            part=part,
            quantity=5
        )
        
        # Create selection option
        option = JobSelectionOption.objects.create(
            name='Kit Option',
            group='item_selection',
            kit=kit
        )
        
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Select the option
        JobSelectedOption.objects.create(job=ticket, option=option)
        
        # Convert to job
        self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Verify JobKit created
        job_kits = JobKit.objects.filter(job=ticket)
        self.assertEqual(job_kits.count(), 1)
        job_kit = job_kits.first()
        self.assertEqual(job_kit.source_kit, kit)
        self.assertEqual(job_kit.name, 'Test Kit')
        
        # Verify JobKitItem created
        job_kit_items = JobKitItem.objects.filter(job_kit=job_kit)
        self.assertEqual(job_kit_items.count(), 1)
        job_kit_item = job_kit_items.first()
        self.assertEqual(job_kit_item.source_kit_item, kit_item)
        self.assertEqual(job_kit_item.part, part)
        self.assertEqual(job_kit_item.quantity, 5)
    
    def test_convert_copies_buildlist_selections(self):
        """Test that conversion copies BuildList selections with all items."""
        # Create a build list
        build_list = BuildList.objects.create(name='Test Build List')
        bl_item = BuildListItem.objects.create(
            build_list=build_list,
            name='Build Item 1',
            description='Test description',
            hour_qty=2.5
        )
        
        # Create selection option
        option = JobSelectionOption.objects.create(
            name='BuildList Option',
            group='block_build_lists',
            build_list=build_list
        )
        
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Select the option
        JobSelectedOption.objects.create(job=ticket, option=option)
        
        # Convert to job
        self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Verify JobBuildList created
        job_build_lists = JobBuildList.objects.filter(job=ticket)
        self.assertEqual(job_build_lists.count(), 1)
        job_build_list = job_build_lists.first()
        self.assertEqual(job_build_list.source_build_list, build_list)
        self.assertEqual(job_build_list.name, 'Test Build List')
        
        # Verify JobBuildListItem created
        job_bl_items = JobBuildListItem.objects.filter(job_build_list=job_build_list)
        self.assertEqual(job_bl_items.count(), 1)
        job_bl_item = job_bl_items.first()
        self.assertEqual(job_bl_item.source_build_list_item, bl_item)
        self.assertEqual(job_bl_item.name, 'Build Item 1')
        self.assertEqual(job_bl_item.estimated_hours, 2.5)
    
    def test_convert_copies_all_selection_types(self):
        """Test conversion with mix of Parts, Kits, and BuildLists."""
        # Create all types
        part = Part.objects.create(name='Test Part', part_number='P1')
        kit = Kit.objects.create(name='Test Kit')
        build_list = BuildList.objects.create(name='Test BuildList')
        
        # Create options
        part_option = JobSelectionOption.objects.create(
            name='Part Option', group='parts_selection', part=part
        )
        kit_option = JobSelectionOption.objects.create(
            name='Kit Option', group='item_selection', kit=kit
        )
        bl_option = JobSelectionOption.objects.create(
            name='BuildList Option', group='block_build_lists', build_list=build_list
        )
        
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Select all options
        JobSelectedOption.objects.create(job=ticket, option=part_option)
        JobSelectedOption.objects.create(job=ticket, option=kit_option)
        JobSelectedOption.objects.create(job=ticket, option=bl_option)
        
        # Convert to job
        self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Verify all copied
        self.assertEqual(JobPart.objects.filter(job=ticket).count(), 1)
        self.assertEqual(JobKit.objects.filter(job=ticket).count(), 1)
        self.assertEqual(JobBuildList.objects.filter(job=ticket).count(), 1)
    
    def test_convert_preserves_component_data(self):
        """Test that JobComponent data is preserved."""
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Create component with data
        component = JobComponent.objects.create(
            job=ticket,
            block=True,
            head=True,
            crankshaft=False,
            rods_qty=8
        )
        
        # Convert to job
        self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Verify component still exists and has same data
        component.refresh_from_db()
        self.assertEqual(component.job, ticket)
        self.assertTrue(component.block)
        self.assertTrue(component.head)
        self.assertFalse(component.crankshaft)
        self.assertEqual(component.rods_qty, 8)
    
    def test_cannot_convert_job_to_job(self):
        """Test that trying to convert an already-converted job does nothing."""
        # Create a job (not ticket)
        job = Job.objects.create(
            job_type='job',
            status='quote',
            date=timezone.now().date()
        )
        job.job_number = 'J1'
        job.save()
        
        # Try to convert
        response = self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': job.pk}),
            follow=True
        )
        
        # Should redirect to job detail (not create a new job)
        job.refresh_from_db()
        self.assertEqual(job.job_type, 'job')
        self.assertEqual(job.job_number, 'J1')
    
    def test_convert_redirects_to_job_edit(self):
        """Test that conversion redirects to job edit page."""
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        # Convert to job
        response = self.client.post(
            reverse('jobs:create_job_from_ticket', kwargs={'pk': ticket.pk})
        )
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('jobs:job_detail', kwargs={'pk': ticket.pk})
        )
    
    def test_job_delete(self):
        """Test that a job can be deleted."""
        # Create a job
        job = Job.objects.create(
            job_type='job',
            status='quote',
            date=timezone.now().date()
        )
        job.job_number = 'J1'
        job.save()
        
        job_pk = job.pk
        
        # Delete the job
        response = self.client.post(
            reverse('jobs:job_delete', kwargs={'pk': job_pk})
        )
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('jobs:job_list'))
        
        # Verify job is deleted
        self.assertFalse(Job.objects.filter(pk=job_pk).exists())
    
    def test_ticket_delete(self):
        """Test that a ticket can be deleted."""
        # Create a ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        ticket.ticket_number = 'T1'
        ticket.save()
        
        ticket_pk = ticket.pk
        
        # Delete the ticket
        response = self.client.post(
            reverse('jobs:ticket_delete', kwargs={'pk': ticket_pk})
        )
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('jobs:ticket_list'))
        
        # Verify ticket is deleted
        self.assertFalse(Job.objects.filter(pk=ticket_pk).exists())

