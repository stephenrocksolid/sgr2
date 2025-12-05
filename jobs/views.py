from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, View
from django.urls import reverse, reverse_lazy
from django.http import Http404, HttpResponse, JsonResponse
from django.db.models import Q, Sum, Count, F
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from django.contrib.auth.models import User
from .models import Job, Customer, CustomerShipToAddress, JobComponent, JobSelectionOption, JobSelectedOption, JobEmployee, JobBuildList, JobBuildListItem, JobKit, JobKitItem, JobPart, JobAttachment, JobTime, PurchaseOrder, PurchaseOrderItem, PurchaseOrderReceiving, PurchaseOrderAttachment
from .forms import JobTicketForm, CustomerForm, CustomerShipToAddressForm, EngineQuickCreateForm, JobComponentForm, JobSelectionOptionForm, TimeEntryForm, PurchaseOrderForm
from inventory.models import Engine, Vendor, VendorContact, Part
import re
from decimal import Decimal


# ===================================
# Helper Functions for Sequential Numbering
# ===================================

def get_next_ticket_number():
    """Generate next sequential ticket number (T1, T2, T3, ...)."""
    # Get all ticket numbers (from any job, even if converted to job type)
    tickets = Job.objects.filter(
        ticket_number__isnull=False
    ).exclude(ticket_number='').values_list('ticket_number', flat=True)
    
    if not tickets:
        return 'T1'
    
    # Extract numbers and find max
    max_num = 0
    for ticket_num in tickets:
        match = re.search(r'\d+', ticket_num)
        if match:
            num = int(match.group())
            max_num = max(max_num, num)
    
    return f'T{max_num + 1}'


def get_next_job_number():
    """Generate next sequential job number (J1, J2, J3, ...)."""
    # Get all job numbers for jobs
    jobs = Job.objects.filter(
        job_type='job',
        job_number__isnull=False
    ).exclude(job_number='').values_list('job_number', flat=True)
    
    if not jobs:
        return 'J1'
    
    # Extract numbers and find max
    max_num = 0
    for job_num in jobs:
        match = re.search(r'\d+', job_num)
        if match:
            num = int(match.group())
            max_num = max(max_num, num)
    
    return f'J{max_num + 1}'


def get_next_po_number():
    """Generate next sequential PO number (PO-0001, PO-0002, ...)."""
    # Get all PO numbers
    pos = PurchaseOrder.objects.filter(
        po_number__isnull=False
    ).exclude(po_number='').values_list('po_number', flat=True)
    
    if not pos:
        return 'PO-0001'
    
    # Extract numbers and find max
    max_num = 0
    for po_num in pos:
        match = re.search(r'\d+', po_num)
        if match:
            num = int(match.group())
            max_num = max(max_num, num)
    
    return f'PO-{max_num + 1:04d}'


@login_required
def home(request):
    """
    Main home view for the jobs app.
    Displays KPIs, recent jobs, notifications, and quick actions.
    """
    from datetime import timedelta
    from .models import JobNotification
    
    # Use localdate() to get the date in the configured timezone (America/New_York)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())  # Monday
    
    # ===== KPI Stats =====
    # Total active jobs (not cancelled/completed)
    total_active_jobs = Job.objects.filter(job_type='job').exclude(
        status__in=['completed', 'cancelled']
    ).count()
    
    # Jobs in progress
    jobs_in_progress = Job.objects.filter(
        job_type='job', 
        status='in_progress'
    ).count()
    
    # Jobs completed this week
    jobs_completed_week = Job.objects.filter(
        job_type='job',
        status='completed',
        updated_at__date__gte=week_start
    ).count()
    
    # Total hours logged this week
    hours_this_week = JobTime.objects.filter(
        start_time__date__gte=week_start,
        end_time__isnull=False
    ).aggregate(
        total_hours=Sum(
            (F('end_time') - F('start_time'))
        )
    )['total_hours']
    
    # Convert timedelta to hours
    if hours_this_week:
        hours_this_week = round(hours_this_week.total_seconds() / 3600, 1)
    else:
        hours_this_week = 0
    
    # Pending tickets count
    pending_tickets = Job.objects.filter(
        job_type='ticket',
        status__in=['new', 'draft']
    ).count()
    
    # ===== Jobs by Status =====
    jobs_by_status = Job.objects.filter(job_type='job').exclude(
        status__isnull=True
    ).values('status').annotate(count=Count('id')).order_by('status')
    
    status_labels = {
        'draft': 'Draft',
        'new': 'New',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'quote': 'Quote',
        'wo': 'Work Order',
        'invoice': 'Invoice',
    }
    
    status_colors = {
        'draft': '#9CA3AF',
        'new': '#3B82F6',
        'in_progress': '#F59E0B',
        'completed': '#10B981',
        'cancelled': '#EF4444',
        'quote': '#8B5CF6',
        'wo': '#06B6D4',
        'invoice': '#6366F1',
    }
    
    jobs_status_data = [
        {
            'status': item['status'],
            'label': status_labels.get(item['status'], item['status']),
            'count': item['count'],
            'color': status_colors.get(item['status'], '#6B7280'),
        }
        for item in jobs_by_status
    ]
    
    # ===== Recent Jobs =====
    recent_jobs = Job.objects.filter(job_type='job').select_related(
        'customer', 'engine'
    ).order_by('-updated_at')[:8]
    
    # ===== Today's Work Orders =====
    todays_jobs = Job.objects.filter(
        job_type='job',
        status__in=['in_progress', 'wo']
    ).select_related('customer', 'component_info').order_by('-updated_at')[:5]
    
    # ===== Active Time Entry =====
    active_time_entry = JobTime.objects.filter(
        user=request.user,
        end_time__isnull=True
    ).select_related('job', 'job_build_list', 'job_build_list_item').first()
    
    # ===== Pending POs =====
    pending_pos = PurchaseOrder.objects.filter(
        status__in=['draft', 'submitted', 'partially_received']
    ).select_related('vendor').order_by('-po_date')[:5]
    
    pending_pos_count = PurchaseOrder.objects.filter(
        status__in=['draft', 'submitted', 'partially_received']
    ).count()
    
    # ===== Notifications =====
    show_filter = request.GET.get('show', 'unread')
    
    notifications_query = JobNotification.objects.filter(
        user=request.user
    ).select_related('job', 'created_by')
    
    if show_filter == 'unread':
        notifications = notifications_query.filter(read_at__isnull=True)[:10]
    else:
        notifications = notifications_query[:10]
    
    unread_count = JobNotification.objects.filter(
        user=request.user, 
        read_at__isnull=True
    ).count()
    
    # ===== User's Assigned Jobs (Daily Report) =====
    # Show only jobs with WO status where user is a JobEmployee
    my_jobs = Job.objects.filter(
        job_employees__user=request.user,
        job_type='job',
        status='wo'
    ).select_related(
        'customer', 'component_info'
    ).distinct().order_by('-updated_at')[:10]
    
    context = {
        # KPIs
        'total_active_jobs': total_active_jobs,
        'jobs_in_progress': jobs_in_progress,
        'jobs_completed_week': jobs_completed_week,
        'hours_this_week': hours_this_week,
        'pending_tickets': pending_tickets,
        'pending_pos_count': pending_pos_count,
        
        # Jobs data
        'jobs_status_data': jobs_status_data,
        'recent_jobs': recent_jobs,
        'todays_jobs': todays_jobs,
        'my_jobs': my_jobs,
        
        # Time tracking
        'active_time_entry': active_time_entry,
        
        # Purchase orders
        'pending_pos': pending_pos,
        
        # Notifications
        'notifications': notifications,
        'unread_count': unread_count,
        'show_filter': show_filter,
        
        # Date info
        'today': today,
        'week_start': week_start,
    }
    return render(request, 'jobs/home.html', context)


@login_required
def job_ticket_list(request):
    """List all job tickets with search, sorting, and status filtering."""
    from core.view_utils import get_list_context
    
    # Base queryset - only tickets
    tickets = Job.objects.filter(job_type='ticket').select_related(
        'customer', 'sales_person', 'engine', 'component_info'
    )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    # Get list context with search, sort, and pagination
    context = get_list_context(
        queryset=tickets,
        request=request,
        search_fields=['ticket_number', 'customer__name', 'engine_make', 'engine_model'],
        sort_fields={
            'ticket_number', '-ticket_number',
            'date', '-date',
            'customer__name', '-customer__name',
            'status', '-status',
            'store', '-store',
            'sales_person__username', '-sales_person__username'
        },
        default_sort=['-date', '-id'],
        per_page=50
    )
    
    # Add tickets to context for template compatibility
    context['tickets'] = context['object_list']
    
    # Calculate stats (from all tickets, not filtered)
    all_tickets = Job.objects.filter(job_type='ticket')
    context['stats'] = {
        'draft': all_tickets.filter(status='draft').count(),
        'ready_for_review': all_tickets.filter(status='ready_for_review').count(),
    }
    
    # Add status filter to context
    context['status_filter'] = status_filter
    
    context['create_url'] = reverse_lazy('jobs:ticket_create')
    context['create_label'] = 'New Job Ticket'
    
    return render(request, 'jobs/ticket_list.html', context)


class JobTicketCreateView(LoginRequiredMixin, View):
    """Create a new job ticket - auto-creates a draft and redirects to edit."""
    
    def get(self, request):
        """Create a draft ticket and redirect to edit page."""
        # Create a minimal draft ticket
        ticket = Job.objects.create(
            job_type='ticket',
            status='draft',
            date=timezone.now().date()
        )
        
        # Generate ticket number
        ticket.ticket_number = get_next_ticket_number()
        ticket.save(update_fields=['ticket_number'])
        
        # Redirect to edit page where customer selection is available
        return redirect('jobs:ticket_detail', pk=ticket.pk)


