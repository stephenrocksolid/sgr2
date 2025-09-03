from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint, Index
from django.db.models.functions import Lower
from core.models import AuditMixin
from decimal import Decimal


def recalc_kit_totals(kit):
    """Recalculate kit cost_total and sale_price based on items and margin."""
    from django.db import transaction
    
    with transaction.atomic():
        # Calculate total cost from items
        cost_total = Decimal('0.00')
        for item in kit.items.all():
            cost_total += item.unit_cost * item.quantity
        
        # Calculate sale price with margin
        margin_multiplier = Decimal('1.00') + (kit.margin_pct / Decimal('100.00'))
        sale_price = cost_total * margin_multiplier
        
        # Update kit totals
        kit.cost_total = cost_total
        kit.sale_price = sale_price
        kit.save(update_fields=['cost_total', 'sale_price'])
        
        return cost_total, sale_price


class PartCategory(models.Model):
    """Category for organizing parts with custom attributes."""
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    
    def __str__(self):
        return self.name


class PartAttribute(models.Model):
    """Attribute definition for a part category."""
    class DataType(models.TextChoices):
        TEXT = 'text', 'Text'
        INTEGER = 'int', 'Integer'
        DECIMAL = 'dec', 'Decimal'
        BOOLEAN = 'bool', 'Boolean'
        DATE = 'date', 'Date'
        CHOICE = 'choice', 'Choice'
    
    category = models.ForeignKey('PartCategory', on_delete=models.CASCADE, related_name='attributes')
    name = models.CharField(max_length=120)  # e.g. "Thread Size"
    code = models.SlugField(max_length=140)  # e.g. "thread_size"
    data_type = models.CharField(max_length=10, choices=DataType.choices)
    unit = models.CharField(max_length=40, blank=True)  # optional display unit
    is_required = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    help_text = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = (('category', 'code'),)
        ordering = ('sort_order', 'name')
    
    def __str__(self):
        return f'{self.category}:{self.name}'


class PartAttributeChoice(models.Model):
    """Choice options for CHOICE type attributes."""
    attribute = models.ForeignKey('PartAttribute', on_delete=models.CASCADE, related_name='choices')
    value = models.CharField(max_length=120)  # stored value
    label = models.CharField(max_length=120)  # display label
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = (('attribute', 'value'),)
        ordering = ('sort_order', 'label')
    
    def __str__(self):
        return self.label


class PartAttributeValue(models.Model):
    """EAV values for part attributes with type-specific columns."""
    part = models.ForeignKey('Part', on_delete=models.CASCADE, related_name='attribute_values')
    attribute = models.ForeignKey('PartAttribute', on_delete=models.CASCADE, related_name='values')
    # One of these will be populated depending on attribute.data_type:
    value_text = models.CharField(max_length=255, blank=True, null=True)
    value_int = models.BigIntegerField(blank=True, null=True)
    value_dec = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    value_bool = models.BooleanField(blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    choice = models.ForeignKey('PartAttributeChoice', blank=True, null=True, on_delete=models.SET_NULL)
    
    class Meta:
        unique_together = (('part', 'attribute'),)
        indexes = [
            models.Index(fields=['attribute', 'value_text']),
            models.Index(fields=['attribute', 'value_int']),
            models.Index(fields=['attribute', 'value_dec']),
            models.Index(fields=['attribute', 'value_bool']),
            models.Index(fields=['attribute', 'value_date']),
            models.Index(fields=['attribute', 'choice']),
        ]


class SGEngine(AuditMixin):
    """Spring Garden Engine model."""
    sg_make = models.CharField(max_length=100)
    sg_model = models.CharField(max_length=100)
    identifier = models.CharField(max_length=100, unique=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['sg_make', 'sg_model'],
                name='unique_sg_engine_make_model',
                violation_error_message='SG Engine with this make and model already exists.'
            )
        ]
        indexes = [
            Index(Lower('sg_make'), name='sg_engine_make_lower_idx'),
            Index(Lower('sg_model'), name='sg_engine_model_lower_idx'),
        ]

    def __str__(self):
        return f"{self.sg_make} {self.sg_model}"


