from django.db import models
from django.conf import settings
from django.db.models import SET_NULL, CASCADE, PROTECT
from core.models import AuditMixin
from inventory.models import Engine, Part, Kit, BuildList, BuildListItem, KitItem


class Customer(AuditMixin):
    """Customer model for jobs."""
    
    PRICE_SETTING_CHOICES = [
        ('list', 'List'),
        ('jobber', 'Jobber'),
    ]
    
    TERMS_CHOICES = [
        ('net_30', 'Net 30'),
        ('1pct_10', '1% 10'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255, null=True, blank=True)
    bill_to_name = models.CharField(max_length=255, null=True, blank=True)
    bill_to_address = models.CharField(max_length=255, null=True, blank=True)
    bill_to_city = models.CharField(max_length=100, null=True, blank=True)
    bill_to_state = models.CharField(max_length=50, null=True, blank=True)
    bill_to_zip = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    
    # Default pricing settings
    default_price_setting = models.CharField(
        max_length=20, 
        choices=PRICE_SETTING_CHOICES, 
        null=True, 
        blank=True,
        help_text="Default price setting for this customer"
    )
    default_terms = models.CharField(
        max_length=20, 
        choices=TERMS_CHOICES, 
        null=True, 
        blank=True,
        help_text="Default payment terms for this customer"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name or "(No Name)"
    
    def get_default_ship_to(self):
        """Get the default ship-to address for this customer."""
        return self.ship_to_addresses.filter(is_default=True).first()


class CustomerShipToAddress(AuditMixin):
    """Ship-to addresses for customers."""
    customer = models.ForeignKey(Customer, on_delete=CASCADE, related_name='ship_to_addresses')
    name = models.CharField(max_length=255, help_text="Label like 'Warehouse 1', 'Main Office', etc.")
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'name'],
                name='unique_customer_ship_to_name'
            )
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        """If this is set as default, unset other defaults for this customer."""
        if self.is_default:
            CustomerShipToAddress.objects.filter(
                customer=self.customer,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Job(AuditMixin):
    """Merged JobTicket + Job/WO model."""
    
    JOB_TYPE_CHOICES = [
        ('ticket', 'Ticket'),
        ('job', 'Job'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('quote', 'Quote'),
        ('wo', 'WO'),
        ('invoice', 'Invoice'),
    ]
    
    INJECTION_TYPE_CHOICES = [
        ('di', 'DI'),
        ('idi', 'IDI'),
    ]
    
    PRICE_SETTING_CHOICES = [
        ('list', 'List'),
        ('jobber', 'Jobber'),
    ]
    
    TERMS_CHOICES = [
        ('net_30', 'Net 30'),
        ('1pct_10', '1% 10'),
        ('other', 'Other'),
    ]
    
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, null=True, blank=True)
    ticket_number = models.CharField(max_length=50, null=True, blank=True)
    job_number = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    store = models.CharField(max_length=100, null=True, blank=True)
    finish_date = models.DateField(null=True, blank=True)
    
    customer = models.ForeignKey(Customer, on_delete=PROTECT, related_name="jobs", null=True, blank=True)
    
    # Engine relationship and fields
    engine = models.ForeignKey(Engine, on_delete=PROTECT, related_name="jobs", null=True, blank=True)
    engine_make = models.CharField(max_length=255, null=True, blank=True)
    engine_model = models.CharField(max_length=255, null=True, blank=True)
    engine_identifier = models.CharField(max_length=255, null=True, blank=True)
    engine_serial_number = models.CharField(max_length=255, null=True, blank=True)
    engine_stamped_number = models.CharField(max_length=255, null=True, blank=True)
    injection_type = models.CharField(max_length=10, choices=INJECTION_TYPE_CHOICES, null=True, blank=True)
    
    notes = models.TextField(null=True, blank=True)
    customer_po = models.CharField(max_length=100, null=True, blank=True)
    
    sales_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=SET_NULL, 
        related_name="jobs_as_sales", 
        null=True, 
        blank=True
    )
    
    price_setting = models.CharField(max_length=20, choices=PRICE_SETTING_CHOICES, null=True, blank=True)
    terms = models.CharField(max_length=20, choices=TERMS_CHOICES, null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    
    # Billing address fields
    bill_to_name = models.CharField(max_length=255, null=True, blank=True)
    bill_to_address = models.CharField(max_length=255, null=True, blank=True)
    bill_to_city = models.CharField(max_length=100, null=True, blank=True)
    bill_to_state = models.CharField(max_length=50, null=True, blank=True)
    bill_to_zip = models.CharField(max_length=20, null=True, blank=True)
    
    # Shipping address fields
    ship_to_name = models.CharField(max_length=255, null=True, blank=True)
    ship_to_address = models.CharField(max_length=255, null=True, blank=True)
    ship_to_city = models.CharField(max_length=100, null=True, blank=True)
    ship_to_state = models.CharField(max_length=50, null=True, blank=True)
    ship_to_zip = models.CharField(max_length=20, null=True, blank=True)
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=SET_NULL, 
        related_name="assigned_jobs", 
        null=True, 
        blank=True
    )
    
    progress_percent = models.PositiveIntegerField(null=True, blank=True)
    email_client_on_step_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.job_number:
            return f"Job {self.job_number}"
        elif self.ticket_number:
            return f"Ticket {self.ticket_number}"
        return f"Job #{self.pk}"