class JobTicketUpdateView(LoginRequiredMixin, UpdateView):
    """Combined view/edit page for a job ticket (always editable)."""
    model = Job
    form_class = JobTicketForm
    template_name = 'jobs/ticket_form.html'
    
    def get_queryset(self):
        """Filter to show tickets or jobs that have a ticket_number (originated from tickets)."""
        return Job.objects.filter(Q(job_type='ticket') | Q(ticket_number__isnull=False))
    
    def get_object(self, queryset=None):
        """Get the object and ensure it's a ticket or has a ticket_number (404 if not)."""
        obj = super().get_object(queryset)
        if obj.job_type != 'ticket' and not obj.ticket_number:
            raise Http404("Job ticket not found")
        return obj
    
    def get_success_url(self):
        """Redirect to ticket list after successful update."""
        return reverse_lazy('jobs:ticket_list')
    
    def get_context_data(self, **kwargs):
        """Add context for the template."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Job Ticket'
        context['is_create'] = False
        
        # Get or create JobComponent for this ticket
        component, created = JobComponent.objects.get_or_create(job=self.object)
        
        # Add component form to context
        if self.request.POST:
            context['component_form'] = JobComponentForm(self.request.POST, instance=component)
        else:
            context['component_form'] = JobComponentForm(instance=component)
        
        # Get all active selection options grouped by category
        context['parts_selection_options'] = JobSelectionOption.objects.filter(
            group='parts_selection', is_active=True
        ).order_by('sort_order', 'name')
        context['block_build_lists_options'] = JobSelectionOption.objects.filter(
            group='block_build_lists', is_active=True
        ).order_by('sort_order', 'name')
        context['head_build_lists_options'] = JobSelectionOption.objects.filter(
            group='head_build_lists', is_active=True
        ).order_by('sort_order', 'name')
        context['item_selection_options'] = JobSelectionOption.objects.filter(
            group='item_selection', is_active=True
        ).order_by('sort_order', 'name')
        
        # Get currently selected option IDs for this job
        context['selected_option_ids'] = set(
            self.object.selected_options.values_list('option_id', flat=True)
        )
        
        return context
    
    def form_valid(self, form):
        """Save both the ticket and component forms."""
        context = self.get_context_data()
        component_form = context['component_form']
        
        if component_form.is_valid():
            # Save the ticket first
            self.object = form.save()
            
            # Save the component form
            component = component_form.save(commit=False)
            component.job = self.object
            component.save()
            
            # Handle job selections
            # Get all option IDs from checkboxes
            selected_option_ids = self.request.POST.getlist('job_selections')
            selected_option_ids = [int(id) for id in selected_option_ids]
            
            # Get existing selections
            existing_selections = set(
                self.object.selected_options.values_list('option_id', flat=True)
            )
            
            # Determine which to add and which to remove
            to_add = set(selected_option_ids) - existing_selections
            to_remove = existing_selections - set(selected_option_ids)
            
            # Remove unselected options
            if to_remove:
                JobSelectedOption.objects.filter(
                    job=self.object,
                    option_id__in=to_remove
                ).delete()
            
            # Add newly selected options
            for option_id in to_add:
                JobSelectedOption.objects.create(
                    job=self.object,
                    option_id=option_id
                )
            
            return redirect(self.get_success_url())
        else:
            # If component form is invalid, re-render with errors
            return self.render_to_response(self.get_context_data(form=form))


@login_required
@require_http_methods(["POST"])
def ticket_delete(request, pk):
    """Delete a job ticket."""
    ticket = get_object_or_404(Job, pk=pk, job_type='ticket')
    ticket.delete()
    return redirect('jobs:ticket_list')


# ===================================
# Ticket to Job Conversion
# ===================================

@login_required
@require_http_methods(["POST"])
def create_job_from_ticket(request, pk):
    """
    Convert a ticket to a job by:
    - Changing job_type from 'ticket' to 'job'
    - Setting status to 'quote'
    - Generating a new job_number
    - Keeping the existing ticket_number
    - Copying selected options (Parts/Kits/BuildLists) to job tables
    """
    from inventory.models import BuildList, Kit, Part, BuildListItem, KitItem
    from .models import JobBuildListItem, JobKitItem
    
    # Get the ticket and validate
    ticket = get_object_or_404(Job, pk=pk)
    
    if ticket.job_type != 'ticket':
        # Already converted or is a job
        return redirect('jobs:job_detail', pk=ticket.pk)
    
    with transaction.atomic():
        # Convert ticket to job
        ticket.job_type = 'job'
        ticket.status = 'quote'
        
        # Keep existing ticket_number, generate new job_number
        ticket.job_number = get_next_job_number()
        ticket.save()
        
        # Process selected options and copy to job tables
        selected_options = ticket.selected_options.select_related(
            'option__part', 'option__kit', 'option__build_list'
        ).all()
        
        for selected_option in selected_options:
            option = selected_option.option
            
            # Copy Part selections
            if option.part:
                part = option.part
                JobPart.objects.create(
                    job=ticket,
                    source_part=part,
                    part_number=part.part_number,
                    name=part.name,
                    quantity=1,
                    notes='',
                    selected=False
                )
            
            # Copy Kit selections with all kit items
            if option.kit:
                kit = option.kit
                job_kit = JobKit.objects.create(
                    job=ticket,
                    source_kit=kit,
                    name=kit.name,
                    notes='',
                    is_selected=False
                )
                
                # Copy all kit items
                kit_items = KitItem.objects.filter(kit=kit).select_related('part')
                for idx, kit_item in enumerate(kit_items, start=1):
                    JobKitItem.objects.create(
                        job_kit=job_kit,
                        source_kit_item=kit_item,
                        part=kit_item.part,
                        part_number=kit_item.part.part_number if kit_item.part else '',
                        name=kit_item.part.name if kit_item.part else '',
                        quantity=kit_item.quantity,
                        sort_order=idx,
                        on_job=True,
                        is_complete=False
                    )
            
            # Copy BuildList selections with all build list items
            if option.build_list:
                build_list = option.build_list
                job_build_list = JobBuildList.objects.create(
                    job=ticket,
                    source_build_list=build_list,
                    name=build_list.name,
                    notes=build_list.notes if hasattr(build_list, 'notes') else '',
                    selected=False
                )
                
                # Copy all build list items
                build_list_items = BuildListItem.objects.filter(build_list=build_list)
                for idx, bl_item in enumerate(build_list_items, start=1):
                    JobBuildListItem.objects.create(
                        job_build_list=job_build_list,
                        source_build_list_item=bl_item,
                        name=bl_item.name,
                        description=bl_item.description,
                        estimated_hours=bl_item.hour_qty,
                        sort_order=idx,
                        on_job=True,
                        is_complete=False
                    )
        
        # JobComponent and JobSelectedOptions already exist on the same record
        # so no need to copy them - they're automatically preserved
    
    # Redirect to job edit page
    return redirect('jobs:job_detail', pk=ticket.pk)


# Customer Search & Selection Views

@login_required
@require_http_methods(["GET"])
def customer_search_modal(request, pk):
    """Render the customer search modal for a ticket or job."""
    job = get_object_or_404(Job, pk=pk)
    context = {
        'ticket': job,  # Using 'ticket' name for template compatibility
    }
    return render(request, 'jobs/partials/customer_search_modal.html', context)


@login_required
@require_http_methods(["GET"])
def customer_search_results(request, pk):
    """HTMX endpoint returning filtered customers."""
    job = get_object_or_404(Job, pk=pk)
    query = request.GET.get('q', '').strip()
    
    customers = Customer.objects.all().order_by('name')
    
    if query:
        # Search across name, email, phone, and all address fields
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(bill_to_name__icontains=query) |
            Q(bill_to_address__icontains=query) |
            Q(bill_to_city__icontains=query) |
            Q(bill_to_state__icontains=query) |
            Q(bill_to_zip__icontains=query)
        ).distinct()
    
    context = {
        'ticket': job,  # Using 'ticket' name for template compatibility
        'customers': customers[:50],  # Limit to 50 results
        'query': query,
    }
    return render(request, 'jobs/partials/customer_search_results.html', context)


@login_required
@require_http_methods(["POST"])
def customer_select(request, pk, customer_id):
    """Set customer on job and copy addresses."""
    job = get_object_or_404(Job, pk=pk)
    customer = get_object_or_404(Customer, pk=customer_id)
    ticket = job  # Alias for template compatibility
    
    # Set customer
    ticket.customer = customer
    
    # Copy bill-to address from customer
    ticket.bill_to_name = customer.bill_to_name
    ticket.bill_to_address = customer.bill_to_address
    ticket.bill_to_city = customer.bill_to_city
    ticket.bill_to_state = customer.bill_to_state
    ticket.bill_to_zip = customer.bill_to_zip
    
    # Copy default price settings and terms
    if customer.default_price_setting:
        ticket.price_setting = customer.default_price_setting
    if customer.default_terms:
        ticket.terms = customer.default_terms
    
    # Get default ship-to address and copy
    default_ship_to = customer.get_default_ship_to()
    if default_ship_to:
        ticket.ship_to_name = default_ship_to.name
        ticket.ship_to_address = default_ship_to.address
        ticket.ship_to_city = default_ship_to.city
        ticket.ship_to_state = default_ship_to.state
        ticket.ship_to_zip = default_ship_to.zip
    
    ticket.save()
    
    # Return updated customer section
    context = {
        'ticket': ticket,
        'selected_ship_to': default_ship_to,
    }
    return render(request, 'jobs/partials/customer_selected_section.html', context)


# Engine Search & Selection Views

@login_required
@require_http_methods(["GET"])
def engine_search_modal(request, pk):
    """Render the engine search modal for a ticket or job."""
    job = get_object_or_404(Job, pk=pk)
    context = {
        'ticket': job,  # Using 'ticket' name for template compatibility
    }
    return render(request, 'jobs/partials/engine_search_modal.html', context)


@login_required
@require_http_methods(["GET"])
def engine_search_results(request, pk):
    """HTMX endpoint returning filtered engines."""
    job = get_object_or_404(Job, pk=pk)
    query = request.GET.get('q', '').strip()
    ticket = job  # Alias for template compatibility
    
    engines = Engine.objects.all().order_by('engine_make', 'engine_model')
    
    if query:
        # Search across engine fields
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(identifier__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(injection_type__icontains=query)
        ).distinct()
    
    context = {
        'ticket': ticket,
        'engines': engines[:50],  # Limit to 50 results
        'query': query,
    }
    return render(request, 'jobs/partials/engine_search_results.html', context)


@login_required
@require_http_methods(["POST"])
def engine_select(request, pk, engine_id):
    """Set engine on job and copy engine details."""
    job = get_object_or_404(Job, pk=pk)
    engine = get_object_or_404(Engine, pk=engine_id)
    ticket = job  # Alias for template compatibility
    
    # Set engine and copy fields
    ticket.engine = engine
    ticket.engine_make = engine.engine_make
    ticket.engine_model = engine.engine_model
    ticket.engine_identifier = engine.identifier
    ticket.engine_serial_number = engine.serial_number
    
    # Copy injection type if available
    if engine.injection_type:
        ticket.injection_type = engine.injection_type
    
    ticket.save()
    
    # Return updated engine section
    context = {
        'ticket': ticket,
    }
    return render(request, 'jobs/partials/engine_selected_section.html', context)


@login_required
@require_http_methods(["GET"])
def engine_create_modal(request, pk):
    """Render create engine modal."""
    job = get_object_or_404(Job, pk=pk)
    form = EngineQuickCreateForm()
    context = {
        'ticket': job,  # Using 'ticket' name for template compatibility
        'form': form,
    }
    return render(request, 'jobs/partials/engine_create_modal.html', context)


@login_required
@require_http_methods(["POST"])
def engine_create(request, pk):
    """Create a new engine and select it."""
    job = get_object_or_404(Job, pk=pk)
    form = EngineQuickCreateForm(request.POST)
    ticket = job  # Alias for template compatibility
    
    if form.is_valid():
        engine = form.save()
        
        # Get the stamped_number from form (not saved to Engine)
        stamped_number = form.cleaned_data.get('stamped_number', '')
        
        # Set engine on ticket and copy fields
        ticket.engine = engine
        ticket.engine_make = engine.engine_make
        ticket.engine_model = engine.engine_model
        ticket.engine_identifier = engine.identifier
        ticket.engine_serial_number = engine.serial_number
        ticket.engine_stamped_number = stamped_number
        
        if engine.injection_type:
            ticket.injection_type = engine.injection_type
        
        ticket.save()
        
        # Return updated engine section
        context = {
            'ticket': ticket,
        }
        return render(request, 'jobs/partials/engine_selected_section.html', context)
    
    # Return form with errors
    context = {
        'ticket': ticket,
        'form': form,
    }
    return render(request, 'jobs/partials/engine_create_modal.html', context, status=400)


@login_required
@require_http_methods(["GET"])
def customer_create_modal(request, pk):
    """Render create customer modal."""
    job = get_object_or_404(Job, pk=pk)
    form = CustomerForm()
    context = {
        'ticket': job,  # Using 'ticket' name for template compatibility
        'form': form,
    }
    return render(request, 'jobs/partials/customer_create_modal.html', context)


@login_required
@require_http_methods(["POST"])
def customer_create(request, pk):
    """Create a new customer and select it."""
    job = get_object_or_404(Job, pk=pk)
    form = CustomerForm(request.POST)
    ticket = job  # Alias for template compatibility
    
    if form.is_valid():
        customer = form.save()
        
        # Set customer on ticket and copy bill-to address
        ticket.customer = customer
        ticket.bill_to_name = customer.bill_to_name
        ticket.bill_to_address = customer.bill_to_address
        ticket.bill_to_city = customer.bill_to_city
        ticket.bill_to_state = customer.bill_to_state
        ticket.bill_to_zip = customer.bill_to_zip
        
        # Copy default price settings and terms
        if customer.default_price_setting:
            ticket.price_setting = customer.default_price_setting
        if customer.default_terms:
            ticket.terms = customer.default_terms
        
        ticket.save()
        
        # Return updated customer section
        context = {
            'ticket': ticket,
            'selected_ship_to': None,
        }
        return render(request, 'jobs/partials/customer_selected_section.html', context)
    
    # Return form with errors
    context = {
        'ticket': ticket,
        'form': form,
    }
    return render(request, 'jobs/partials/customer_create_modal.html', context, status=400)


# Ship-To Address Management Views

@login_required
@require_http_methods(["GET"])
def customer_ship_to_list(request, customer_id):
    """HTMX endpoint showing ship-to addresses for a customer."""
    customer = get_object_or_404(Customer, pk=customer_id)
    ship_to_addresses = customer.ship_to_addresses.all()
    
    # Support both ticket_id and job_id parameters for backwards compatibility
    ticket_id = request.GET.get('ticket_id') or request.GET.get('job_id')
    ticket = None
    if ticket_id:
        ticket = get_object_or_404(Job, pk=ticket_id)
    
    context = {
        'customer': customer,
        'ship_to_addresses': ship_to_addresses,
        'ticket': ticket,
    }
    return render(request, 'jobs/partials/customer_ship_to_list.html', context)


@login_required
@require_http_methods(["GET"])
def customer_ship_to_create_modal(request, customer_id):
    """Nested modal for adding ship-to address."""
    customer = get_object_or_404(Customer, pk=customer_id)
    form = CustomerShipToAddressForm()
    
    # Support both ticket_id and job_id parameters for backwards compatibility
    ticket_id = request.GET.get('ticket_id') or request.GET.get('job_id')
    ticket = None
    if ticket_id:
        ticket = get_object_or_404(Job, pk=ticket_id)
    
    context = {
        'customer': customer,
        'form': form,
        'ticket': ticket,
    }
    return render(request, 'jobs/partials/customer_ship_to_create_modal.html', context)


@login_required
@require_http_methods(["POST"])
def customer_ship_to_create(request, customer_id):
    """Create a new ship-to address."""
    customer = get_object_or_404(Customer, pk=customer_id)
    form = CustomerShipToAddressForm(request.POST)
    
    # Support both ticket_id and job_id parameters for backwards compatibility
    ticket_id = request.POST.get('ticket_id') or request.POST.get('job_id')
    ticket = None
    if ticket_id:
        ticket = get_object_or_404(Job, pk=ticket_id)
    
    if form.is_valid():
        ship_to = form.save(commit=False)
        ship_to.customer = customer
        ship_to.created_by = request.user
        ship_to.save()
        
        # Return updated list - use table partial for customer management, list partial for ticket
        context = {
            'customer': customer,
            'ship_to_addresses': customer.ship_to_addresses.all(),
            'ticket': ticket,
        }
        if ticket:
            return render(request, 'jobs/partials/customer_ship_to_list.html', context)
        else:
            return render(request, 'jobs/partials/customer_ship_to_table.html', context)
    
    # Return form with errors
    context = {
        'customer': customer,
        'form': form,
        'ticket': ticket,
    }
    return render(request, 'jobs/partials/customer_ship_to_create_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def job_select_ship_to(request, pk, address_id):
    """Select which ship-to address to use for the job/ticket."""
    ticket = get_object_or_404(Job, pk=pk)
    ship_to = get_object_or_404(CustomerShipToAddress, pk=address_id)
    
    # Copy ship-to address to job
    ticket.ship_to_name = ship_to.name
    ticket.ship_to_address = ship_to.address
    ticket.ship_to_city = ship_to.city
    ticket.ship_to_state = ship_to.state
    ticket.ship_to_zip = ship_to.zip
    ticket.save()
    
    # Return updated customer section
    context = {
        'ticket': ticket,
        'selected_ship_to': ship_to,
    }
    return render(request, 'jobs/partials/customer_selected_section.html', context)


# Job Selection Options Setup Views

class JobSelectionOptionListView(LoginRequiredMixin, ListView):
    """List all job selection options grouped by category."""
    model = JobSelectionOption
    template_name = 'jobs/selection_options_list.html'
    context_object_name = 'options'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Group options by category
        context['parts_selection'] = JobSelectionOption.objects.filter(group='parts_selection').order_by('sort_order', 'name')
        context['block_build_lists'] = JobSelectionOption.objects.filter(group='block_build_lists').order_by('sort_order', 'name')
        context['head_build_lists'] = JobSelectionOption.objects.filter(group='head_build_lists').order_by('sort_order', 'name')
        context['item_selection'] = JobSelectionOption.objects.filter(group='item_selection').order_by('sort_order', 'name')
        return context


@login_required
@require_http_methods(["GET"])
def selection_option_create_modal(request):
    """Render create modal for job selection option."""
    form = JobSelectionOptionForm()
    context = {
        'form': form,
        'title': 'Add Job Selection Option',
        'is_create': True,
    }
    return render(request, 'jobs/partials/selection_option_modal.html', context)


@login_required
@require_http_methods(["POST"])
def selection_option_create(request):
    """Create a new job selection option."""
    form = JobSelectionOptionForm(request.POST)
    
    if form.is_valid():
        form.save()
        # Return updated list - trigger full page reload
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    
    # Return form with errors
    context = {
        'form': form,
        'title': 'Add Job Selection Option',
        'is_create': True,
    }
    return render(request, 'jobs/partials/selection_option_modal.html', context, status=400)


@login_required
@require_http_methods(["GET"])
def selection_option_update_modal(request, pk):
    """Render update modal for job selection option."""
    option = get_object_or_404(JobSelectionOption, pk=pk)
    form = JobSelectionOptionForm(instance=option)
    context = {
        'form': form,
        'option': option,
        'title': 'Edit Job Selection Option',
        'is_create': False,
    }
    return render(request, 'jobs/partials/selection_option_modal.html', context)


@login_required
@require_http_methods(["POST"])
def selection_option_update(request, pk):
    """Update an existing job selection option."""
    option = get_object_or_404(JobSelectionOption, pk=pk)
    form = JobSelectionOptionForm(request.POST, instance=option)
    
    if form.is_valid():
        form.save()
        # Return updated list - trigger full page reload
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    
    # Return form with errors
    context = {
        'form': form,
        'option': option,
        'title': 'Edit Job Selection Option',
        'is_create': False,
    }
    return render(request, 'jobs/partials/selection_option_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def selection_option_delete(request, pk):
    """Delete a job selection option."""
    option = get_object_or_404(JobSelectionOption, pk=pk)
    option.delete()
    return redirect('jobs:selection_options_list')


# Selection Option Search Modals
@login_required
@require_http_methods(["GET"])
def so_part_search_modal(request):
    """Render part search modal for selection options."""
    return render(request, 'jobs/partials/so_part_search_modal.html')


@login_required
@require_http_methods(["GET"])
def so_part_search_results(request):
    """Search parts for selection options."""
    from inventory.models import Part
    query = request.GET.get('q', '').strip()
    parts = []
    
    if query:
        parts = Part.objects.filter(
            Q(part_number__icontains=query) | 
            Q(name__icontains=query)
        )[:50]
    
    context = {
        'parts': parts,
        'query': query,
    }
    return render(request, 'jobs/partials/so_part_search_results.html', context)


@login_required
@require_http_methods(["GET"])
def so_kit_search_modal(request):
    """Render kit search modal for selection options."""
    return render(request, 'jobs/partials/so_kit_search_modal.html')


@login_required
@require_http_methods(["GET"])
def so_kit_search_results(request):
    """Search kits for selection options."""
    from inventory.models import Kit
    query = request.GET.get('q', '').strip()
    kits = []
    
    if query:
        kits = Kit.objects.filter(
            Q(name__icontains=query) |
            Q(notes__icontains=query)
        )[:50]
    
    context = {
        'kits': kits,
        'query': query,
    }
    return render(request, 'jobs/partials/so_kit_search_results.html', context)


@login_required
@require_http_methods(["GET"])
def so_buildlist_search_modal(request):
    """Render build list search modal for selection options."""
    return render(request, 'jobs/partials/so_buildlist_search_modal.html')


@login_required
@require_http_methods(["GET"])
def so_buildlist_search_results(request):
    """Search build lists for selection options."""
    from inventory.models import BuildList
    query = request.GET.get('q', '').strip()
    buildlists = []
    
    if query:
        buildlists = BuildList.objects.filter(
            Q(name__icontains=query) |
            Q(notes__icontains=query)
        )[:50]
    
    context = {
        'buildlists': buildlists,
        'query': query,
    }
    return render(request, 'jobs/partials/so_buildlist_search_results.html', context)


# ===================================
# Employee Views
# ===================================

# Old employee functions removed - now using User model managed in Settings
# Job views to be appended to views.py

# ===================================
# Job Views (actual jobs, not tickets)
# ===================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from .models import Job, JobComponent


@login_required
def job_list(request):
    """List all jobs with search, sorting, and status filtering."""
    from core.view_utils import get_list_context
    from django.db.models import Count
    
    # Base queryset - only jobs (not tickets)
    jobs = Job.objects.filter(job_type='job').select_related(
        'customer', 'engine', 'component_info'
    ).prefetch_related('job_parts').annotate(
        parts_count=Count('job_parts')
    )
    
    # Status filter - default to 'wo' (Work Order), 'all' shows everything
    status_filter = request.GET.get('status', 'wo')
    if status_filter and status_filter != 'all':
        jobs = jobs.filter(status=status_filter)
    
    # Get list context with search, sort, and pagination
    context = get_list_context(
        queryset=jobs,
        request=request,
        search_fields=['job_number', 'customer__name', 'engine_make', 'engine_model'],
        sort_fields={
            'job_number', '-job_number',
            'customer__name', '-customer__name',
            'engine_make', '-engine_make',
            'date', '-date',
            'finish_date', '-finish_date',
            'status', '-status'
        },
        default_sort='-date',
        per_page=50
    )
    context['jobs'] = context['object_list']
    
    # Calculate stats (from all jobs, not filtered)
    all_jobs = Job.objects.filter(job_type='job')
    context['stats'] = {
        'quote': all_jobs.filter(status='quote').count(),
        'wo': all_jobs.filter(status='wo').count(),
        'invoice': all_jobs.filter(status='invoice').count(),
    }
    
    # Add status filter to context
    context['status_filter'] = status_filter
    
    context['page_heading'] = 'Jobs'
    context['item_name_plural'] = 'jobs'
    context['search_placeholder'] = 'Search jobs… job #, customer name'
    context['create_url'] = reverse_lazy('jobs:job_create')
    context['create_label'] = 'New Job'
    
    return render(request, 'jobs/job_list.html', context)


@login_required
def purchase_order_list(request):
    """List all purchase orders with search and sorting."""
    from core.view_utils import get_list_context
    from django.db.models import Count
    
    # Base queryset with related data for efficiency
    pos = PurchaseOrder.objects.select_related(
        'vendor', 'requested_by'
    ).prefetch_related('items')
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        pos = pos.filter(status=status_filter)
    
    # Get list context with search, sort, and pagination
    context = get_list_context(
        queryset=pos,
        request=request,
        search_fields=['po_number', 'vendor__name', 'vendor_po_number', 'notes'],
        sort_fields={
            'po_number', '-po_number',
            'vendor__name', '-vendor__name',
            'status', '-status',
            'po_date', '-po_date',
            'expected_delivery_date', '-expected_delivery_date',
            'submitted_date', '-submitted_date',
            'total_amount', '-total_amount'
        },
        default_sort='-po_date',
        per_page=50
    )
    
    # Add annotated item count
    context['purchase_orders'] = context['object_list'].annotate(
        item_count=Count('items')
    )
    
    # Calculate stats (from all POs, not filtered)
    all_pos = PurchaseOrder.objects.all()
    context['stats'] = {
        'draft': all_pos.filter(status='draft').count(),
        'submitted': all_pos.filter(status='submitted').count(),
        'partially_received': all_pos.filter(status='partially_received').count(),
        'received': all_pos.filter(status='received').count(),
    }
    
    # Add status filter to context
    context['status_filter'] = status_filter
    
    # Add additional context for the template
    context['page_heading'] = 'Purchase Orders'
    context['item_name_plural'] = 'purchase orders'
    context['search_placeholder'] = 'Search POs… PO number, vendor name, notes'
    context['create_url'] = reverse_lazy('jobs:po_create')
    context['create_label'] = 'New Purchase Order'
    
    return render(request, 'jobs/purchase_order_list.html', context)


@login_required
def job_create(request):
    """Create a new job - redirect to create page or handle form."""
    # For now, create a draft job and redirect to edit
    from django.utils import timezone
    
    job = Job.objects.create(
        job_type='job',
        status='quote',
        date=timezone.now().date()
    )
    
    # Generate job number
    job.job_number = get_next_job_number()
    job.save(update_fields=['job_number'])
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
def job_detail(request, pk):
    """Combined view/edit page for a job (always editable)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    job = get_object_or_404(Job, pk=pk, job_type='job')
    
    if request.method == 'POST':
        # Update basic job fields
        job.status = request.POST.get('status')
        job.date = request.POST.get('date') or None
        job.finish_date = request.POST.get('finish_date') or None
        job.invoice_date = request.POST.get('invoice_date') or None
        job.store = request.POST.get('store')
        job.customer_po = request.POST.get('customer_po')
        job.sales_person_id = request.POST.get('sales_person') or None
        job.price_setting = request.POST.get('price_setting')
        job.terms = request.POST.get('terms')
        job.notes = request.POST.get('notes')
        job.email_client_on_step_complete = 'email_client_on_step_complete' in request.POST
        job.engine_stamped_number = request.POST.get('engine_stamped_number') or None
        job.save()
        
        # Get component and track old state for detecting changes
        component, _ = JobComponent.objects.get_or_create(job=job)
        old_state = {
            'block_done': component.block_done,
            'head_done': component.head_done,
            'crankshaft_done': component.crankshaft_done,
            'waterpump_done': component.waterpump_done,
            'rods_done': component.rods_done,
            'pistons_done': component.pistons_done,
            'flywheel_done': component.flywheel_done,
            'manifold_done': component.manifold_done,
        }
        
        # Update component progress checkboxes
        component.block_done = 'block_done' in request.POST
        component.head_done = 'head_done' in request.POST
        component.crankshaft_done = 'crankshaft_done' in request.POST
        component.waterpump_done = 'waterpump_done' in request.POST
        component.rods_done = 'rods_done' in request.POST
        component.pistons_done = 'pistons_done' in request.POST
        component.flywheel_done = 'flywheel_done' in request.POST
        component.manifold_done = 'manifold_done' in request.POST
        
        # Update component fields (Main Brg. and Piston Size)
        component.main_bearing = request.POST.get('main_bearing') or None
        component.piston_size = request.POST.get('piston_size') or None
        component.save()
        
        # Detect newly completed components and send notifications
        newly_completed = []
        component_names = {
            'block_done': 'Block',
            'head_done': 'Head',
            'crankshaft_done': 'Crankshaft',
            'waterpump_done': 'Water Pump',
            'rods_done': 'Rods',
            'pistons_done': 'Pistons',
            'flywheel_done': 'Flywheel',
            'manifold_done': 'Manifold',
        }
        
        for field, component_name in component_names.items():
            old_value = old_state.get(field, False)
            new_value = getattr(component, field)
            
            # If it changed from False to True, it was newly completed
            if not old_value and new_value:
                newly_completed.append(component_name)
        
        # Send notifications for newly completed components (only if "Notify on step complete" is checked)
        if newly_completed and job.email_client_on_step_complete:
            for component_name in newly_completed:
                message = f"{component_name} has been marked as completed"
                create_job_notifications(
                    job=job,
                    message=message,
                    notification_type='step_completed',
                    sender_user=request.user
                )
        
        return redirect('jobs:job_list')
    
    # Get related data
    component, _ = JobComponent.objects.get_or_create(job=job)
    
    # Calculate progress percentage
    total_steps = 0
    completed_steps = 0
    
    # Count which components are included and which are done
    if component.block:
        total_steps += 1
        if component.block_done:
            completed_steps += 1
    if component.head:
        total_steps += 1
        if component.head_done:
            completed_steps += 1
    if component.crankshaft:
        total_steps += 1
        if component.crankshaft_done:
            completed_steps += 1
    if component.waterpump:
        total_steps += 1
        if component.waterpump_done:
            completed_steps += 1
    if component.rods:
        total_steps += 1
        if component.rods_done:
            completed_steps += 1
    if component.pistons:
        total_steps += 1
        if component.pistons_done:
            completed_steps += 1
    if component.flywheel:
        total_steps += 1
        if component.flywheel_done:
            completed_steps += 1
    if component.manifold:
        total_steps += 1
        if component.manifold_done:
            completed_steps += 1
    
    # Calculate percentage
    progress_percentage = round((completed_steps / total_steps * 100)) if total_steps > 0 else 0
    
    # Get POs linked to this job (via PO items)
    job_pos = PurchaseOrder.objects.filter(
        items__job=job
    ).distinct().select_related('vendor').annotate(
        item_count=Count('items', filter=Q(items__job=job))
    ).order_by('-po_date')
    
    # Count open POs (not received, closed, or cancelled)
    open_pos_count = job_pos.exclude(status__in=['received', 'closed', 'cancelled']).count()
    
    context = {
        'job': job,
        'component': component,
        'progress_percentage': progress_percentage,
        'job_employees': job.job_employees.select_related('user').all(),
        'job_build_lists': job.job_build_lists.select_related('source_build_list').all(),
        'job_kits': job.job_kits.select_related('source_kit').all(),
        'job_parts': job.job_parts.select_related('source_part').all(),
        'attachments': job.attachments.all(),
        'sales_people': User.objects.filter(is_active=True).order_by('username'),
        'job_pos': job_pos,
        'open_pos_count': open_pos_count,
    }
    
    return render(request, 'jobs/job_form.html', context)