class Engine(AuditMixin):
    """Engine model with specifications."""
    sg_engine = models.ForeignKey(SGEngine, on_delete=models.SET_NULL, null=True, blank=True)
    engine_make = models.CharField(max_length=100)
    engine_model = models.CharField(max_length=100)
    sg_engine_identifier = models.CharField(max_length=100, blank=True)
    sg_engine_notes = models.TextField(blank=True)
    
    # Specifications
    cpl_number = models.CharField(max_length=50, blank=True)
    ar_number = models.CharField(max_length=50, blank=True)
    build_list = models.CharField(max_length=100, blank=True)
    engine_code = models.CharField(max_length=50, blank=True)
    
    # Components
    crankshaft_no = models.CharField(max_length=50, blank=True)
    piston_no = models.CharField(max_length=50, blank=True)
    piston_marked_no = models.CharField(max_length=50, blank=True)
    piston_notes = models.TextField(blank=True)
    
    # Service
    oh_kit_no = models.CharField(max_length=50, blank=True)
    
    # Geometry
    cylinder = models.PositiveIntegerField(null=True, blank=True)
    valves_per_cyl = models.PositiveIntegerField(null=True, blank=True)
    bore_stroke = models.CharField(max_length=50, blank=True)
    compression_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    firing_order = models.CharField(max_length=50, blank=True)
    
    # Overview
    overview_comments = models.TextField(blank=True)
    interference = models.CharField(max_length=100, blank=True)
    camshaft = models.CharField(max_length=100, blank=True)
    valve_adjustment = models.CharField(max_length=100, blank=True)
    
    # Journals
    rod_journal_diameter = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    main_journal_diameter_pos1 = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    main_journal_diameter_1 = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    big_end_housing_bore = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    
    # Price and status
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=100, blank=True)
    
    # Serial Number
    serial_number = models.CharField(max_length=120, blank=True, null=True, db_index=True, verbose_name="S/N")
    
    # Injection System
    di = models.BooleanField(default=False, verbose_name="DI (Direct Injection)")
    idi = models.BooleanField(default=False, verbose_name="IDI (Indirect Injection)")
    common_rail = models.BooleanField(default=False, verbose_name="Common Rail")
    
    # Valve Configuration
    two_valve = models.BooleanField(default=False, verbose_name="2V (2 Valve)")
    four_valve = models.BooleanField(default=False, verbose_name="4V (4 Valve)")
    five_valve = models.BooleanField(default=False, verbose_name="5V (5 Valve)")
    
    # Casting Information
    casting_comments = models.TextField(blank=True, null=True, verbose_name="Casting # Comments")
    
    # Engine relationships
    interchanges = models.ManyToManyField(
        'self',
        symmetrical=True,
        blank=True
    )
    compatibles = models.ManyToManyField(
        'self',
        symmetrical=True,
        blank=True
    )

    class Meta:
        indexes = [
            Index(Lower('engine_make'), name='engine_make_lower_idx'),
            Index(Lower('engine_model'), name='engine_model_lower_idx'),
            Index(Lower('cpl_number'), name='engine_cpl_number_lower_idx'),
        ]

    def __str__(self):
        base_name = f"{self.engine_make} {self.engine_model}"
        if self.serial_number:
            return f"{base_name} (SN: {self.serial_number})"
        return base_name
    
    @property
    def valves_display(self):
        """Display valve configuration flags."""
        flags = []
        if self.two_valve: flags.append("2V")
        if self.four_valve: flags.append("4V")
        if self.five_valve: flags.append("5V")
        return ", ".join(flags) or "-"
    
    @property
    def supersedes(self):
        """Engines that this engine supersedes (this engine is newer than them)"""
        return Engine.objects.filter(supersedes_links__from_engine=self)
    
    @property
    def superseded_by(self):
        """Engines that supersede this engine (this engine is older than them)"""
        return Engine.objects.filter(superseded_by_links__to_engine=self)
    
    def get_or_create_build_list(self):
        """Get or create the single build list for this engine."""
        bl = getattr(self, '_cached_bl', None)
        if bl:
            return bl
        bl, _ = self.build_lists.get_or_create(
            defaults={'name': 'Default Build List', 'notes': ''}
        )
        self._cached_bl = bl
        return bl


class EngineSupercession(AuditMixin):
    """Through model for Engine supersession relationships."""
    from_engine = models.ForeignKey('Engine', on_delete=models.CASCADE, related_name='superseded_by_links')
    to_engine = models.ForeignKey('Engine', on_delete=models.CASCADE, related_name='supersedes_links')
    notes = models.TextField(blank=True)
    effective_date = models.DateField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['from_engine', 'to_engine'], name='unique_supercession')
        ]
    
    def __str__(self):
        return f"{self.from_engine} → {self.to_engine}"


class Machine(AuditMixin):
    """Machine model."""
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    machine_type = models.CharField(max_length=100)
    market_type = models.CharField(max_length=100)
    engines = models.ManyToManyField(Engine, through='MachineEngine')
    parts = models.ManyToManyField('Part', through='MachinePart')

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['make', 'model', 'year', 'machine_type', 'market_type'],
                name='unique_machine_key',
                violation_error_message='Machine with this combination already exists.'
            )
        ]
        indexes = [
            Index(Lower('make'), name='machine_make_lower_idx'),
            Index(Lower('model'), name='machine_model_lower_idx'),
            Index(Lower('machine_type'), name='machine_type_lower_idx'),
            Index(Lower('market_type'), name='machine_market_type_lower_idx'),
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class MachineEngine(AuditMixin):
    """Through model for Machine-Engine relationship."""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    engine = models.ForeignKey(Engine, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['machine', 'engine'],
                name='unique_machine_engine',
                violation_error_message='This machine-engine combination already exists.'
            )
        ]

    def __str__(self):
        return f"{self.machine} - {self.engine}"