class JobComponent(AuditMixin):
    """Component info + progress for a Job."""
    
    MANIFOLD_PIECES_CHOICES = [
        (1, '1 piece'),
        (2, '2 pieces'),
        (3, '3 pieces'),
    ]
    
    job = models.OneToOneField(Job, on_delete=CASCADE, related_name="component_info")
    
    # Component included flags
    block = models.BooleanField(default=False)
    block_mb_caps = models.BooleanField(default=False)
    block_cam = models.BooleanField(default=False)
    head = models.BooleanField(default=False)
    head_vs = models.BooleanField(default=False)
    head_bare = models.BooleanField(default=False)
    crankshaft = models.BooleanField(default=False)
    waterpump = models.BooleanField(default=False)
    rods = models.BooleanField(default=False)
    rods_fractured = models.BooleanField(default=False)
    rods_machined = models.BooleanField(default=False)
    rods_qty = models.PositiveSmallIntegerField(null=True, blank=True)
    pistons = models.BooleanField(default=False)
    pistons_part_number = models.CharField(max_length=100, null=True, blank=True)
    pistons_qty = models.PositiveSmallIntegerField(null=True, blank=True)
    flywheel = models.BooleanField(default=False)
    flywheel_stepped = models.BooleanField(default=False)
    flywheel_flat = models.BooleanField(default=False)
    manifold = models.BooleanField(default=False)
    manifold_pieces = models.PositiveSmallIntegerField(
        choices=MANIFOLD_PIECES_CHOICES, 
        null=True, 
        blank=True
    )
    manifold_diameter = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    
    # Component progress flags
    block_done = models.BooleanField(default=False)
    head_done = models.BooleanField(default=False)
    crankshaft_done = models.BooleanField(default=False)
    waterpump_done = models.BooleanField(default=False)
    rods_done = models.BooleanField(default=False)
    pistons_done = models.BooleanField(default=False)
    flywheel_done = models.BooleanField(default=False)
    manifold_done = models.BooleanField(default=False)

    @property
    def progress_percentage(self):
        """Calculate progress percentage based on selected components and their done status."""
        components = [
            ('block', 'block_done'),
            ('head', 'head_done'),
            ('crankshaft', 'crankshaft_done'),
            ('rods', 'rods_done'),
            ('pistons', 'pistons_done'),
            ('flywheel', 'flywheel_done'),
            ('waterpump', 'waterpump_done'),
            ('manifold', 'manifold_done'),
        ]
        
        total_steps = 0
        completed_steps = 0
        
        for selected_field, done_field in components:
            if getattr(self, selected_field, False):
                total_steps += 1
                if getattr(self, done_field, False):
                    completed_steps += 1
        
        if total_steps == 0:
            return 0
        return round((completed_steps / total_steps) * 100)

    def __str__(self):
        return f"Components for {self.job}"