@login_required
@require_http_methods(["POST"])
def job_delete(request, pk):
    """Delete a job."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    job.delete()
    return redirect('jobs:job_list')


# ============== JOB EMPLOYEE ASSIGNMENT VIEWS ==============

@login_required
@require_http_methods(["GET"])
def job_user_assign_modal(request, pk):
    """Show modal to manage user assignments for a job."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    
    # Get list of currently assigned user IDs
    assigned_user_ids = list(job.job_employees.values_list('user_id', flat=True))
    
    context = {
        'job': job,
        'users': users,
        'assigned_user_ids': assigned_user_ids,
    }
    return render(request, 'jobs/modals/job_user_assign_modal.html', context)


@login_required
@require_http_methods(["POST"])
def job_user_assign(request, pk):
    """Manage user assignments for a job (add/remove based on checkboxes)."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    
    # Get selected user IDs from checkboxes
    selected_user_ids = request.POST.getlist('user_ids')
    selected_user_ids = [int(id) for id in selected_user_ids]
    
    # Get currently assigned user IDs
    current_assignments = job.job_employees.all()
    current_user_ids = set(current_assignments.values_list('user_id', flat=True))
    
    # Determine which to add and which to remove
    to_add = set(selected_user_ids) - current_user_ids
    to_remove = current_user_ids - set(selected_user_ids)
    
    # Add new assignments with time = 0
    for user_id in to_add:
        user = get_object_or_404(User, pk=user_id)
        JobEmployee.objects.create(
            job=job,
            user=user,
            calculated_total_time=0
        )
    
    # Remove unchecked assignments
    if to_remove:
        JobEmployee.objects.filter(job=job, user_id__in=to_remove).delete()
    
    # If HTMX request, return updated table and close modal
    if request.headers.get('HX-Request'):
        job_employees = job.job_employees.select_related('user').all()
        response = render(request, 'jobs/partials/job_employees_table_body.html', {
            'job': job,
            'job_employees': job_employees,
        })
        # Add header to close the modal
        response['HX-Trigger'] = 'closeModal'
        return response
    
    # Redirect back to where the modal was opened from (fallback for non-HTMX)
    return redirect(request.POST.get('next', request.META.get('HTTP_REFERER', f'/jobs/{job.pk}/')))


@login_required
@require_http_methods(["POST"])
def job_user_remove(request, job_pk, user_pk):
    """Remove a user from a job."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    assignment = get_object_or_404(JobEmployee, job=job, user_id=user_pk)
    assignment.delete()
    
    return redirect('jobs:job_detail', pk=job.pk)


# ============== JOB BUILD LIST VIEWS ==============

