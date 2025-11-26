from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint, Index
from django.db.models.functions import Lower
from core.models import AuditMixin
from decimal import Decimal


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
    sg_make = models.CharField(max_length=100, null=True, blank=True)
    sg_model = models.CharField(max_length=100, null=True, blank=True)
    identifier = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            Index(Lower('sg_make'), name='sg_engine_make_lower_idx'),
            Index(Lower('sg_model'), name='sg_engine_model_lower_idx'),
        ]

    def __str__(self):
        make = self.sg_make or ""
        model = self.sg_model or ""
        return f"{make} {model}".strip() or "(No Make/Model)"


class Engine(AuditMixin):
    """Engine model with specifications."""
    sg_engine = models.ForeignKey(SGEngine, on_delete=models.SET_NULL, null=True, blank=True)
    engine_make = models.CharField(max_length=100, null=True, blank=True)
    engine_model = models.CharField(max_length=100, null=True, blank=True)
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
    identifier = models.CharField(max_length=100, blank=True, null=True, verbose_name="Identifier")
    
    # Engine characteristics - free text fields
    injection_type = models.CharField(max_length=50, blank=True, verbose_name="Injection Type")
    valve_config = models.CharField(max_length=50, blank=True, verbose_name="Valve Configuration")
    fuel_system_type = models.CharField(max_length=50, blank=True, verbose_name="Fuel System Type")
    
    # Engine relationships
    vendor = models.ForeignKey('Vendor', null=True, blank=True, on_delete=models.SET_NULL, related_name='engines')
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
        make = self.engine_make or ""
        model = self.engine_model or ""
        base_name = f"{make} {model}".strip() or "(No Make/Model)"
        if self.serial_number:
            return f"{base_name} (SN: {self.serial_number})"
        return base_name
    
    @property
    def supersedes(self):
        """Engines that this engine supersedes (this engine is newer than them)"""
        return Engine.objects.filter(supersedes_links__from_engine=self)
    
    @property
    def superseded_by(self):
        """Engines that supersede this engine (this engine is older than them)"""
        return Engine.objects.filter(superseded_by_links__to_engine=self)
    

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
    make = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    machine_type = models.CharField(max_length=100, null=True, blank=True)
    market_type = models.CharField(max_length=100, null=True, blank=True)
    engines = models.ManyToManyField(Engine, through='MachineEngine')
    parts = models.ManyToManyField('Part', through='MachinePart')

    class Meta:
        indexes = [
            Index(Lower('make'), name='machine_make_lower_idx'),
            Index(Lower('model'), name='machine_model_lower_idx'),
            Index(Lower('machine_type'), name='machine_type_lower_idx'),
            Index(Lower('market_type'), name='machine_market_type_lower_idx'),
        ]

    def __str__(self):
        year = self.year or ""
        make = self.make or ""
        model = self.model or ""
        return f"{year} {make} {model}".strip() or "(No Info)"


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


class SGVendor(models.Model):
    """Canonical Spring Garden Vendor model for unifying vendor names."""
    name = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["name"]
        indexes = [
            Index(Lower('name'), name='idx_sgvendor_lower_name'),
        ]
    
    def __str__(self):
        return self.name or "(No Name)"


class Vendor(AuditMixin):
    """Vendor model."""
    name = models.CharField(max_length=200, null=True, blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    sg_vendor = models.ForeignKey('SGVendor', null=True, blank=True, on_delete=models.SET_NULL, related_name='vendors')

    class Meta:
        ordering = ["name"]
        indexes = [
            Index(Lower('name'), name='vendor_name_lower_idx'),
        ]

    def __str__(self):
        return self.name or "(No Name)"


class VendorContact(models.Model):
    """Vendor contact model for multiple contacts per vendor."""
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='contacts')
    full_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name', 'id']

    def __str__(self):
        return f"{self.full_name} ({self.vendor.name})"