class JobSelectionOption(AuditMixin):
    """Setup: what appears as checkboxes for job selection."""
    
    GROUP_CHOICES = [
        ('parts_selection', 'Parts Selection'),
        ('block_build_lists', 'Block Build Lists'),
        ('head_build_lists', 'Head Build Lists'),
        ('item_selection', 'Item Selection'),
    ]
    
    name = models.CharField(max_length=255, null=True, blank=True)
    group = models.CharField(max_length=30, choices=GROUP_CHOICES, null=True, blank=True)
    part = models.ForeignKey(Part, on_delete=PROTECT, related_name="selection_options", null=True, blank=True)
    kit = models.ForeignKey(Kit, on_delete=PROTECT, related_name="selection_options", null=True, blank=True)
    build_list = models.ForeignKey(BuildList, on_delete=PROTECT, related_name="selection_options", null=True, blank=True)
    sort_order = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name or f"Option {self.pk}"


class JobSelectedOption(AuditMixin):
    """What's checked for a Job."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="selected_options", null=True, blank=True)
    option = models.ForeignKey(JobSelectionOption, on_delete=PROTECT, related_name="job_selections", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'option'], 
                name='unique_job_option'
            )
        ]

    def __str__(self):
        return f"{self.job} - {self.option}"


class JobBuildList(AuditMixin):
    """BuildList attached to a Job (snapshot)."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="job_build_lists", null=True, blank=True)
    source_build_list = models.ForeignKey(
        BuildList, 
        on_delete=PROTECT, 
        related_name="job_build_lists", 
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=255, null=True, blank=True)  # snapshot
    notes = models.TextField(null=True, blank=True)  # snapshot
    sort_order = models.PositiveIntegerField(null=True, blank=True)
    is_selected = models.BooleanField(null=True, blank=True)
    selected = models.BooleanField(default=False)  # For PO selection
    time_worked = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total hours worked")

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.job} - {self.name}"


class JobBuildListItem(AuditMixin):
    """Items on a BuildList for this Job (snapshot)."""
    job_build_list = models.ForeignKey(JobBuildList, on_delete=CASCADE, related_name="items", null=True, blank=True)
    source_build_list_item = models.ForeignKey(
        BuildListItem, 
        on_delete=PROTECT, 
        related_name="job_items", 
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=255, null=True, blank=True)  # snapshot
    description = models.TextField(null=True, blank=True)  # snapshot
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # snapshot
    sort_order = models.PositiveIntegerField(null=True, blank=True)
    on_job = models.BooleanField(default=True)
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.job_build_list} - {self.name}"


class JobPart(AuditMixin):
    """Individual parts on the Job (snapshot)."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="job_parts", null=True, blank=True)
    source_part = models.ForeignKey(Part, on_delete=PROTECT, related_name="job_parts", null=True, blank=True)
    part_number = models.CharField(max_length=100, null=True, blank=True)  # snapshot
    name = models.CharField(max_length=255, null=True, blank=True)  # snapshot
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, null=True, blank=True)
    selected = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.job} - {self.part_number or self.name}"


class JobKit(AuditMixin):
    """Kit attached to a Job (snapshot)."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="job_kits", null=True, blank=True)
    source_kit = models.ForeignKey(Kit, on_delete=PROTECT, related_name="job_kits", null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)  # snapshot
    notes = models.TextField(null=True, blank=True)  # snapshot
    sort_order = models.PositiveIntegerField(null=True, blank=True)
    is_selected = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.job} - {self.name}"