@login_required
@require_http_methods(["GET"])
def job_buildlist_add_modal(request, pk):
    """Show modal to add a build list to a job."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    context = {
        'job': job,
    }
    return render(request, 'jobs/modals/job_buildlist_add_modal.html', context)


@login_required
@require_http_methods(["GET"])
def job_buildlist_add_results(request, pk):
    """HTMX endpoint returning filtered build lists."""
    from inventory.models import BuildList
    job = get_object_or_404(Job, pk=pk, job_type='job')
    query = request.GET.get('q', '').strip()
    
    build_lists = BuildList.objects.all().order_by('name')
    if query:
        build_lists = build_lists.filter(name__icontains=query)
    
    # Filter out already added build lists
    added_bl_ids = job.job_build_lists.values_list('source_build_list_id', flat=True)
    build_lists = build_lists.exclude(id__in=added_bl_ids)[:50]
    
    context = {
        'job': job,
        'build_lists': build_lists,
        'query': query,
    }
    return render(request, 'jobs/modals/job_buildlist_add_results.html', context)


@login_required
@require_http_methods(["POST"])
def job_buildlist_add(request, pk, buildlist_pk):
    """Add a build list to a job."""
    from inventory.models import BuildList, BuildListItem
    job = get_object_or_404(Job, pk=pk, job_type='job')
    build_list = get_object_or_404(BuildList, pk=buildlist_pk)
    
    # Create the JobBuildList
    job_build_list = JobBuildList.objects.create(
        job=job,
        source_build_list=build_list,
        name=build_list.name,  # Snapshot
        notes=build_list.notes if hasattr(build_list, 'notes') else ''
    )
    
    # Copy all build list items
    build_list_items = BuildListItem.objects.filter(build_list=build_list)
    for idx, bl_item in enumerate(build_list_items, start=1):
        JobBuildListItem.objects.create(
            job_build_list=job_build_list,
            source_build_list_item=bl_item,
            name=bl_item.name,
            description=bl_item.description,
            estimated_hours=bl_item.hour_qty,
            sort_order=idx,
            on_job=True,
            is_complete=False
        )
    
    # Return the updated build lists table for HTMX
    job_build_lists = job.job_build_lists.all()
    context = {
        'job': job,
        'job_build_lists': job_build_lists,
    }
    return render(request, 'jobs/partials/job_buildlists_table.html', context)


@login_required
@require_http_methods(["POST"])
def job_buildlist_remove(request, job_pk, buildlist_pk):
    """Remove a build list from a job."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    jbl.delete()
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_http_methods(["POST"])
def job_buildlist_toggle_select(request, job_pk, buildlist_pk):
    """Toggle selection status for PO."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    jbl.selected = not jbl.selected
    jbl.save()
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_http_methods(["GET"])
def job_buildlist_items_modal(request, job_pk, buildlist_pk):
    """Show modal with build list items."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    
    # Get filter parameter (default to 'on_job')
    filter_param = request.GET.get('filter', 'on_job')
    
    # Get all items for this build list and convert to list to preserve attributes
    all_items = list(jbl.items.all())
    
    # Calculate time_worked for each item
    for item in all_items:
        item_time_entries = JobTime.objects.filter(
            job_build_list_item=item,
            end_time__isnull=False
        )
        total_hours = 0
        for entry in item_time_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                total_hours += delta.total_seconds() / 3600
        item.time_worked = round(total_hours, 2)
    
    # Apply filter
    if filter_param == 'on_job':
        items = [item for item in all_items if item.on_job]
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = len(all_items)
    items_on_job_count = sum(1 for item in all_items if item.on_job)
    
    context = {
        'job': job,
        'job_build_list': jbl,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    # If this is an HTMX request from within the modal (filter button clicked),
    # return only the partial table. Check if HX-Target is the table container.
    hx_target = request.headers.get('HX-Target', '')
    if hx_target == 'buildlist-items-table-container':
        return render(request, 'jobs/partials/job_buildlist_items_table.html', context)
    
    # Otherwise return the full modal (initial load)
    return render(request, 'jobs/modals/job_buildlist_items_modal.html', context)


@login_required
@require_http_methods(["POST"])
def job_buildlist_item_toggle_on_job(request, job_pk, buildlist_pk, item_pk):
    """Toggle the on_job status of a build list item."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    item = get_object_or_404(JobBuildListItem, job_build_list=jbl, pk=item_pk)
    
    # Toggle the on_job status
    item.on_job = not item.on_job
    item.save()
    
    # Get the current filter from the request (default to 'on_job')
    filter_param = request.POST.get('current_filter', 'on_job')
    
    # Get all items for this build list and convert to list to preserve attributes
    all_items = list(jbl.items.all())
    
    # Calculate time_worked for each item
    for itm in all_items:
        item_time_entries = JobTime.objects.filter(
            job_build_list_item=itm,
            end_time__isnull=False
        )
        total_hours = 0
        for entry in item_time_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                total_hours += delta.total_seconds() / 3600
        itm.time_worked = round(total_hours, 2)
    
    # Apply filter
    if filter_param == 'on_job':
        items = [itm for itm in all_items if itm.on_job]
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = len(all_items)
    items_on_job_count = sum(1 for itm in all_items if itm.on_job)
    
    context = {
        'job': job,
        'job_build_list': jbl,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    # Render the items table
    items_html = render_to_string('jobs/partials/job_buildlist_items_table.html', context, request=request)
    
    # Also render the build lists table for OOB swap to update % complete
    job_build_lists = job.job_build_lists.all()
    buildlists_context = {
        'job': job,
        'job_build_lists': job_build_lists,
    }
    buildlists_html = render_to_string('jobs/partials/job_buildlists_table.html', buildlists_context, request=request)
    
    # Add hx-swap-oob attribute to the build lists section
    buildlists_html_oob = buildlists_html.replace(
        '<div id="job-buildlists-section">',
        '<div id="job-buildlists-section" hx-swap-oob="true">'
    )
    
    # Return both: items table (main) + build lists table (OOB)
    return HttpResponse(items_html + buildlists_html_oob)


@login_required
@require_http_methods(["POST"])
def job_buildlist_item_toggle_complete(request, job_pk, buildlist_pk, item_pk):
    """Toggle the is_complete status of a build list item."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    item = get_object_or_404(JobBuildListItem, job_build_list=jbl, pk=item_pk)
    
    # Toggle the is_complete status
    item.is_complete = not item.is_complete
    item.save()
    
    # Get the current filter from the request (default to 'on_job')
    filter_param = request.POST.get('current_filter', 'on_job')
    
    # Get all items for this build list and convert to list to preserve attributes
    all_items = list(jbl.items.all())
    
    # Calculate time_worked for each item
    for itm in all_items:
        item_time_entries = JobTime.objects.filter(
            job_build_list_item=itm,
            end_time__isnull=False
        )
        total_hours = 0
        for entry in item_time_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                total_hours += delta.total_seconds() / 3600
        itm.time_worked = round(total_hours, 2)
    
    # Apply filter
    if filter_param == 'on_job':
        items = [itm for itm in all_items if itm.on_job]
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = len(all_items)
    items_on_job_count = sum(1 for itm in all_items if itm.on_job)
    
    context = {
        'job': job,
        'job_build_list': jbl,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    # Render the items table
    items_html = render_to_string('jobs/partials/job_buildlist_items_table.html', context, request=request)
    
    # Also render the build lists table for OOB swap to update % complete
    job_build_lists = job.job_build_lists.all()
    buildlists_context = {
        'job': job,
        'job_build_lists': job_build_lists,
    }
    buildlists_html = render_to_string('jobs/partials/job_buildlists_table.html', buildlists_context, request=request)
    
    # Add hx-swap-oob attribute to the build lists section
    buildlists_html_oob = buildlists_html.replace(
        '<div id="job-buildlists-section">',
        '<div id="job-buildlists-section" hx-swap-oob="true">'
    )
    
    # Return both: items table (main) + build lists table (OOB)
    return HttpResponse(items_html + buildlists_html_oob)


@login_required
@require_http_methods(["GET"])
def job_buildlist_quick_time_modal(request, job_pk, buildlist_pk):
    """Show modal for quick time entry on a build list."""
    from django.contrib.auth.models import User
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    
    # Get all active users
    employees = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    
    context = {
        'job': job,
        'job_build_list': jbl,
        'job_build_list_item': None,
        'employees': employees,
        'current_user': request.user,
        'submit_url': f'/jobs/{job_pk}/buildlists/{buildlist_pk}/add-time/',
        'target_element': '#job-buildlists-section',
    }
    return render(request, 'jobs/modals/quick_time_entry_modal.html', context)


@login_required
@require_http_methods(["POST"])
def job_buildlist_quick_time_submit(request, job_pk, buildlist_pk):
    """Create a quick time entry for a build list."""
    from datetime import timedelta
    from decimal import Decimal
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    
    employee_id = request.POST.get('employee_id')
    hours_str = request.POST.get('hours')
    description = request.POST.get('description', '')
    
    if not employee_id or not hours_str:
        return HttpResponse("Employee and Hours are required", status=400)
    
    employee = get_object_or_404(User, pk=employee_id)
    hours_decimal = Decimal(hours_str)
    
    # Calculate start_time and end_time
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=float(hours_decimal))
    
    # Create time entry
    JobTime.objects.create(
        job=job,
        user=employee,
        job_build_list=jbl,
        job_build_list_item=None,
        start_time=start_time,
        end_time=end_time,
        description=description,
        status='completed'
    )
    
    # Update JobBuildList.time_worked
    completed_bl_entries = JobTime.objects.filter(
        job_build_list=jbl,
        end_time__isnull=False
    )
    
    bl_total_hours = 0
    for entry in completed_bl_entries:
        if entry.start_time and entry.end_time:
            delta = entry.end_time - entry.start_time
            bl_total_hours += delta.total_seconds() / 3600
    
    jbl.time_worked = bl_total_hours
    jbl.save()
    
    # Update JobEmployee.calculated_total_time
    job_employee, created = JobEmployee.objects.get_or_create(
        job=job,
        user=employee,
        defaults={'calculated_total_time': 0}
    )
    
    # Calculate total hours from all completed time entries for this employee on this job
    completed_entries = JobTime.objects.filter(
        job=job,
        user=employee,
        end_time__isnull=False
    )
    
    total_hours = 0
    for entry in completed_entries:
        if entry.start_time and entry.end_time:
            delta = entry.end_time - entry.start_time
            total_hours += delta.total_seconds() / 3600
    
    job_employee.calculated_total_time = total_hours
    job_employee.save()
    
    # Return the updated build lists table
    job_build_lists = job.job_build_lists.all()
    context = {
        'job': job,
        'job_build_lists': job_build_lists,
    }
    return render(request, 'jobs/partials/job_buildlists_table.html', context)


@login_required
@require_http_methods(["GET"])
def job_buildlist_item_quick_time_modal(request, job_pk, buildlist_pk, item_pk):
    """Show modal for quick time entry on a build list item."""
    from django.contrib.auth.models import User
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    item = get_object_or_404(JobBuildListItem, job_build_list=jbl, pk=item_pk)
    
    # Get all active users
    employees = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    
    context = {
        'job': job,
        'job_build_list': jbl,
        'job_build_list_item': item,
        'employees': employees,
        'current_user': request.user,
        'submit_url': f'/jobs/{job_pk}/buildlists/{buildlist_pk}/items/{item_pk}/add-time/',
        'target_element': '#buildlist-items-table-container',
    }
    return render(request, 'jobs/modals/quick_time_entry_modal.html', context)


@login_required
@require_http_methods(["POST"])
def job_buildlist_item_quick_time_submit(request, job_pk, buildlist_pk, item_pk):
    """Create a quick time entry for a build list item."""
    from datetime import timedelta
    from decimal import Decimal
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jbl = get_object_or_404(JobBuildList, job=job, pk=buildlist_pk)
    item = get_object_or_404(JobBuildListItem, job_build_list=jbl, pk=item_pk)
    
    employee_id = request.POST.get('employee_id')
    hours_str = request.POST.get('hours')
    description = request.POST.get('description', '')
    
    if not employee_id or not hours_str:
        return HttpResponse("Employee and Hours are required", status=400)
    
    employee = get_object_or_404(User, pk=employee_id)
    hours_decimal = Decimal(hours_str)
    
    # Calculate start_time and end_time
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=float(hours_decimal))
    
    # Create time entry
    JobTime.objects.create(
        job=job,
        user=employee,
        job_build_list=jbl,
        job_build_list_item=item,
        start_time=start_time,
        end_time=end_time,
        description=description,
        status='completed'
    )
    
    # Update JobBuildList.time_worked
    completed_bl_entries = JobTime.objects.filter(
        job_build_list=jbl,
        end_time__isnull=False
    )
    
    bl_total_hours = 0
    for entry in completed_bl_entries:
        if entry.start_time and entry.end_time:
            delta = entry.end_time - entry.start_time
            bl_total_hours += delta.total_seconds() / 3600
    
    jbl.time_worked = bl_total_hours
    jbl.save()
    
    # Update JobEmployee.calculated_total_time
    job_employee, created = JobEmployee.objects.get_or_create(
        job=job,
        user=employee,
        defaults={'calculated_total_time': 0}
    )
    
    # Calculate total hours from all completed time entries for this employee on this job
    completed_entries = JobTime.objects.filter(
        job=job,
        user=employee,
        end_time__isnull=False
    )
    
    total_hours = 0
    for entry in completed_entries:
        if entry.start_time and entry.end_time:
            delta = entry.end_time - entry.start_time
            total_hours += delta.total_seconds() / 3600
    
    job_employee.calculated_total_time = total_hours
    job_employee.save()
    
    # Get the current filter to maintain it
    filter_param = request.POST.get('current_filter', 'on_job')
    
    # Get all items for this build list and convert to list to preserve attributes
    all_items = list(jbl.items.all())
    
    # Calculate time_worked for each item
    for itm in all_items:
        item_time_entries = JobTime.objects.filter(
            job_build_list_item=itm,
            end_time__isnull=False
        )
        total_hours = 0
        for entry in item_time_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                total_hours += delta.total_seconds() / 3600
        itm.time_worked = round(total_hours, 2)
    
    # Apply filter
    if filter_param == 'on_job':
        items = [itm for itm in all_items if itm.on_job]
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = len(all_items)
    items_on_job_count = sum(1 for itm in all_items if itm.on_job)
    
    context = {
        'job': job,
        'job_build_list': jbl,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    return render(request, 'jobs/partials/job_buildlist_items_table.html', context)


@login_required
@require_http_methods(["GET"])
def job_kit_items_modal(request, job_pk, kit_pk):
    """Show modal with kit items."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jkit = get_object_or_404(JobKit, job=job, pk=kit_pk)
    
    # Get filter parameter (default to 'on_job')
    filter_param = request.GET.get('filter', 'on_job')
    
    # Get all items for this kit
    all_items = jkit.items.all()
    
    # Apply filter
    if filter_param == 'on_job':
        items = all_items.filter(on_job=True)
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = all_items.count()
    items_on_job_count = all_items.filter(on_job=True).count()
    
    context = {
        'job': job,
        'job_kit': jkit,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    # If this is an HTMX request from within the modal (filter button clicked),
    # return only the partial table. Check if HX-Target is the table container.
    hx_target = request.headers.get('HX-Target', '')
    if hx_target == 'kit-items-table-container':
        return render(request, 'jobs/partials/job_kit_items_table.html', context)
    
    # Otherwise return the full modal (initial load)
    return render(request, 'jobs/modals/job_kit_items_modal.html', context)


# ============== JOB KIT VIEWS ==============

@login_required
@require_http_methods(["GET"])
def job_kit_add_modal(request, pk):
    """Show modal to add a kit to a job."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    context = {
        'job': job,
    }
    return render(request, 'jobs/modals/job_kit_add_modal.html', context)


@login_required
@require_http_methods(["GET"])
def job_kit_add_results(request, pk):
    """HTMX endpoint returning filtered kits."""
    from inventory.models import Kit
    job = get_object_or_404(Job, pk=pk, job_type='job')
    query = request.GET.get('q', '').strip()
    
    kits = Kit.objects.all().order_by('name')
    if query:
        kits = kits.filter(name__icontains=query)
    
    # Filter out already added kits
    added_kit_ids = job.job_kits.values_list('source_kit_id', flat=True)
    kits = kits.exclude(id__in=added_kit_ids)[:50]
    
    context = {
        'job': job,
        'kits': kits,
        'query': query,
    }
    return render(request, 'jobs/modals/job_kit_add_results.html', context)


@login_required
@require_http_methods(["POST"])
def job_kit_add(request, pk, kit_pk):
    """Add a kit to a job."""
    from inventory.models import Kit, KitItem
    job = get_object_or_404(Job, pk=pk, job_type='job')
    kit = get_object_or_404(Kit, pk=kit_pk)
    notes = request.POST.get('notes', '')
    
    # Create the JobKit
    job_kit = JobKit.objects.create(
        job=job,
        source_kit=kit,
        name=kit.name,  # Snapshot
        notes=notes
    )
    
    # Copy all kit items
    kit_items = KitItem.objects.filter(kit=kit).select_related('part')
    for idx, kit_item in enumerate(kit_items, start=1):
        JobKitItem.objects.create(
            job_kit=job_kit,
            source_kit_item=kit_item,
            part=kit_item.part,
            part_number=kit_item.part.part_number if kit_item.part else '',
            name=kit_item.part.name if kit_item.part else '',
            quantity=kit_item.quantity,
            sort_order=idx,
            on_job=True,
            is_complete=False
        )
    
    # Return the updated kits table for HTMX
    job_kits = job.job_kits.all()
    context = {
        'job': job,
        'job_kits': job_kits,
    }
    return render(request, 'jobs/partials/job_kits_table.html', context)