class Part(AuditMixin):
    """Part model."""
    part_number = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    category = models.ForeignKey('PartCategory', null=True, blank=True, on_delete=models.SET_NULL, related_name='parts')
    manufacturer = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    type = models.CharField(max_length=100, blank=True)
    manufacturer_type = models.CharField(max_length=100, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Weight in pounds")
    primary_vendor = models.ForeignKey(
        Vendor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='primary_parts'
    )
    vendor = models.ForeignKey('Vendor', null=True, blank=True, on_delete=models.SET_NULL, related_name='parts')
    
    # Many-to-many relationships
    engines = models.ManyToManyField(Engine, through='EnginePart')
    machines = models.ManyToManyField('Machine', through='MachinePart')
    vendors = models.ManyToManyField(Vendor, through='PartVendor', related_name='supplied_parts')

    class Meta:
        indexes = [
            Index(Lower('part_number'), name='part_number_lower_idx'),
            Index(Lower('name'), name='part_name_lower_idx'),
            Index(Lower('manufacturer'), name='part_manufacturer_lower_idx'),
        ]

    def __str__(self):
        if self.part_number and self.name:
            return f"{self.part_number} - {self.name}"
        elif self.part_number:
            return self.part_number
        elif self.name:
            return self.name
        return "(No Part Number/Name)"
    
    @property
    def vendor_offers(self):
        return self.vendor_links.select_related('vendor').all()
    
    def auto_set_primary_vendor(self):
        """
        Automatically set primary_vendor if there's exactly one vendor.
        Always overrides existing primary_vendor if only 1 vendor exists.
        Returns True if primary_vendor was changed, False otherwise.
        """
        vendor_count = self.vendor_links.count()
        if vendor_count == 1:
            single_vendor = self.vendor_links.first().vendor
            if self.primary_vendor != single_vendor:
                self.primary_vendor = single_vendor
                self.save(update_fields=['primary_vendor'])
                return True
        elif vendor_count == 0:
            # Clear primary_vendor if no vendors exist
            if self.primary_vendor is not None:
                self.primary_vendor = None
                self.save(update_fields=['primary_vendor'])
                return True
        return False


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
    vendor_part_number = models.CharField(max_length=120, blank=True)
    vendor_sku = models.CharField(max_length=120, blank=True)  # Keep for backward compatibility
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Keep for backward compatibility
    stock_qty = models.IntegerField(null=True, blank=True)
    lead_time_days = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('part', 'vendor'),)
        indexes = [
            models.Index(fields=['part', 'vendor']),
        ]
        ordering = ["vendor__name"]

    def __str__(self):
        return f"{self.part_id} @ {self.vendor_id} (${self.price} / qty {self.stock_qty})"


class BuildList(models.Model):
    """Build list that can be assigned to multiple engines."""
    name = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    engines = models.ManyToManyField('Engine', related_name='build_lists', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+', blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class BuildListItem(models.Model):
    """Items within a build list."""
    build_list = models.ForeignKey('BuildList', on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    hour_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.build_list.name} - {self.name}"


class Kit(models.Model):
    """Kit containing multiple parts that can be assigned to multiple engines."""
    name = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    engines = models.ManyToManyField('Engine', related_name='kits', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+', blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class KitItem(models.Model):
    """Individual part within a kit with quantity."""
    kit = models.ForeignKey('Kit', on_delete=models.CASCADE, related_name='items')
    part = models.ForeignKey('Part', on_delete=models.PROTECT, related_name='kit_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        unique_together = (('kit', 'part'),)
        ordering = ['part__part_number']
    
    def __str__(self):
        return f'{self.kit}: {self.part}'
    
    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.quantity is None:
            raise ValidationError({"quantity": "Quantity is required."})
        if Decimal(str(self.quantity)) <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than 0."})


class Casting(models.Model):
    """Casting number entries for an engine."""
    engine = models.ForeignKey('Engine', on_delete=models.CASCADE, related_name='castings')
    casting_number = models.CharField(max_length=100)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['casting_number']
    
    def __str__(self):
        return f"{self.engine} - {self.casting_number}"