class JobKitItem(AuditMixin):
    """Items inside a kit on this Job (snapshot)."""
    job_kit = models.ForeignKey(JobKit, on_delete=CASCADE, related_name="items", null=True, blank=True)
    source_kit_item = models.ForeignKey(KitItem, on_delete=PROTECT, related_name="job_items", null=True, blank=True)
    part = models.ForeignKey(Part, on_delete=PROTECT, related_name="job_kit_items", null=True, blank=True)
    part_number = models.CharField(max_length=100, null=True, blank=True)  # snapshot
    name = models.CharField(max_length=255, null=True, blank=True)  # snapshot
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # snapshot
    sort_order = models.PositiveIntegerField(null=True, blank=True)
    on_job = models.BooleanField(default=True)
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['sort_order', 'part_number', 'name']

    def __str__(self):
        return f"{self.job_kit} - {self.part_number or self.name}"


class JobEmployee(AuditMixin):
    """Link between Job and User (employee)."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="job_employees", null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=SET_NULL,
        related_name="job_assignments",
        null=True,
        blank=True
    )
    calculated_total_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total hours worked"
    )

    def __str__(self):
        if self.user:
            name = self.user.get_full_name() or self.user.username
            return f"{self.job} - {name}"
        return f"{self.job} - (No User)"


class JobTime(AuditMixin):
    """Time entries per build list item."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="time_entries", null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True
    )
    job_build_list = models.ForeignKey(
        JobBuildList,
        on_delete=SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True
    )
    job_build_list_item = models.ForeignKey(
        JobBuildListItem, 
        on_delete=SET_NULL, 
        related_name="time_entries", 
        null=True, 
        blank=True
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    percent_complete = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        if self.user:
            name = self.user.get_full_name() or self.user.username
            return f"{name} - {self.job} ({self.start_time})"
        return f"(No User) - {self.job} ({self.start_time})"


class JobAttachment(AuditMixin):
    """Files attached to a Job."""
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="attachments", null=True, blank=True)
    file = models.FileField(upload_to="job_attachments/%Y/%m/%d")
    original_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    file_type = models.CharField(max_length=50, null=True, blank=True)  # optional tagging

    def __str__(self):
        return f"{self.job} - {self.original_name or self.file.name}"