@login_required
@require_http_methods(["POST"])
def job_kit_item_toggle_on_job(request, job_pk, kit_pk, item_pk):
    """Toggle the on_job status of a kit item."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jkit = get_object_or_404(JobKit, job=job, pk=kit_pk)
    item = get_object_or_404(JobKitItem, job_kit=jkit, pk=item_pk)
    
    # Toggle the on_job status
    item.on_job = not item.on_job
    item.save()
    
    # Get the current filter from the request (default to 'on_job')
    filter_param = request.POST.get('current_filter', 'on_job')
    
    # Get all items for this kit
    all_items = jkit.items.all()
    
    # Apply filter
    if filter_param == 'on_job':
        items = all_items.filter(on_job=True)
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = all_items.count()
    items_on_job_count = all_items.filter(on_job=True).count()
    
    context = {
        'job': job,
        'job_kit': jkit,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    return render(request, 'jobs/partials/job_kit_items_table.html', context)


@login_required
@require_http_methods(["POST"])
def job_kit_item_toggle_complete(request, job_pk, kit_pk, item_pk):
    """Toggle the is_complete status of a kit item."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jkit = get_object_or_404(JobKit, job=job, pk=kit_pk)
    item = get_object_or_404(JobKitItem, job_kit=jkit, pk=item_pk)
    
    # Toggle the is_complete status
    item.is_complete = not item.is_complete
    item.save()
    
    # Get the current filter from the request (default to 'on_job')
    filter_param = request.POST.get('current_filter', 'on_job')
    
    # Get all items for this kit
    all_items = jkit.items.all()
    
    # Apply filter
    if filter_param == 'on_job':
        items = all_items.filter(on_job=True)
    else:
        items = all_items
    
    # Count items for the tab display
    all_items_count = all_items.count()
    items_on_job_count = all_items.filter(on_job=True).count()
    
    context = {
        'job': job,
        'job_kit': jkit,
        'items': items,
        'filter': filter_param,
        'all_items_count': all_items_count,
        'items_on_job_count': items_on_job_count,
    }
    
    return render(request, 'jobs/partials/job_kit_items_table.html', context)


@login_required
@require_http_methods(["POST"])
def job_kit_remove(request, job_pk, kit_pk):
    """Remove a kit from a job."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jkit = get_object_or_404(JobKit, job=job, pk=kit_pk)
    jkit.delete()
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_http_methods(["POST"])
def job_kit_toggle_select(request, job_pk, kit_pk):
    """Toggle selection status for PO."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jkit = get_object_or_404(JobKit, job=job, pk=kit_pk)
    jkit.is_selected = not jkit.is_selected
    jkit.save()
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_http_methods(["POST"])
def job_kit_update_notes(request, job_pk, kit_pk):
    """Update notes for a job kit."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jkit = get_object_or_404(JobKit, job=job, pk=kit_pk)
    jkit.notes = request.POST.get('notes', '')
    jkit.save()
    
    return redirect('jobs:job_detail', pk=job.pk)


# ============== JOB PART VIEWS ==============

@login_required
@require_http_methods(["GET"])
def job_part_add_modal(request, pk):
    """Show modal to add a part to a job."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    context = {
        'job': job,
    }
    return render(request, 'jobs/modals/job_part_add_modal.html', context)


@login_required
@require_http_methods(["GET"])
def job_part_add_results(request, pk):
    """HTMX endpoint returning filtered parts."""
    from inventory.models import Part
    job = get_object_or_404(Job, pk=pk, job_type='job')
    query = request.GET.get('q', '').strip()
    
    parts = Part.objects.all().order_by('name')
    if query:
        parts = parts.filter(
            Q(name__icontains=query) | Q(part_number__icontains=query)
        )
    
    # Filter out already added parts (allow duplicates but show in search)
    parts = parts[:50]
    
    context = {
        'job': job,
        'parts': parts,
        'query': query,
    }
    return render(request, 'jobs/modals/job_part_add_results.html', context)


@login_required
@require_http_methods(["POST"])
def job_part_add(request, pk, part_pk):
    """Add a part to a job."""
    from inventory.models import Part
    job = get_object_or_404(Job, pk=pk, job_type='job')
    part = get_object_or_404(Part, pk=part_pk)
    qty = request.POST.get('qty', 1)
    notes = request.POST.get('notes', '')
    
    JobPart.objects.create(
        job=job,
        source_part=part,
        part_number=part.part_number,  # Snapshot
        name=part.name,  # Snapshot
        quantity=qty,
        notes=notes
    )
    
    # Return the updated parts table for HTMX
    job_parts = job.job_parts.all()
    context = {
        'job': job,
        'job_parts': job_parts,
    }
    return render(request, 'jobs/partials/job_parts_table.html', context)


@login_required
@require_http_methods(["POST"])
def job_part_remove(request, job_pk, part_pk):
    """Remove a part from a job."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jpart = get_object_or_404(JobPart, job=job, pk=part_pk)
    jpart.delete()
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_http_methods(["POST"])
def job_part_toggle_select(request, job_pk, part_pk):
    """Toggle selection status for PO."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jpart = get_object_or_404(JobPart, job=job, pk=part_pk)
    jpart.selected = not jpart.selected
    jpart.save()
    
    # Return updated parts table for HTMX
    context = {
        'job': job,
        'job_parts': job.job_parts.select_related('source_part').all(),
    }
    return render(request, 'jobs/partials/job_parts_table.html', context)


