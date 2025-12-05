from django import forms
from .models import Job, Customer, CustomerShipToAddress, JobComponent, JobSelectionOption, JobTime, PurchaseOrder, PurchaseOrderItem
from inventory.models import Engine


class EngineQuickCreateForm(forms.ModelForm):
    """Form for quickly creating engines from job tickets."""
    
    # Add stamped_number as a custom field since it's job-specific
    stamped_number = forms.CharField(
        max_length=255, 
        required=False, 
        label='Stamped Number',
        help_text='Engine stamped number (stored on job)'
    )
    
    class Meta:
        model = Engine
        fields = [
            'engine_make',
            'engine_model',
            'identifier',
            'serial_number',
            'injection_type',
        ]
        labels = {
            'identifier': 'Engine Identifier',
            'serial_number': 'Serial Number',
            'injection_type': 'Injection Type',
        }
        widgets = {
            'engine_make': forms.TextInput(attrs={'required': True}),
            'engine_model': forms.TextInput(attrs={'required': True}),
            'injection_type': forms.TextInput(attrs={'placeholder': 'e.g., DI, IDI'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make engine_make and engine_model required
        self.fields['engine_make'].required = True
        self.fields['engine_model'].required = True


class CustomerForm(forms.ModelForm):
    """Form for creating and updating customers."""
    
    class Meta:
        model = Customer
        fields = [
            'name',
            'email',
            'phone',
            'bill_to_name',
            'bill_to_address',
            'bill_to_city',
            'bill_to_state',
            'bill_to_zip',
            'default_price_setting',
            'default_terms',
        ]


class CustomerShipToAddressForm(forms.ModelForm):
    """Form for creating and updating ship-to addresses."""
    
    class Meta:
        model = CustomerShipToAddress
        fields = [
            'name',
            'address',
            'city',
            'state',
            'zip',
            'is_default',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Warehouse 1, Main Office'}),
        }


class JobTicketForm(forms.ModelForm):
    """Form for creating and updating job tickets."""
    
    class Meta:
        model = Job
        fields = [
            'date',
            'status',
            'store',
            'finish_date',
            # customer removed - will be set via modal
            'customer_po',
            'sales_person',
            'price_setting',
            'terms',
            'invoice_date',
            'notes',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'finish_date': forms.DateInput(attrs={'type': 'date'}),
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use ticket-specific status choices (Draft, Ready for Review)
        self.fields['status'].choices = [('', '---------')] + list(Job.TICKET_STATUS_CHOICES)


class JobComponentForm(forms.ModelForm):
    """Form for job component information."""
    
    class Meta:
        model = JobComponent
        fields = [
            'block', 'block_mb_caps', 'block_cam',
            'head', 'head_vs', 'head_bare',
            'crankshaft',
            'waterpump',
            'rods', 'rods_fractured', 'rods_machined', 'rods_qty',
            'pistons', 'pistons_part_number', 'pistons_qty',
            'flywheel', 'flywheel_stepped', 'flywheel_flat',
            'manifold', 'manifold_pieces', 'manifold_diameter',
        ]
        widgets = {
            'pistons_part_number': forms.TextInput(attrs={'placeholder': 'Part #', 'size': 20}),
            'rods_qty': forms.NumberInput(attrs={'placeholder': 'Qty', 'min': 0, 'style': 'width: 80px;'}),
            'pistons_qty': forms.NumberInput(attrs={'placeholder': 'Qty', 'min': 0, 'style': 'width: 80px;'}),
            'manifold_diameter': forms.NumberInput(attrs={'placeholder': 'Diameter', 'step': '0.001', 'style': 'width: 100px;'}),
        }


class JobSelectionOptionForm(forms.ModelForm):
    """Form for creating and updating job selection options."""
    
    class Meta:
        model = JobSelectionOption
        fields = ['name', 'group', 'part', 'kit', 'build_list', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Option name'}),
            'sort_order': forms.NumberInput(attrs={'min': 0}),
        }


class TimeEntryForm(forms.ModelForm):
    """Form for editing time entries."""
    
    class Meta:
        model = JobTime
        fields = ['start_time', 'end_time', 'description']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this time entry'}),
        }
        labels = {
            'start_time': 'Start Time',
            'end_time': 'End Time',
            'description': 'Notes',
        }


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating and updating purchase orders."""
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'status',
            'po_date',
            'submitted_date',
            'expected_delivery_date',
            'actual_delivery_date',
            'vendor_contact',
            'vendor_po_number',
            'subtotal',
            'tax_rate',
            'tax_amount',
            'shipping_cost',
            'other_charges',
            'discount_amount',
            'total_amount',
            'payment_terms',
            'shipping_method',
            'shipping_account_number',
            'ship_to_name',
            'ship_to_address',
            'ship_to_city',
            'ship_to_state',
            'ship_to_zip',
            'ship_to_phone',
            'tracking_number',
            'carrier',
            'notes',
            'vendor_notes',
            'receiving_notes',
            'is_urgent',
            'is_drop_ship',
            'requested_by',
        ]
        widgets = {
            'po_date': forms.DateInput(attrs={'type': 'date'}),
            'submitted_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Internal notes'}),
            'vendor_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes for vendor'}),
            'receiving_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Receiving notes'}),
            'subtotal': forms.NumberInput(attrs={'step': '0.01', 'readonly': True}),
            'total_amount': forms.NumberInput(attrs={'step': '0.01', 'readonly': True}),
            'tax_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'tax_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'shipping_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'other_charges': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'discount_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    """Form for PO item validation (not used in modal, but for backend validation)."""
    
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'part',
            'quantity_ordered',
            'unit_price',
            'line_notes',
            'expected_date',
        ]
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'expected_date': forms.DateInput(attrs={'type': 'date'}),
            'line_notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Notes for this line item'}),
        }