class JobNotification(AuditMixin):
    """Notifications for users related to jobs."""
    
    TYPE_CHOICES = [
        ('step_completed', 'Step Completed'),
        ('po_missing_on_close', 'PO Missing on Close'),
        ('generic', 'Generic'),
        ('team_message', 'Team Message'),
        ('reply', 'Reply'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=CASCADE, 
        related_name="job_notifications", 
        null=True, 
        blank=True
    )
    job = models.ForeignKey(Job, on_delete=CASCADE, related_name="notifications", null=True, blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    parent_notification = models.ForeignKey(
        'self',
        on_delete=SET_NULL,
        related_name='replies',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.type} - {self.job}"


class PurchaseOrder(AuditMixin):
    """Purchase Order model for tracking orders to vendors."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('net_30', 'Net 30'),
        ('net_60', 'Net 60'),
        ('cod', 'COD'),
        ('prepaid', 'Prepaid'),
        ('other', 'Other'),
    ]
    
    # Identification & Status
    po_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    po_date = models.DateField()
    
    # Vendor Information
    vendor = models.ForeignKey('inventory.Vendor', on_delete=PROTECT, related_name='purchase_orders', null=True, blank=True)
    vendor_contact = models.ForeignKey('inventory.VendorContact', on_delete=SET_NULL, null=True, blank=True, related_name='purchase_orders')
    vendor_po_number = models.CharField(max_length=100, null=True, blank=True)
    
    # Dates
    submitted_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    
    # Financial Fields
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    other_charges = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD', null=True, blank=True)
    
    # Terms & Shipping
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS_CHOICES, null=True, blank=True)
    shipping_method = models.CharField(max_length=100, null=True, blank=True)
    shipping_account_number = models.CharField(max_length=100, null=True, blank=True)
    
    # Shipping Address
    ship_to_name = models.CharField(max_length=255, null=True, blank=True)
    ship_to_address = models.CharField(max_length=255, null=True, blank=True)
    ship_to_city = models.CharField(max_length=100, null=True, blank=True)
    ship_to_state = models.CharField(max_length=50, null=True, blank=True)
    ship_to_zip = models.CharField(max_length=20, null=True, blank=True)
    ship_to_phone = models.CharField(max_length=50, null=True, blank=True)
    
    # Tracking & Notes
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    carrier = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    vendor_notes = models.TextField(null=True, blank=True)
    receiving_notes = models.TextField(null=True, blank=True)
    
    # Flags
    is_urgent = models.BooleanField(default=False)
    is_drop_ship = models.BooleanField(default=False)
    
    # Requestor
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=SET_NULL, 
        null=True, 
        blank=True, 
        related_name='requested_pos'
    )

    class Meta:
        ordering = ['-po_date', '-created_at']

    def __str__(self):
        return f"PO {self.po_number} - {self.vendor}"


class PurchaseOrderItem(AuditMixin):
    """Line items on a Purchase Order."""
    
    STATUS_CHOICES = [
        ('ordered', 'Ordered'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('backordered', 'Backordered'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Relationships
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=CASCADE, related_name='items')
    part = models.ForeignKey('inventory.Part', on_delete=PROTECT, related_name='po_items', null=True, blank=True)
    job = models.ForeignKey(Job, on_delete=SET_NULL, null=True, blank=True, related_name='po_items')
    job_part = models.ForeignKey(JobPart, on_delete=SET_NULL, null=True, blank=True, related_name='po_items')
    
    # Quantities
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_backordered = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_cancelled = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, null=True, blank=True)
    
    # Financial Fields
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_taxable = models.BooleanField(default=True)
    
    # Item Details (Snapshot from Part at time of PO creation)
    part_number = models.CharField(max_length=100, null=True, blank=True)
    part_name = models.CharField(max_length=255, null=True, blank=True)
    vendor_part_number = models.CharField(max_length=120, null=True, blank=True)
    manufacturer = models.CharField(max_length=100, null=True, blank=True)
    
    # Status & Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered')
    expected_date = models.DateField(null=True, blank=True)
    
    # Notes
    line_notes = models.TextField(null=True, blank=True)
    
    # Ordering
    sort_order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.part_number or self.part_name}"
    
    @property
    def quantity_remaining(self):
        """Calculate quantity still to be received."""
        return self.quantity_ordered - self.quantity_received - self.quantity_cancelled


class PurchaseOrderReceiving(AuditMixin):
    """Receiving log for tracking partial receives of PO items."""
    
    CONDITION_CHOICES = [
        ('good', 'Good'),
        ('damaged', 'Damaged'),
        ('wrong_item', 'Wrong Item'),
        ('incomplete', 'Incomplete'),
    ]
    
    # Relationships
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=CASCADE, related_name='receives')
    
    # Receiving Details
    received_date = models.DateTimeField()
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=SET_NULL, 
        null=True, 
        blank=True, 
        related_name='po_receives'
    )
    
    # Condition & Location
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    received_location = models.CharField(max_length=255, null=True, blank=True)
    
    # Notes
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-received_date']

    def __str__(self):
        return f"{self.purchase_order_item.purchase_order.po_number} - {self.quantity_received} received on {self.received_date.strftime('%Y-%m-%d')}"


class PurchaseOrderAttachment(AuditMixin):
    """Files attached to a Purchase Order."""
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=CASCADE, related_name='attachments')
    file = models.FileField(upload_to='po_attachments/%Y/%m/%d')
    original_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    file_type = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.original_name or self.file.name}"