@login_required
@require_http_methods(["POST"])
def job_part_update(request, job_pk, part_pk):
    """Update qty and notes for a job part."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    jpart = get_object_or_404(JobPart, job=job, pk=part_pk)
    jpart.quantity = request.POST.get('qty', jpart.quantity)
    jpart.notes = request.POST.get('notes', jpart.notes)
    jpart.save()
    
    return redirect('jobs:job_detail', pk=job.pk)


# ============== JOB PO CREATION VIEWS ==============

@login_required
@require_http_methods(["GET"])
def job_create_po_modal(request, pk):
    """Show modal to create PO from selected job parts."""
    from inventory.models import Vendor
    
    job = get_object_or_404(Job, pk=pk, job_type='job')
    
    # Get selected parts with their source parts (for vendor info)
    selected_parts = job.job_parts.filter(selected=True).select_related('source_part__primary_vendor')
    
    if not selected_parts.exists():
        # Return a message modal if no parts selected
        return render(request, 'jobs/modals/job_create_po_modal.html', {
            'job': job,
            'no_parts_selected': True,
        })
    
    # Group parts by their primary vendor
    parts_by_vendor = {}
    parts_without_vendor = []
    
    for jpart in selected_parts:
        vendor = None
        if jpart.source_part and jpart.source_part.primary_vendor:
            vendor = jpart.source_part.primary_vendor
        
        if vendor:
            if vendor.pk not in parts_by_vendor:
                parts_by_vendor[vendor.pk] = {
                    'vendor': vendor,
                    'parts': [],
                    'existing_draft_po': PurchaseOrder.objects.filter(
                        vendor=vendor,
                        status='draft'
                    ).first()
                }
            parts_by_vendor[vendor.pk]['parts'].append(jpart)
        else:
            parts_without_vendor.append(jpart)
    
    # Get all vendors for dropdown
    all_vendors = Vendor.objects.all().order_by('name')
    
    context = {
        'job': job,
        'selected_parts': selected_parts,
        'parts_by_vendor': parts_by_vendor,
        'parts_without_vendor': parts_without_vendor,
        'all_vendors': all_vendors,
    }
    return render(request, 'jobs/modals/job_create_po_modal.html', context)


@login_required
@require_http_methods(["POST"])
def job_create_po(request, pk):
    """Create PO or add items to existing PO from selected job parts."""
    from inventory.models import Vendor
    
    job = get_object_or_404(Job, pk=pk, job_type='job')
    
    # Get form data
    vendor_id = request.POST.get('vendor_id')
    existing_po_id = request.POST.get('existing_po_id')
    part_ids = request.POST.getlist('part_ids')
    
    if not vendor_id or not part_ids:
        # Return error
        return render(request, 'jobs/modals/job_create_po_modal.html', {
            'job': job,
            'error': 'Please select a vendor and at least one part.',
        })
    
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    
    # Either use existing PO or create new one
    if existing_po_id:
        po = get_object_or_404(PurchaseOrder, pk=existing_po_id, status='draft')
    else:
        po = PurchaseOrder.objects.create(
            po_number=get_next_po_number(),
            po_date=timezone.now().date(),
            status='draft',
            vendor=vendor,
            requested_by=request.user
        )
    
    # Add items to PO
    for part_id in part_ids:
        jpart = get_object_or_404(JobPart, pk=part_id, job=job)
        quantity = request.POST.get(f'qty_{part_id}', jpart.quantity) or jpart.quantity
        
        # Check if this part is already on this PO
        existing_item = PurchaseOrderItem.objects.filter(
            purchase_order=po,
            job_part=jpart
        ).first()
        
        if existing_item:
            # Update quantity instead of creating duplicate
            existing_item.quantity_ordered = quantity
            existing_item.save()
        else:
            # Create new PO item
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                part=jpart.source_part,
                job=job,
                job_part=jpart,
                quantity_ordered=quantity,
                part_number=jpart.part_number,
                part_name=jpart.name,
            )
        
        # Clear the selected flag after adding to PO
        jpart.selected = False
        jpart.save()
    
    # Recalculate PO totals
    po.subtotal = sum(
        (item.line_total or 0) for item in po.items.all()
    )
    po.save()
    
    # Return success - close modal and refresh parts table
    response = render(request, 'jobs/partials/job_parts_table.html', {
        'job': job,
        'job_parts': job.job_parts.select_related('source_part').all(),
    })
    response['HX-Trigger'] = 'poCreated'
    return response


# ============== JOB ATTACHMENT VIEWS ==============

@login_required
@require_http_methods(["POST"])
def job_attachment_upload(request, pk):
    """Upload an attachment to a job."""
    job = get_object_or_404(Job, pk=pk, job_type='job')
    file = request.FILES.get('file')
    
    if file:
        JobAttachment.objects.create(
            job=job,
            file=file,
            original_name=file.name,
            created_by=request.user
        )
    
    # If HTMX request, return updated attachments list
    if request.headers.get('HX-Request'):
        attachments = job.attachments.all()
        return render(request, 'jobs/partials/job_attachments_list.html', {
            'job': job,
            'attachments': attachments,
        })
    
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_http_methods(["POST"])
def job_attachment_delete(request, job_pk, attachment_pk):
    """Delete an attachment from a job."""
    job = get_object_or_404(Job, pk=job_pk, job_type='job')
    attachment = get_object_or_404(JobAttachment, job=job, pk=attachment_pk)
    
    # Delete the file from storage
    if attachment.file:
        attachment.file.delete()
    
    attachment.delete()
    
    # If HTMX request, return updated attachments list
    if request.headers.get('HX-Request'):
        attachments = job.attachments.all()
        return render(request, 'jobs/partials/job_attachments_list.html', {
            'job': job,
            'attachments': attachments,
        })
    
    return redirect('jobs:job_detail', pk=job.pk)


# ============== TIME TRACKING VIEWS ==============

@login_required
def time_tracking_page(request):
    """Main time tracking page with user, job, and build list selection."""
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    jobs = Job.objects.filter(job_type='job').select_related('customer').order_by('-date')
    
    context = {
        'users': users,
        'jobs': jobs,
        'current_user_id': request.user.id,
    }
    return render(request, 'jobs/time_tracking.html', context)


@login_required
@require_http_methods(["POST"])
def time_tracking_start(request):
    """Start a new time entry for a user."""
    user_id = request.POST.get('user_id')
    job_id = request.POST.get('job_id')
    job_build_list_id = request.POST.get('job_build_list_id')
    job_build_list_item_id = request.POST.get('job_build_list_item_id')
    
    if not user_id or not job_id:
        return HttpResponse("User and Job are required", status=400)
    
    user = get_object_or_404(User, pk=user_id)
    job = get_object_or_404(Job, pk=job_id)
    
    # Check if user already has an active time entry (no end_time)
    active_entry = JobTime.objects.filter(
        user=user,
        end_time__isnull=True
    ).first()
    
    if active_entry:
        return HttpResponse("User already has an active time entry. Please end it first.", status=400)
    
    # Create new time entry
    time_entry = JobTime.objects.create(
        job=job,
        user=user,
        job_build_list_id=job_build_list_id if job_build_list_id else None,
        job_build_list_item_id=job_build_list_item_id if job_build_list_item_id else None,
        start_time=timezone.now(),
        status='active'
    )
    
    # Return the active entry partial
    context = {
        'active_entry': time_entry,
        'user_id': user_id,
        'job_id': job_id,
    }
    return render(request, 'jobs/partials/time_tracking_active_entry.html', context)


@login_required
@require_http_methods(["POST"])
def time_tracking_end(request, time_entry_pk):
    """End an active time entry and update totals."""
    time_entry = get_object_or_404(JobTime, pk=time_entry_pk)
    
    if time_entry.end_time:
        return HttpResponse("This time entry has already been ended.", status=400)
    
    # Set end time
    time_entry.end_time = timezone.now()
    time_entry.status = 'completed'
    time_entry.save()
    
    # Calculate duration in hours
    duration = time_entry.end_time - time_entry.start_time
    duration_hours = duration.total_seconds() / 3600
    
    # Update JobEmployee.calculated_total_time
    job_employee, created = JobEmployee.objects.get_or_create(
        job=time_entry.job,
        user=time_entry.user,
        defaults={'calculated_total_time': 0}
    )
    
    # Calculate total hours from all completed time entries
    completed_entries = JobTime.objects.filter(
        job=time_entry.job,
        user=time_entry.user,
        end_time__isnull=False
    )
    
    total_hours = 0
    for entry in completed_entries:
        if entry.start_time and entry.end_time:
            delta = entry.end_time - entry.start_time
            total_hours += delta.total_seconds() / 3600
    
    job_employee.calculated_total_time = total_hours
    job_employee.save()
    
    # Update JobBuildList.time_worked if a build list is selected
    if time_entry.job_build_list:
        completed_bl_entries = JobTime.objects.filter(
            job_build_list=time_entry.job_build_list,
            end_time__isnull=False
        )
        
        bl_total_hours = 0
        for entry in completed_bl_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                bl_total_hours += delta.total_seconds() / 3600
        
        time_entry.job_build_list.time_worked = bl_total_hours
        time_entry.job_build_list.save()
    
    # Return empty response to clear active entry and trigger history reload
    response = HttpResponse("")
    response['HX-Trigger'] = 'timeEnded'
    return response


@login_required
@require_http_methods(["GET"])
def time_tracking_history(request, user_pk):
    """Load time history table for selected user."""
    user = get_object_or_404(User, pk=user_pk)
    
    # Get all time entries for this user, ordered by most recent
    time_entries = JobTime.objects.filter(
        user=user
    ).select_related('job', 'job_build_list').order_by('-start_time')[:100]
    
    # Calculate duration for each entry
    entries_with_duration = []
    for entry in time_entries:
        duration_str = '-'
        if entry.start_time and entry.end_time:
            delta = entry.end_time - entry.start_time
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            duration_str = f"{hours}h {minutes}m"
        
        entries_with_duration.append({
            'entry': entry,
            'duration': duration_str
        })
    
    context = {
        'user': user,
        'entries_with_duration': entries_with_duration,
    }
    return render(request, 'jobs/partials/time_tracking_history_table.html', context)


@login_required
@require_http_methods(["GET"])
def time_tracking_job_buildlists(request, job_pk):
    """Load build lists for selected job."""
    job = get_object_or_404(Job, pk=job_pk)
    
    # Get all build lists for this job
    job_build_lists = job.job_build_lists.all()
    
    context = {
        'job_build_lists': job_build_lists,
    }
    return render(request, 'jobs/partials/time_tracking_buildlist_options.html', context)


@login_required
@require_http_methods(["GET"])
def time_tracking_buildlist_items(request, buildlist_pk):
    """Load build list items for selected build list."""
    job_build_list = get_object_or_404(JobBuildList, pk=buildlist_pk)
    
    # Get all items for this build list
    items = job_build_list.items.filter(on_job=True).order_by('sort_order', 'name')
    
    context = {
        'items': items,
    }
    return render(request, 'jobs/partials/time_tracking_buildlist_item_options.html', context)


@login_required
@require_http_methods(["GET"])
def time_tracking_active_entry(request):
    """Check if user has an active time entry."""
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return HttpResponse("")
    
    user = get_object_or_404(User, pk=user_id)
    
    # Check for active entry
    active_entry = JobTime.objects.filter(
        user=user,
        end_time__isnull=True
    ).first()
    
    if active_entry:
        context = {
            'active_entry': active_entry,
            'user_id': user_id,
        }
        return render(request, 'jobs/partials/time_tracking_active_entry.html', context)
    
    return HttpResponse("")


@login_required
@require_http_methods(["GET"])
def time_entry_edit_modal(request, time_entry_pk):
    """Show modal to edit a time entry."""
    time_entry = get_object_or_404(JobTime, pk=time_entry_pk)
    
    # Format datetimes for datetime-local input
    initial_data = {}
    if time_entry.start_time:
        initial_data['start_time'] = time_entry.start_time.strftime('%Y-%m-%dT%H:%M')
    if time_entry.end_time:
        initial_data['end_time'] = time_entry.end_time.strftime('%Y-%m-%dT%H:%M')
    
    form = TimeEntryForm(instance=time_entry, initial=initial_data)
    
    context = {
        'time_entry': time_entry,
        'form': form,
    }
    return render(request, 'jobs/modals/time_entry_modal.html', context)


@login_required
@require_http_methods(["POST"])
def time_entry_update(request, time_entry_pk):
    """Update a time entry."""
    time_entry = get_object_or_404(JobTime, pk=time_entry_pk)
    form = TimeEntryForm(request.POST, instance=time_entry)
    
    if form.is_valid():
        updated_entry = form.save()
        
        # Recalculate totals after update
        # Update JobEmployee.calculated_total_time
        job_employee, created = JobEmployee.objects.get_or_create(
            job=updated_entry.job,
            user=updated_entry.user,
            defaults={'calculated_total_time': 0}
        )
        
        # Calculate total hours from all completed time entries
        completed_entries = JobTime.objects.filter(
            job=updated_entry.job,
            user=updated_entry.user,
            end_time__isnull=False
        )
        
        total_hours = 0
        for entry in completed_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                total_hours += delta.total_seconds() / 3600
        
        job_employee.calculated_total_time = total_hours
        job_employee.save()
        
        # Update JobBuildList.time_worked if a build list is selected
        if updated_entry.job_build_list:
            completed_bl_entries = JobTime.objects.filter(
                job_build_list=updated_entry.job_build_list,
                end_time__isnull=False
            )
            
            bl_total_hours = 0
            for entry in completed_bl_entries:
                if entry.start_time and entry.end_time:
                    delta = entry.end_time - entry.start_time
                    bl_total_hours += delta.total_seconds() / 3600
            
            updated_entry.job_build_list.time_worked = bl_total_hours
            updated_entry.job_build_list.save()
        
        # Close modal and refresh history
        response = HttpResponse("")
        response['HX-Trigger'] = 'timeUpdated'
        return response
    
    # Return form with errors
    context = {
        'time_entry': time_entry,
        'form': form,
    }
    return render(request, 'jobs/modals/time_entry_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def time_entry_delete(request, time_entry_pk):
    """Delete a time entry."""
    time_entry = get_object_or_404(JobTime, pk=time_entry_pk)
    
    # Store info before deletion for recalculation
    job = time_entry.job
    user = time_entry.user
    job_build_list = time_entry.job_build_list
    
    time_entry.delete()
    
    # Recalculate totals after deletion
    job_employee = JobEmployee.objects.filter(job=job, user=user).first()
    if job_employee:
        completed_entries = JobTime.objects.filter(
            job=job,
            user=user,
            end_time__isnull=False
        )
        
        total_hours = 0
        for entry in completed_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                total_hours += delta.total_seconds() / 3600
        
        job_employee.calculated_total_time = total_hours
        job_employee.save()
    
    # Update JobBuildList.time_worked if a build list was selected
    if job_build_list:
        completed_bl_entries = JobTime.objects.filter(
            job_build_list=job_build_list,
            end_time__isnull=False
        )
        
        bl_total_hours = 0
        for entry in completed_bl_entries:
            if entry.start_time and entry.end_time:
                delta = entry.end_time - entry.start_time
                bl_total_hours += delta.total_seconds() / 3600
        
        job_build_list.time_worked = bl_total_hours
        job_build_list.save()
    
    # Close modal and refresh history
    response = HttpResponse("")
    response['HX-Trigger'] = 'timeUpdated'
    return response


# ===================================
# Notification System Views
# ===================================

def create_job_notifications(job, message, notification_type, sender_user, parent_notification=None):
    """
    Helper function to create notifications for all assigned employees with user accounts.
    
    Args:
        job: The Job instance
        message: The notification message
        notification_type: Type of notification (from JobNotification.TYPE_CHOICES)
        sender_user: The user sending the notification
        parent_notification: Optional parent notification for threading
    
    Returns:
        Count of notifications created
    """
    from .models import JobNotification
    
    # Get all employees assigned to the job
    job_employees = JobEmployee.objects.filter(job=job).select_related('user')
    
    notifications_created = 0
    for job_employee in job_employees:
        if job_employee.user:
            # Don't send notification to the sender
            if job_employee.user != sender_user:
                JobNotification.objects.create(
                    user=job_employee.user,
                    job=job,
                    type=notification_type,
                    message=message,
                    created_by=sender_user,
                    parent_notification=parent_notification
                )
                notifications_created += 1
    
    return notifications_created


@login_required
@require_http_methods(["GET"])
def job_notify_team_modal(request, pk):
    """Show modal to select team members to notify."""
    job = get_object_or_404(Job, pk=pk)
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    
    # Get list of currently assigned user IDs (these will be pre-checked)
    assigned_user_ids = list(job.job_employees.values_list('user_id', flat=True))
    
    context = {
        'job': job,
        'users': users,
        'assigned_user_ids': assigned_user_ids,
    }
    return render(request, 'jobs/modals/notify_team_modal.html', context)


@login_required
@require_http_methods(["POST"])
def job_notify_team(request, pk):
    """Send a notification to selected team members."""
    from .models import JobNotification
    
    job = get_object_or_404(Job, pk=pk)
    message = request.POST.get('message', '').strip()
    
    # Get selected user IDs from checkboxes
    selected_user_ids = request.POST.getlist('user_ids')
    selected_user_ids = [int(id) for id in selected_user_ids if id]
    
    if not message:
        # If HTMX request, return error without reload
        if request.headers.get('HX-Request'):
            return HttpResponse("Message is required", status=400)
        # Redirect back with error (in production, you might want to use messages framework)
        return redirect('jobs:job_detail', pk=pk)
    
    if not selected_user_ids:
        # If HTMX request, return error without reload
        if request.headers.get('HX-Request'):
            return HttpResponse("Please select at least one team member", status=400)
        return redirect('jobs:job_detail', pk=pk)
    
    # Create notifications for selected users only
    count = 0
    for user_id in selected_user_ids:
        try:
            user = User.objects.get(pk=user_id, is_active=True)
            # Don't notify the sender
            if user != request.user:
                JobNotification.objects.create(
                    user=user,
                    job=job,
                    type='team_message',
                    message=message,
                    created_by=request.user
                )
                count += 1
        except User.DoesNotExist:
            continue
    
    # If HTMX request, return success and trigger modal close
    if request.headers.get('HX-Request'):
        response = HttpResponse("")
        response['HX-Trigger'] = 'notificationSent'
        return response
    
    # Redirect back to job edit page (fallback for non-HTMX)
    return redirect('jobs:job_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def notification_mark_read(request, pk):
    """Mark a notification as read."""
    from .models import JobNotification
    
    notification = get_object_or_404(JobNotification, pk=pk, user=request.user)
    notification.read_at = timezone.now()
    notification.save()
    
    # If HTMX request, return updated notifications partial with sidebar OOB update
    if request.headers.get('HX-Request'):
        return _render_notifications_partial(request, include_sidebar_oob=True)
    
    return redirect('jobs:home')


@login_required
@require_http_methods(["POST"])
def notification_mark_unread(request, pk):
    """Mark a notification as unread."""
    from .models import JobNotification
    
    notification = get_object_or_404(JobNotification, pk=pk, user=request.user)
    notification.read_at = None
    notification.save()
    
    # If HTMX request, return updated notifications partial with sidebar OOB update
    if request.headers.get('HX-Request'):
        return _render_notifications_partial(request, include_sidebar_oob=True)
    
    return redirect('jobs:home')


def _render_notifications_partial(request, include_sidebar_oob=False):
    """Helper to render the notifications partial for HTMX updates."""
    from .models import JobNotification
    
    show_filter = request.GET.get('show', 'unread')
    
    notifications_query = JobNotification.objects.filter(
        user=request.user
    ).select_related('job', 'created_by')
    
    if show_filter == 'unread':
        notifications = notifications_query.filter(read_at__isnull=True)[:8]
    else:
        notifications = notifications_query[:8]
    
    unread_count = JobNotification.objects.filter(
        user=request.user, 
        read_at__isnull=True
    ).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'show_filter': show_filter,
        'include_sidebar_oob': include_sidebar_oob,
    }
    return render(request, 'jobs/partials/dashboard_notifications.html', context)


@login_required
def dashboard_notifications(request):
    """
    Return the notifications partial for HTMX polling.
    Polls every 30 seconds to check for new notifications.
    """
    return _render_notifications_partial(request)


@login_required
def sidebar_notification_indicator(request):
    """
    Return just the sidebar Home link with notification indicator.
    Used for HTMX polling on all pages to update the notification badge.
    """
    from .models import JobNotification
    
    unread_count = JobNotification.objects.filter(
        user=request.user,
        read_at__isnull=True
    ).count()
    
    return render(request, 'jobs/partials/sidebar_home_link.html', {
        'unread_count': unread_count,
    })


@login_required
@require_http_methods(["POST"])
def notification_reply(request, notification_pk):
    """Reply to a notification sender."""
    from .models import JobNotification
    
    original_notification = get_object_or_404(JobNotification, pk=notification_pk, user=request.user)
    message = request.POST.get('message', '').strip()
    
    if not message:
        return redirect('jobs:home')
    
    # Create notification for the original sender
    if original_notification.created_by:
        JobNotification.objects.create(
            user=original_notification.created_by,
            job=original_notification.job,
            type='generic',
            message=message,
            created_by=request.user,
            parent_notification=original_notification
        )
    
    return redirect('jobs:home')


@login_required
@require_http_methods(["POST"])
def notification_reply_all(request, notification_pk):
    """Reply to all team members on the job."""
    from .models import JobNotification
    
    original_notification = get_object_or_404(JobNotification, pk=notification_pk, user=request.user)
    message = request.POST.get('message', '').strip()
    
    if not message or not original_notification.job:
        return redirect('jobs:home')
    
    # Create notifications for all assigned team members
    create_job_notifications(
        job=original_notification.job,
        message=message,
        notification_type='generic',
        sender_user=request.user,
        parent_notification=original_notification
    )
    
    return redirect('jobs:home')


@login_required
def notifications_api(request):
    """API endpoint to fetch notifications for polling."""
    from django.http import JsonResponse
    from django.utils import timezone as django_tz
    from .models import JobNotification
    
    # Get filter parameter (all or unread)
    show_filter = request.GET.get('show', 'unread')
    
    # Query notifications for the logged-in user
    notifications_query = JobNotification.objects.filter(user=request.user).select_related('job', 'created_by')
    
    if show_filter == 'unread':
        notifications = notifications_query.filter(read_at__isnull=True)
    else:
        notifications = notifications_query
    
    # Count unread notifications
    unread_count = JobNotification.objects.filter(user=request.user, read_at__isnull=True).count()
    
    # Build notification data
    notifications_data = []
    for notification in notifications:
        # Convert to local timezone (settings.TIME_ZONE)
        local_time = django_tz.localtime(notification.created_at)
        
        # Format time to match Django template format: "m/d/Y g:i A"
        # Use %-I on Unix or custom formatting to avoid leading zero on hour
        hour = local_time.strftime('%I').lstrip('0') or '12'  # Remove leading zero, handle midnight
        formatted_time = local_time.strftime(f'%m/%d/%Y {hour}:%M %p')
        
        notifications_data.append({
            'id': notification.pk,
            'created_at': formatted_time,
            'job_id': notification.job.pk if notification.job else None,
            'job_number': notification.job.job_number if notification.job else 'N/A',
            'from_user': notification.created_by.username if notification.created_by else 'System',
            'message': notification.message,
            'is_read': notification.read_at is not None,
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': unread_count,
        'show_filter': show_filter,
    })


@login_required
def send_notification_modal(request):
    """
    Show the send notification modal from the dashboard.
    Allows sending notifications to selected users about a job.
    """
    users = User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by('first_name', 'last_name', 'username')
    
    context = {
        'users': users,
    }
    return render(request, 'jobs/modals/send_notification_modal.html', context)


@login_required
def notification_job_search(request):
    """HTMX endpoint for searching jobs when sending a notification."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return HttpResponse('')
    
    jobs = Job.objects.filter(job_type='job').select_related('customer').order_by('-created_at')
    
    # Search by job number, customer name, or engine info
    jobs = jobs.filter(
        Q(job_number__icontains=query) |
        Q(ticket_number__icontains=query) |
        Q(customer__name__icontains=query) |
        Q(engine_make__icontains=query) |
        Q(engine_model__icontains=query)
    ).distinct()[:10]
    
    context = {
        'jobs': jobs,
        'query': query,
    }
    return render(request, 'jobs/partials/notification_job_search_results.html', context)


@login_required
@require_http_methods(["POST"])
def send_notification(request):
    """
    Send a notification from the dashboard to selected users.
    Supports sending to all users or selected users, optionally about a job.
    """
    from .models import JobNotification
    
    message = request.POST.get('message', '').strip()
    job_id = request.POST.get('job_id', '').strip()
    recipient_mode = request.POST.get('recipient_mode', 'all')
    selected_user_ids = request.POST.getlist('user_ids')
    
    if not message:
        if request.headers.get('HX-Request'):
            return HttpResponse("Message is required", status=400)
        return redirect('jobs:home')
    
    # Get the job if specified
    job = None
    if job_id:
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            pass
    
    # Determine recipients
    if recipient_mode == 'all':
        # Send to all active users except the sender
        recipients = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
    else:
        # Send to selected users
        selected_user_ids = [int(uid) for uid in selected_user_ids if uid]
        recipients = User.objects.filter(pk__in=selected_user_ids, is_active=True)
    
    # Create notifications
    notifications_created = 0
    for user in recipients:
        JobNotification.objects.create(
            user=user,
            job=job,
            type='team_message',
            message=message,
            created_by=request.user
        )
        notifications_created += 1
    
    # Return success response
    if request.headers.get('HX-Request'):
        response = HttpResponse("")
        response['HX-Trigger'] = 'dashboardNotificationSent'
        return response
    
    return redirect('jobs:home')


