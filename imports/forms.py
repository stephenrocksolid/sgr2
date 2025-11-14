from django import forms
from django.core.exceptions import ValidationError
from .models import ImportBatch, SavedImportMapping

class ImportFileUploadForm(forms.ModelForm):
    """Form for uploading import files."""
    
    class Meta:
        model = ImportBatch
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.csv,.xlsx,.xls',
                'id': 'import-file'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("Please select a file to upload.")
        
        # Check file size (50MB limit)
        if file.size > 50 * 1024 * 1024:
            raise ValidationError("File size must be less than 50MB.")
        
        # Check file extension
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_extension = file.name.lower()
        if not any(file_extension.endswith(ext) for ext in allowed_extensions):
            raise ValidationError("Please upload a CSV or Excel file (.csv, .xlsx, .xls).")
        
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        
        # Set file_size on the instance if file is provided
        if file and hasattr(self, 'instance'):
            self.instance.file_size = file.size
        
        return cleaned_data

class CSVOptionsForm(forms.Form):
    """Form for CSV import options."""
    
    encoding = forms.ChoiceField(
        choices=[
            ('utf-8', 'UTF-8'),
            ('latin-1', 'Latin-1'),
            ('cp1252', 'Windows-1252'),
            ('iso-8859-1', 'ISO-8859-1'),
        ],
        initial='utf-8',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    delimiter = forms.ChoiceField(
        choices=[
            (',', 'Comma (,)'),
            (';', 'Semicolon (;)'),
            ('\t', 'Tab'),
            ('|', 'Pipe (|)'),
        ],
        initial=',',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class XLSXOptionsForm(forms.Form):
    """Form for XLSX import options."""
    
    worksheet_name = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        worksheet_choices = kwargs.pop('worksheet_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['worksheet_name'].choices = worksheet_choices

class ImportMappingForm(forms.Form):
    """Form for mapping import fields."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        section = kwargs.pop('section', 'machines')  # machines, engines, parts
        super().__init__(*args, **kwargs)
        
        # Define expected fields for each section
        section_fields = {
            'machines': [
                ('make', 'Make'),
                ('model', 'Model'),
                ('year', 'Year'),
                ('machine_type', 'Machine Type'),
                ('market_type', 'Market Type'),
                ('serial_number', 'Serial Number'),
                ('notes', 'Notes'),
            ],
            'engines': [
                # Core engine fields only
                ('engine_make', 'Engine Make'),
                ('engine_model', 'Engine Model'),
                ('engine_identifier', 'Engine Identifier'),
            ],
            'parts': [
                ('part_number', 'Part Number'),
                ('name', 'Name'),
                ('manufacturer', 'Manufacturer'),
                ('category', 'Category'),
                ('description', 'Description'),
                ('weight', 'Weight'),
                ('notes', 'Notes'),
            ]
        }
        
        # Create choice field for each expected field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in section_fields.get(section, []):
            self.fields[f'map_{section}_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        
        # For engines section, expose core keys for template grouping
        if section == 'engines':
            self.engine_core_keys = [f'map_engines_{field_name}' for field_name, _ in section_fields['engines']]
            # Everything else that starts with 'map_engines_' but not core → goes to More Engine Fields
            self.engine_more_keys = [k for k in self.fields.keys()
                                   if k.startswith('map_engines_') and k not in self.engine_core_keys]

class AdditionalEngineMappingForm(forms.Form):
    """Form for mapping additional engine fields."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        super().__init__(*args, **kwargs)
        
        # Define additional engine fields (moved from main engine form + existing additional fields)
        additional_engine_fields = [
            # Fields moved from main engine form
            ('status', 'Status'),
            ('notes', 'Notes'),
            
            # Specifications
            ('cpl_number', 'CPL Number'),
            ('ar_number', 'AR Number'),
            ('build_list', 'Build List'),
            ('engine_code', 'Engine Code'),
            ('serial_number', 'S/N (Serial Number)'),
            ('cylinder', 'Cylinders'),
            ('valves_per_cyl', 'Valves per Cylinder'),
            ('bore_stroke', 'Bore & Stroke'),
            ('compression_ratio', 'Compression Ratio'),
            ('firing_order', 'Firing Order'),
            
            # Components
            ('crankshaft_no', 'Crankshaft Number'),
            ('piston_no', 'Piston Number'),
            ('piston_marked_no', 'Piston Marked Number'),
            ('piston_notes', 'Piston Notes'),
            ('oh_kit_no', 'Overhaul Kit Number'),
            
            # Injection System
            ('di', 'DI (Direct Injection)'),
            ('idi', 'IDI (Indirect Injection)'),
            ('common_rail', 'Common Rail'),
            
            # Valve Configuration
            ('two_valve', '2V (2 Valve)'),
            ('four_valve', '4V (4 Valve)'),
            ('five_valve', '5V (5 Valve)'),
            
            # Overview
            ('overview_comments', 'Overview Comments'),
            ('interference', 'Interference'),
            ('camshaft', 'Camshaft'),
            ('valve_adjustment', 'Valve Adjustment'),
            
            # Journals
            ('rod_journal_diameter', 'Rod Journal Diameter'),
            ('main_journal_diameter_pos1', 'Main Journal Diameter (Pos 1)'),
            ('main_journal_diameter_1', 'Main Journal Diameter (1)'),
            ('big_end_housing_bore', 'Big End Housing Bore'),
            
            # Price
            ('price', 'Price'),
        ]
        
        # Create choice field for each additional engine field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in additional_engine_fields:
            self.fields[f'map_engines_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        
        # Expose all additional engine field keys for template grouping
        self.engine_more_keys = [f'map_engines_{field_name}' for field_name, _ in additional_engine_fields]

class VendorMappingForm(forms.Form):
    """Form for mapping vendor fields."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        super().__init__(*args, **kwargs)
        
        # Define vendor fields
        vendor_fields = [
            ('vendor_name', 'Vendor Name'),
            ('vendor_website', 'Vendor Website'),
            ('vendor_contact_name', 'Vendor Contact Name'),
            ('vendor_contact_email', 'Vendor Contact Email'),
            ('vendor_contact_phone', 'Vendor Contact Phone'),
            ('vendor_notes', 'Vendor Notes'),
            ('vendor_part_number', 'Vendor Part Number'),
            ('vendor_price', 'Vendor Price'),
            ('vendor_stock_qty', 'Vendor Stock Qty'),
        ]
        
        # Create choice field for each vendor field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in vendor_fields:
            self.fields[f'map_vendors_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        
        # Add option to create missing vendors
        self.fields['create_missing_vendors'] = forms.BooleanField(
            required=False,
            initial=True,
            label='Create vendors that do not exist',
            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
        )

class SavedMappingForm(forms.ModelForm):
    """Form for saving import mappings."""
    
    class Meta:
        model = SavedImportMapping
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a name for this mapping'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of this mapping'
            })
        }

class BuildListMappingForm(forms.Form):
    """Form for mapping build list fields."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        super().__init__(*args, **kwargs)
        
        # Define build list fields
        buildlist_fields = [
            ('name', 'Build List Name'),
            ('notes', 'Build List Notes'),
        ]
        
        # Create choice field for each build list field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in buildlist_fields:
            self.fields[f'map_buildlists_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )

class BuildListItemMappingForm(forms.Form):
    """Form for mapping build list item fields."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        super().__init__(*args, **kwargs)
        
        # Define build list item fields
        buildlistitem_fields = [
            ('name', 'Item Name'),
            ('description', 'Item Description'),
            ('hour_qty', 'Hour Quantity'),
        ]
        
        # Create choice field for each build list item field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in buildlistitem_fields:
            self.fields[f'map_buildlistitems_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )

class KitMappingForm(forms.Form):
    """Form for mapping kit fields."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        super().__init__(*args, **kwargs)
        
        # Define kit fields
        kit_fields = [
            ('name', 'Kit Name'),
            ('notes', 'Kit Notes'),
        ]
        
        # Create choice field for each kit field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in kit_fields:
            self.fields[f'map_kits_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )

class KitItemMappingForm(forms.Form):
    """Form for mapping kit item fields (including part fields for auto-creation)."""
    
    def __init__(self, *args, **kwargs):
        discovered_headers = kwargs.pop('discovered_headers', [])
        super().__init__(*args, **kwargs)
        
        # Define kit item fields and part fields for auto-creation
        kititem_fields = [
            # Kit item specific
            ('part_number', 'Part Number (Required)'),
            ('quantity', 'Quantity'),
            # Part fields for auto-creation when part doesn't exist
            ('part_name', 'Part Name (for auto-creation)'),
            ('part_category', 'Part Category (for auto-creation)'),
            ('part_manufacturer', 'Part Manufacturer (for auto-creation)'),
            ('part_unit', 'Part Unit (for auto-creation)'),
            ('part_type', 'Part Type (for auto-creation)'),
            ('part_manufacturer_type', 'Part Manufacturer Type (for auto-creation)'),
            ('part_weight', 'Part Weight (for auto-creation)'),
        ]
        
        # Create choice field for each kit item field
        header_choices = [('', '-- Select Header --')] + [(h, h) for h in sorted(discovered_headers)]
        
        for field_name, field_label in kititem_fields:
            self.fields[f'map_kititems_{field_name}'] = forms.ChoiceField(
                choices=header_choices,
                required=False,
                label=field_label,
                widget=forms.Select(attrs={'class': 'form-control'})
            )

class ProcessingOptionsForm(forms.Form):
    """Form for import processing options."""
    
    chunk_size = forms.IntegerField(
        min_value=100,
        max_value=10000,
        initial=1000,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Number of rows to process in each batch (smaller chunks for large files)"
    )
    
    skip_duplicates = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Skip rows that would create duplicate records. Duplicates are detected by (Engine Make, Engine Model, Engine Identifier)."
    )
    
    update_existing = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Update existing records instead of skipping them"
    )