class MachinePart(AuditMixin):
    """Through model for Machine-Part relationship."""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    part = models.ForeignKey('Part', on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['machine', 'part'],
                name='unique_machine_part',
                violation_error_message='This machine-part combination already exists.'
            )
        ]

    def __str__(self):
        return f"{self.machine} - {self.part}"


class Vendor(AuditMixin):
    """Vendor model."""
    name = models.CharField(max_length=200, unique=True)
    contact_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            Index(Lower('name'), name='vendor_name_lower_idx'),
        ]

    def __str__(self):
        return self.name


class Part(AuditMixin):
    """Part model."""
    part_number = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    category = models.ForeignKey('PartCategory', null=True, blank=True, on_delete=models.SET_NULL, related_name='parts')
    manufacturer = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    type = models.CharField(max_length=100, blank=True)
    manufacturer_type = models.CharField(max_length=100, blank=True)
    primary_vendor = models.ForeignKey(
        Vendor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='primary_parts'
    )
    
    # Many-to-many relationships
    engines = models.ManyToManyField(Engine, through='EnginePart')
    machines = models.ManyToManyField('Machine', through='MachinePart')
    vendors = models.ManyToManyField(Vendor, through='PartVendor', related_name='supplied_parts')

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['part_number', 'name'],
                name='unique_part_number_name',
                violation_error_message='Part with this number and name already exists.'
            )
        ]
        indexes = [
            Index(Lower('part_number'), name='part_number_lower_idx'),
            Index(Lower('name'), name='part_name_lower_idx'),
            Index(Lower('manufacturer'), name='part_manufacturer_lower_idx'),
        ]

    def __str__(self):
        return f"{self.part_number} - {self.name}"
    
    @property
    def vendor_offers(self):
        return self.vendor_links.select_related('vendor').all()


class EnginePart(AuditMixin):
    """Through model for Engine-Part relationship."""
    engine = models.ForeignKey(Engine, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['engine', 'part'],
                name='unique_engine_part',
                violation_error_message='This engine-part combination already exists.'
            )
        ]

    def __str__(self):
        return f"{self.engine} - {self.part}"


class PartVendor(AuditMixin):
    """Through model for Part-Vendor relationship."""
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="vendor_links")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="part_links")
    vendor_sku = models.CharField(max_length=120, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_qty = models.IntegerField(null=True, blank=True)
    lead_time_days = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("part", "vendor")]
        ordering = ["vendor__name"]

    def __str__(self):
        return f"{self.part} - {self.vendor}"


class BuildList(models.Model):
    """Build list for an engine containing multiple kits."""
    engine = models.ForeignKey('Engine', on_delete=models.CASCADE, related_name='build_lists')
    name = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['engine'], name='unique_buildlist_per_engine')
        ]
    
    def __str__(self):
        return f'{self.engine} — {self.name}'


class Kit(models.Model):
    """Kit within a build list containing multiple parts."""
    build_list = models.ForeignKey('BuildList', on_delete=models.CASCADE, related_name='kits')
    name = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    # Pricing controls:
    margin_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # e.g., 25.00 = 25%
    # Cached rollups (updated on save or via service):
    cost_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)  # sum of items (unit_cost * qty)
    sale_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)  # computed from cost_total + margin
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.build_list}: {self.name}'
    
    def recalc_totals(self):
        """Recalculate and update cost_total and sale_price."""
        return recalc_kit_totals(self)
    
    def get_items_count(self):
        """Get the number of items in this kit."""
        return self.items.count()


class KitItem(models.Model):
    """Individual part within a kit with vendor and pricing information."""
    kit = models.ForeignKey('Kit', on_delete=models.CASCADE, related_name='items')
    part = models.ForeignKey('Part', on_delete=models.PROTECT, related_name='kit_items')
    vendor = models.ForeignKey('Vendor', on_delete=models.PROTECT, related_name='kit_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    # Snapshot unit cost at the time of adding (so totals don't change unexpectedly if vendor cost updates later)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = (('kit', 'part', 'vendor'),)
    
    def __str__(self):
        return f'{self.kit}: {self.part} ({self.vendor})'
    
    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.quantity is None:
            raise ValidationError({"quantity": "Quantity is required."})
        d = Decimal(self.quantity)
        if d != d.to_integral_value():
            raise ValidationError({"quantity": "Quantity must be a whole number."})
        if d <= 0:
            raise ValidationError({"quantity": "Quantity must be at least 1."})