# ===================================
# Purchase Order Views
# ===================================

@login_required
def purchase_order_create(request):
    """Create a new purchase order and redirect to edit."""
    po = PurchaseOrder.objects.create(
        po_number=get_next_po_number(),
        po_date=timezone.now().date(),
        status='draft',
        requested_by=request.user
    )
    return redirect('jobs:po_detail', pk=po.pk)


@login_required
def purchase_order_detail(request, pk):
    """Combined view/edit page for purchase orders (always editable)."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        # Update PO fields
        po.status = request.POST.get('status', po.status)
        po.po_date = request.POST.get('po_date') or po.po_date
        po.submitted_date = request.POST.get('submitted_date') or None
        po.expected_delivery_date = request.POST.get('expected_delivery_date') or None
        po.actual_delivery_date = request.POST.get('actual_delivery_date') or None
        po.vendor_contact_id = request.POST.get('vendor_contact') or None
        po.vendor_po_number = request.POST.get('vendor_po_number', '')
        
        # Financial fields
        po.tax_rate = request.POST.get('tax_rate') or None
        po.tax_amount = request.POST.get('tax_amount') or None
        po.shipping_cost = request.POST.get('shipping_cost') or None
        po.other_charges = request.POST.get('other_charges') or None
        po.discount_amount = request.POST.get('discount_amount') or None
        
        # Terms & Shipping
        po.payment_terms = request.POST.get('payment_terms', '')
        po.shipping_method = request.POST.get('shipping_method', '')
        po.shipping_account_number = request.POST.get('shipping_account_number', '')
        po.tracking_number = request.POST.get('tracking_number', '')
        po.carrier = request.POST.get('carrier', '')
        
        # Shipping Address
        po.ship_to_name = request.POST.get('ship_to_name', '')
        po.ship_to_address = request.POST.get('ship_to_address', '')
        po.ship_to_city = request.POST.get('ship_to_city', '')
        po.ship_to_state = request.POST.get('ship_to_state', '')
        po.ship_to_zip = request.POST.get('ship_to_zip', '')
        po.ship_to_phone = request.POST.get('ship_to_phone', '')
        
        # Notes
        po.notes = request.POST.get('notes', '')
        po.vendor_notes = request.POST.get('vendor_notes', '')
        po.receiving_notes = request.POST.get('receiving_notes', '')
        
        # Flags
        po.is_urgent = 'is_urgent' in request.POST
        po.is_drop_ship = 'is_drop_ship' in request.POST
        
        po.save()
        
        # Recalculate totals based on items
        calculate_po_totals(po)
        
        # Redirect to PO list page
        redirect_url = reverse('jobs:purchase_order_list')
        
        # If HTMX request, use HX-Redirect header
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = redirect_url
            return response
        
        return redirect('jobs:purchase_order_list')
    
    # GET request - show the form
    # Calculate subtotal and total from line items
    items = po.items.all()
    
    vendor_contacts = []
    if po.vendor:
        vendor_contacts = VendorContact.objects.filter(vendor=po.vendor).order_by('full_name')
    
    context = {
        'po': po,
        'items': items,
        'vendor_contacts': vendor_contacts,
        'attachments': po.attachments.all(),
        'all_users': User.objects.filter(is_active=True).order_by('username'),
    }
    
    return render(request, 'jobs/purchase_order_form.html', context)


def calculate_po_totals(po):
    """Calculate and update PO subtotal and total based on line items."""
    items = po.items.all()
    
    # Calculate subtotal from line items
    subtotal = Decimal('0.00')
    for item in items:
        if item.line_total:
            subtotal += item.line_total
        elif item.unit_price and item.quantity_ordered:
            subtotal += item.unit_price * item.quantity_ordered
    
    po.subtotal = subtotal
    
    # Calculate total
    total = subtotal
    if po.tax_amount:
        total += po.tax_amount
    if po.shipping_cost:
        total += po.shipping_cost
    if po.other_charges:
        total += po.other_charges
    if po.discount_amount:
        total -= po.discount_amount
    
    po.total_amount = total
    po.save(update_fields=['subtotal', 'total_amount'])


@login_required
@require_http_methods(["POST"])
def purchase_order_delete(request, pk):
    """Delete a purchase order."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    po.delete()
    return redirect('jobs:purchase_order_list')


# Vendor Selection Views

@login_required
@require_http_methods(["GET"])
def po_vendor_search_modal(request, pk):
    """Render the vendor search modal for a PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    context = {'po': po}
    return render(request, 'jobs/partials/po_vendor_search_modal.html', context)


@login_required
@require_http_methods(["GET"])
def po_vendor_search_results(request, pk):
    """HTMX endpoint returning filtered vendors."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    query = request.GET.get('q', '').strip()
    
    vendors = Vendor.objects.all().order_by('name')
    
    if query:
        vendors = vendors.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(website__icontains=query)
        ).distinct()
    
    context = {
        'po': po,
        'vendors': vendors[:50],
        'query': query,
    }
    return render(request, 'jobs/partials/po_vendor_search_results.html', context)


@login_required
@require_http_methods(["POST"])
def po_vendor_select(request, pk, vendor_id):
    """Set vendor on PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    
    po.vendor = vendor
    po.save()
    
    # Get vendor contacts for dropdown
    vendor_contacts = VendorContact.objects.filter(vendor=vendor).order_by('full_name')
    
    # Return updated vendor section
    context = {
        'po': po,
        'vendor_contacts': vendor_contacts,
    }
    return render(request, 'jobs/partials/po_vendor_selected_section.html', context)


@login_required
@require_http_methods(["POST"])
def po_vendor_create(request, pk):
    """Create a new vendor and assign it to the PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    # Get form data
    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    website = request.POST.get('website', '').strip()
    address = request.POST.get('address', '').strip()
    
    if not name:
        return HttpResponse("Vendor name is required", status=400)
    
    # Create the vendor
    vendor = Vendor.objects.create(
        name=name,
        phone=phone,
        email=email,
        website=website,
        address=address,
    )
    
    # Assign vendor to PO
    po.vendor = vendor
    po.save()
    
    # Get vendor contacts for dropdown (will be empty for new vendor)
    vendor_contacts = VendorContact.objects.filter(vendor=vendor).order_by('full_name')
    
    # Return updated vendor section
    context = {
        'po': po,
        'vendor_contacts': vendor_contacts,
    }
    return render(request, 'jobs/partials/po_vendor_selected_section.html', context)


# PO Ship To Address Views

@login_required
@require_http_methods(["GET"])
def po_get_default_address(request):
    """Return the default PO ship-to address from system configuration."""
    from settings_app.models import SystemConfiguration
    
    config = SystemConfiguration.get_config()
    
    # Check if any default address fields are set
    has_address = any([
        config.default_po_ship_to_name,
        config.default_po_ship_to_address,
        config.default_po_ship_to_city,
        config.default_po_ship_to_state,
        config.default_po_ship_to_zip,
        config.default_po_ship_to_phone,
    ])
    
    if has_address:
        return JsonResponse({
            'success': True,
            'name': config.default_po_ship_to_name or '',
            'address': config.default_po_ship_to_address or '',
            'city': config.default_po_ship_to_city or '',
            'state': config.default_po_ship_to_state or '',
            'zip': config.default_po_ship_to_zip or '',
            'phone': config.default_po_ship_to_phone or '',
        })
    else:
        return JsonResponse({'success': False, 'message': 'No default address configured'})


@login_required
@require_http_methods(["GET"])
def po_customer_search_modal(request, pk):
    """Show modal to search customers for ship-to address."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    context = {'po': po}
    return render(request, 'jobs/partials/po_customer_search_modal.html', context)


@login_required
@require_http_methods(["GET"])
def po_customer_search_results(request, pk):
    """HTMX endpoint returning filtered customers."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    query = request.GET.get('q', '').strip()
    
    customers = Customer.objects.all().order_by('name')
    if query:
        customers = customers.filter(
            Q(name__icontains=query) | Q(bill_to_name__icontains=query)
        )
    
    customers = customers[:30]
    
    # For each customer, also get their ship-to addresses
    customer_data = []
    for customer in customers:
        ship_to_addresses = list(customer.ship_to_addresses.all())
        customer_data.append({
            'customer': customer,
            'ship_to_addresses': ship_to_addresses,
        })
    
    context = {
        'po': po,
        'customer_data': customer_data,
        'query': query,
    }
    return render(request, 'jobs/partials/po_customer_search_results.html', context)


# PO Item Management Views

@login_required
@require_http_methods(["GET"])
def po_item_add_modal(request, pk):
    """Show modal to add a part to PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    context = {'po': po}
    return render(request, 'jobs/partials/po_item_add_modal.html', context)


@login_required
@require_http_methods(["GET"])
def po_item_add_results(request, pk):
    """HTMX endpoint returning filtered parts."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    query = request.GET.get('q', '').strip()
    
    parts = Part.objects.all().order_by('name')
    if query:
        parts = parts.filter(
            Q(name__icontains=query) | Q(part_number__icontains=query)
        )
    
    parts = parts[:50]
    
    context = {
        'po': po,
        'parts': parts,
        'query': query,
    }
    return render(request, 'jobs/partials/po_item_add_results.html', context)


@login_required
@require_http_methods(["POST"])
def po_item_add(request, pk, part_pk):
    """Add a part to PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    part = get_object_or_404(Part, pk=part_pk)
    
    qty = request.POST.get('quantity', 1)
    unit_price = request.POST.get('unit_price', 0)
    notes = request.POST.get('notes', '')
    
    # Calculate line total
    try:
        qty_decimal = Decimal(str(qty))
        price_decimal = Decimal(str(unit_price))
        line_total = qty_decimal * price_decimal
    except:
        line_total = Decimal('0.00')
    
    # Create PO item with snapshot of part data
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        part=part,
        part_number=part.part_number or '',
        part_name=part.name or '',
        vendor_part_number=getattr(part, 'vendor_part_number', ''),
        manufacturer=getattr(part, 'manufacturer', ''),
        quantity_ordered=qty_decimal,
        unit_price=price_decimal,
        line_total=line_total,
        line_notes=notes,
        status='ordered'
    )
    
    # Recalculate PO totals
    calculate_po_totals(po)
    
    # Return updated items table
    items = po.items.all()
    context = {
        'po': po,
        'items': items,
    }
    return render(request, 'jobs/partials/po_items_table.html', context)


@login_required
@require_http_methods(["POST"])
def po_custom_item_add(request, pk):
    """Add a custom (non-inventory) item to PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    # Get form data
    part_number = request.POST.get('part_number', '').strip()
    part_name = request.POST.get('part_name', '').strip()
    qty = request.POST.get('quantity', 1)
    unit_price = request.POST.get('unit_price', 0)
    vendor_part_number = request.POST.get('vendor_part_number', '').strip()
    manufacturer = request.POST.get('manufacturer', '').strip()
    notes = request.POST.get('notes', '').strip()
    
    if not part_name:
        return HttpResponse("Item name is required", status=400)
    
    # Calculate line total
    try:
        qty_decimal = Decimal(str(qty))
        price_decimal = Decimal(str(unit_price))
        line_total = qty_decimal * price_decimal
    except:
        qty_decimal = Decimal('1')
        price_decimal = Decimal('0')
        line_total = Decimal('0.00')
    
    # Create PO item WITHOUT linking to a part (custom entry)
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        part=None,  # Custom entry - no part link
        part_number=part_number,
        part_name=part_name,
        vendor_part_number=vendor_part_number,
        manufacturer=manufacturer,
        quantity_ordered=qty_decimal,
        unit_price=price_decimal,
        line_total=line_total,
        line_notes=notes,
        status='ordered'
    )
    
    # Recalculate PO totals
    calculate_po_totals(po)
    
    # Return updated items table
    items = po.items.all()
    context = {
        'po': po,
        'items': items,
    }
    return render(request, 'jobs/partials/po_items_table.html', context)


@login_required
@require_http_methods(["POST"])
def po_item_remove(request, pk, item_pk):
    """Remove an item from PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    item.delete()
    
    # Recalculate PO totals
    calculate_po_totals(po)
    
    # Return updated items table
    items = po.items.all()
    context = {
        'po': po,
        'items': items,
    }
    return render(request, 'jobs/partials/po_items_table.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
@require_http_methods(["GET"])
def po_item_edit_modal(request, pk, item_pk):
    """Show modal to edit a PO item."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    
    context = {
        'po': po,
        'item': item,
    }
    return render(request, 'jobs/partials/po_item_edit_modal.html', context)


@login_required
@require_http_methods(["POST"])
def po_item_update(request, pk, item_pk):
    """Update quantity/price/notes for a PO item inline."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    
    # Update fields
    qty = request.POST.get('quantity', item.quantity_ordered)
    unit_price = request.POST.get('unit_price', item.unit_price)
    notes = request.POST.get('line_notes', item.line_notes)
    
    try:
        qty_decimal = Decimal(str(qty))
        price_decimal = Decimal(str(unit_price))
        item.quantity_ordered = qty_decimal
        item.unit_price = price_decimal
        item.line_total = qty_decimal * price_decimal
        item.line_notes = notes
        item.save()
    except:
        pass
    
    # Recalculate PO totals
    calculate_po_totals(po)
    
    # Return updated items table
    items = po.items.all()
    context = {
        'po': po,
        'items': items,
    }
    return render(request, 'jobs/partials/po_items_table.html', context)


# PO Receiving Views

@login_required
@require_http_methods(["GET"])
def po_item_receive_modal(request, pk, item_pk):
    """Show modal to receive items."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    
    context = {
        'po': po,
        'item': item,
    }
    return render(request, 'jobs/partials/po_item_receive_modal.html', context)


@login_required
@require_http_methods(["POST"])
def po_item_receive_submit(request, pk, item_pk):
    """Process receiving for a PO item."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    
    qty_received = request.POST.get('quantity_received', 0)
    condition = request.POST.get('condition', 'good')
    location = request.POST.get('location', '')
    notes = request.POST.get('notes', '')
    
    try:
        qty_decimal = Decimal(str(qty_received))
        
        # Create receiving record
        PurchaseOrderReceiving.objects.create(
            purchase_order_item=item,
            received_date=timezone.now(),
            quantity_received=qty_decimal,
            received_by=request.user,
            condition=condition,
            received_location=location,
            notes=notes
        )
        
        # Update item quantities
        item.quantity_received += qty_decimal
        
        # Update item status
        if item.quantity_received >= item.quantity_ordered:
            item.status = 'received'
        elif item.quantity_received > 0:
            item.status = 'partially_received'
        
        item.save()
        
        # Update PO status
        update_po_status(po)
        
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=400)
    
    # Refresh PO from database to get updated status
    po.refresh_from_db()
    
    # Render updated items table
    items = po.items.all()
    items_html = render_to_string('jobs/partials/po_items_table.html', {
        'po': po,
        'items': items,
    }, request=request)
    
    # OOB swap for status badge and dropdown
    oob_status = get_po_status_oob_html(po)
    
    # Return items table + status badge and dropdown (OOB)
    return HttpResponse(items_html + oob_status)


def update_po_status(po):
    """Update PO status based on receiving status of all items."""
    items = po.items.all()
    
    if not items.exists():
        return
    
    all_received = all(item.quantity_received >= item.quantity_ordered for item in items)
    any_received = any(item.quantity_received > 0 for item in items)
    
    if all_received:
        po.status = 'received'
    elif any_received:
        po.status = 'partially_received'
    else:
        # Keep current status if nothing received
        pass
    
    po.save(update_fields=['status'])


def get_po_status_oob_html(po):
    """Generate OOB HTML for both status badge and status dropdown."""
    status_choices = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # OOB swap for status badge
    oob_badge = f'<span id="po-status-badge" hx-swap-oob="outerHTML" class="po-status-badge po-status-{po.status}">{po.get_status_display()}</span>'
    
    # OOB swap for status dropdown
    options_html = ''.join([
        f'<option value="{value}" {"selected" if po.status == value else ""}>{label}</option>'
        for value, label in status_choices
    ])
    oob_dropdown = f'<select name="status" id="po-status-select" class="po-select" hx-swap-oob="outerHTML">{options_html}</select>'
    
    return oob_badge + oob_dropdown


@login_required
@require_http_methods(["GET"])
def po_item_receive_history(request, pk, item_pk):
    """Show receiving history for an item."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    
    receives = item.receives.select_related('received_by').order_by('-received_date')
    
    context = {
        'po': po,
        'item': item,
        'receives': receives,
    }
    return render(request, 'jobs/partials/po_item_receive_history.html', context)


@login_required
@require_http_methods(["GET"])
def po_receive_edit_modal(request, pk, item_pk, receive_pk):
    """Show modal to edit a receiving record."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    receive = get_object_or_404(PurchaseOrderReceiving, purchase_order_item=item, pk=receive_pk)
    
    context = {
        'po': po,
        'item': item,
        'receive': receive,
    }
    return render(request, 'jobs/partials/po_receive_edit_modal.html', context)


@login_required
@require_http_methods(["POST"])
def po_receive_update(request, pk, item_pk, receive_pk):
    """Update a receiving record."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    receive = get_object_or_404(PurchaseOrderReceiving, purchase_order_item=item, pk=receive_pk)
    
    old_qty = receive.quantity_received
    
    qty = request.POST.get('quantity_received', receive.quantity_received)
    condition = request.POST.get('condition', receive.condition)
    location = request.POST.get('received_location', receive.received_location)
    notes = request.POST.get('notes', receive.notes)
    
    try:
        new_qty = Decimal(str(qty))
        receive.quantity_received = new_qty
        receive.condition = condition
        receive.received_location = location
        receive.notes = notes
        receive.save()
        
        # Update item's received quantity
        qty_diff = new_qty - old_qty
        item.quantity_received = (item.quantity_received or Decimal('0')) + qty_diff
        # Note: quantity_remaining is a computed property, no need to set it
        
        # Update item status based on computed quantity_remaining
        if item.quantity_remaining <= 0:
            item.status = 'received'
        elif item.quantity_received > 0:
            item.status = 'partially_received'
        else:
            item.status = 'ordered'
        item.save()
        
        # Update PO status
        update_po_status(po)
    except:
        pass
    
    # Refresh item and PO from database to get updated values
    item.refresh_from_db()
    po.refresh_from_db()
    
    # Get updated receives for history modal
    receives = item.receives.select_related('received_by').order_by('-received_date')
    
    # Render the history modal
    history_html = render_to_string('jobs/partials/po_item_receive_history.html', {
        'po': po,
        'item': item,
        'receives': receives,
    }, request=request)
    
    # Render the items table with OOB swap to update the line items section
    items = po.items.all()
    items_html = render_to_string('jobs/partials/po_items_table.html', {
        'po': po,
        'items': items,
    }, request=request)
    
    # Wrap items table in OOB swap div
    oob_items = f'<div id="po-items-section" hx-swap-oob="innerHTML">{items_html}</div>'
    
    # OOB swap for status badge and dropdown
    oob_status = get_po_status_oob_html(po)
    
    # Return: history modal (main swap) + items table (OOB) + status badge and dropdown (OOB)
    return HttpResponse(history_html + oob_items + oob_status)


@login_required
@require_http_methods(["POST"])
def po_receive_delete(request, pk, item_pk, receive_pk):
    """Delete a receiving record."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, purchase_order=po, pk=item_pk)
    receive = get_object_or_404(PurchaseOrderReceiving, purchase_order_item=item, pk=receive_pk)
    
    # Update item's received quantity
    item.quantity_received = (item.quantity_received or Decimal('0')) - receive.quantity_received
    if item.quantity_received < 0:
        item.quantity_received = Decimal('0')
    # Note: quantity_remaining is a computed property, no need to set it
    
    # Update item status based on the computed quantity_remaining property
    if item.quantity_remaining <= 0:
        item.status = 'received'
    elif item.quantity_received > 0:
        item.status = 'partially_received'
    else:
        item.status = 'ordered'
    item.save()
    
    # Delete the receiving record
    receive.delete()
    
    # Update PO status
    update_po_status(po)
    
    # Refresh item and PO from database to get updated values
    item.refresh_from_db()
    po.refresh_from_db()
    
    # Get updated receives for history modal
    receives = item.receives.select_related('received_by').order_by('-received_date')
    
    # Render the history modal
    history_html = render_to_string('jobs/partials/po_item_receive_history.html', {
        'po': po,
        'item': item,
        'receives': receives,
    }, request=request)
    
    # Render the items table with OOB swap to update the line items section
    items = po.items.all()
    items_html = render_to_string('jobs/partials/po_items_table.html', {
        'po': po,
        'items': items,
    }, request=request)
    
    # Wrap items table in OOB swap div
    oob_items = f'<div id="po-items-section" hx-swap-oob="innerHTML">{items_html}</div>'
    
    # OOB swap for status badge and dropdown
    oob_status = get_po_status_oob_html(po)
    
    # Return: history modal (main swap) + items table (OOB) + status badge and dropdown (OOB)
    return HttpResponse(history_html + oob_items + oob_status)


# PO Attachment Views

@login_required
@require_http_methods(["POST"])
def po_attachment_upload(request, pk):
    """Upload an attachment to a PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    file = request.FILES.get('file')
    description = request.POST.get('description', '')
    
    if file:
        PurchaseOrderAttachment.objects.create(
            purchase_order=po,
            file=file,
            original_name=file.name,
            description=description,
            created_by=request.user
        )
    
    # If HTMX request, return updated attachments list
    if request.headers.get('HX-Request'):
        attachments = po.attachments.all()
        return render(request, 'jobs/partials/po_attachments_list.html', {
            'po': po,
            'attachments': attachments,
        })
    
    return redirect('jobs:po_detail', pk=po.pk)


@login_required
@require_http_methods(["POST"])
def po_attachment_delete(request, pk, attachment_pk):
    """Delete an attachment from a PO."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    attachment = get_object_or_404(PurchaseOrderAttachment, purchase_order=po, pk=attachment_pk)
    
    # Delete the file from storage
    if attachment.file:
        attachment.file.delete()
    
    attachment.delete()
    
    # If HTMX request, return updated attachments list
    if request.headers.get('HX-Request'):
        attachments = po.attachments.all()
        return render(request, 'jobs/partials/po_attachments_list.html', {
            'po': po,
            'attachments': attachments,
        })
    
    return redirect('jobs:po_detail', pk=po.pk)


# ===================================
# Customer Management Views
# ===================================

@login_required
def customer_list(request):
    """List all customers with search and sorting."""
    from core.view_utils import get_list_context
    
    # Base queryset
    customers = Customer.objects.all()
    
    # Get list context with search, sort, and pagination
    context = get_list_context(
        queryset=customers,
        request=request,
        search_fields=['name', 'email', 'phone', 'bill_to_name', 'bill_to_city', 'bill_to_state'],
        sort_fields={
            'name', '-name',
            'email', '-email',
            'bill_to_city', '-bill_to_city',
            'default_price_setting', '-default_price_setting',
            'default_terms', '-default_terms',
            'created_at', '-created_at',
        },
        default_sort='name',
        per_page=50
    )
    context['customers'] = context['object_list']
    
    context['page_heading'] = 'Customers'
    context['item_name_plural'] = 'customers'
    context['search_placeholder'] = 'Search customers… name, email, phone, city'
    context['create_url'] = reverse_lazy('jobs:customer_create_page')
    context['create_label'] = 'New Customer'
    
    return render(request, 'jobs/customer_list.html', context)


@login_required
def customer_create_page(request):
    """Create a new customer (standalone page, not modal)."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            return redirect('jobs:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'customer': None,
        'is_new': True,
    }
    return render(request, 'jobs/customer_form.html', context)


@login_required
def customer_detail(request, pk):
    """View and edit a customer."""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.updated_by = request.user
            customer.save()
            # Go to customer list after save
            return redirect('jobs:customer_list')
    else:
        form = CustomerForm(instance=customer)
    
    # Get ship-to addresses
    ship_to_addresses = customer.ship_to_addresses.all()
    
    context = {
        'form': form,
        'customer': customer,
        'ship_to_addresses': ship_to_addresses,
        'is_new': False,
    }
    return render(request, 'jobs/customer_form.html', context)


@login_required
@require_http_methods(["POST"])
def customer_delete(request, pk):
    """Delete a customer (with protection if has jobs)."""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check if customer has jobs
    if customer.jobs.exists():
        # Return error if HTMX request
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<div class="alert alert-danger">Cannot delete customer with associated jobs.</div>',
                status=400
            )
        # For regular request, redirect with error message
        return redirect('jobs:customer_detail', pk=pk)
    
    customer.delete()
    return redirect('jobs:customer_list')


@login_required
@require_http_methods(["GET"])
def customer_ship_to_edit_modal(request, customer_id, address_id):
    """Modal for editing a ship-to address."""
    customer = get_object_or_404(Customer, pk=customer_id)
    address = get_object_or_404(CustomerShipToAddress, pk=address_id, customer=customer)
    form = CustomerShipToAddressForm(instance=address)
    
    context = {
        'customer': customer,
        'address': address,
        'form': form,
    }
    return render(request, 'jobs/partials/customer_ship_to_edit_modal.html', context)


@login_required
@require_http_methods(["POST"])
def customer_ship_to_update(request, customer_id, address_id):
    """Update a ship-to address."""
    customer = get_object_or_404(Customer, pk=customer_id)
    address = get_object_or_404(CustomerShipToAddress, pk=address_id, customer=customer)
    form = CustomerShipToAddressForm(request.POST, instance=address)
    
    if form.is_valid():
        address = form.save(commit=False)
        address.updated_by = request.user
        address.save()
        
        # Return updated table
        ship_to_addresses = customer.ship_to_addresses.all()
        return render(request, 'jobs/partials/customer_ship_to_table.html', {
            'customer': customer,
            'ship_to_addresses': ship_to_addresses,
        })
    
    # Return form with errors
    context = {
        'customer': customer,
        'address': address,
        'form': form,
    }
    return render(request, 'jobs/partials/customer_ship_to_edit_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def customer_ship_to_delete(request, customer_id, address_id):
    """Delete a ship-to address."""
    customer = get_object_or_404(Customer, pk=customer_id)
    address = get_object_or_404(CustomerShipToAddress, pk=address_id, customer=customer)
    
    address.delete()
    
    # Return updated table
    ship_to_addresses = customer.ship_to_addresses.all()
    return render(request, 'jobs/partials/customer_ship_to_table.html', {
        'customer': customer,
        'ship_to_addresses': ship_to_addresses,
    })


# ===================================
# Calendar Views
# ===================================

@login_required
def calendar_view(request):
    """Render the full calendar page."""
    return render(request, 'jobs/calendar.html')


@login_required
def calendar_events_api(request):
    """
    API endpoint for FullCalendar events.
    Returns Jobs (by finish_date) and Purchase Orders (by expected_delivery_date).
    """
    from datetime import datetime
    
    # Get date range from FullCalendar request
    # FullCalendar sends ISO datetime strings, we need just the date part
    start_date_str = request.GET.get('start')
    end_date_str = request.GET.get('end')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        # Parse ISO datetime and extract date (handles "2025-11-30T00:00:00-06:00")
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            start_date = None
    
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            end_date = None
    
    events = []
    
    # Job status colors
    job_colors = {
        'draft': '#9CA3AF',      # Gray
        'new': '#3B82F6',        # Blue
        'in_progress': '#F59E0B', # Amber
        'completed': '#10B981',   # Green
        'cancelled': '#EF4444',   # Red
        'quote': '#8B5CF6',       # Purple
        'wo': '#06B6D4',          # Cyan
        'invoice': '#6366F1',     # Indigo
    }
    
    # PO status colors
    po_colors = {
        'draft': '#94A3B8',           # Slate
        'submitted': '#0EA5E9',       # Sky blue
        'partially_received': '#F97316', # Orange
        'received': '#22C55E',        # Green
        'closed': '#64748B',          # Gray
        'cancelled': '#DC2626',       # Red
    }
    
    # Query Jobs - only WO status with finish_date OR date field set
    jobs_query = Job.objects.filter(
        status='wo'
    ).filter(
        Q(finish_date__isnull=False) | Q(date__isnull=False)
    )
    if start_date and end_date:
        jobs_query = jobs_query.filter(
            Q(finish_date__gte=start_date, finish_date__lte=end_date) |
            Q(finish_date__isnull=True, date__gte=start_date, date__lte=end_date)
        )
    
    for job in jobs_query:
        # Determine which date to use (prefer finish_date, fall back to date)
        event_date = job.finish_date or job.date
        if not event_date:
            continue
        
        # Build title: job number + customer/engine info
        title_parts = []
        if job.job_number:
            title_parts.append(job.job_number)
        elif job.ticket_number:
            title_parts.append(job.ticket_number)
        else:
            title_parts.append(f'Job #{job.pk}')
        
        if job.customer:
            title_parts.append(f'- {job.customer.name}')
        elif job.engine_make or job.engine_model:
            title_parts.append(f'- {job.engine_make or ""} {job.engine_model or ""}'.strip())
        
        events.append({
            'id': f'job-{job.pk}',
            'title': ' '.join(title_parts),
            'start': event_date.isoformat(),
            'url': reverse('jobs:job_detail', args=[job.pk]),
            'backgroundColor': job_colors.get(job.status, '#6B7280'),
            'borderColor': job_colors.get(job.status, '#6B7280'),
            'extendedProps': {
                'type': 'job',
                'status': job.get_status_display() if job.status else 'Draft',
            }
        })
    
    # Query Purchase Orders - only Submitted and Partially Received with expected_delivery_date
    pos_query = PurchaseOrder.objects.filter(
        status__in=['submitted', 'partially_received'],
        expected_delivery_date__isnull=False
    )
    if start_date and end_date:
        pos_query = pos_query.filter(expected_delivery_date__gte=start_date, expected_delivery_date__lte=end_date)
    
    for po in pos_query:
        # Build title: PO number + vendor
        title = po.po_number
        if po.vendor:
            title += f' - {po.vendor.name}'
        
        events.append({
            'id': f'po-{po.pk}',
            'title': title,
            'start': po.expected_delivery_date.isoformat(),
            'url': reverse('jobs:po_detail', args=[po.pk]),
            'backgroundColor': po_colors.get(po.status, '#64748B'),
            'borderColor': po_colors.get(po.status, '#64748B'),
            'extendedProps': {
                'type': 'po',
                'status': po.get_status_display() if po.status else 'Draft',
            }
        })
    
    return JsonResponse(events, safe=False)

