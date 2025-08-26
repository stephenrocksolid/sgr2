from django import forms
from .models import SGEngine, MachineEngine, Engine, MachinePart, Part, EnginePart, Machine, KitItem, PartAttribute, PartAttributeValue, Vendor, PartVendor
from decimal import Decimal, InvalidOperation


class SGEngineForm(forms.ModelForm):
    """Form for creating and editing SG Engines."""
    
    # Define the make-model relationships
    MODEL_TO_MAKE_MAPPING = {
        '8N': 'Ford',
        '9N': 'Ford',
        '2N': 'Ford',
        '1066': 'International Harvester',
        '1086': 'International Harvester',
        '1486': 'International Harvester',
        '1586': 'International Harvester',
        '886': 'International Harvester',
        '986': 'International Harvester',
        'A': 'John Deere',
        'B': 'John Deere',
        'G': 'John Deere',
        'H': 'John Deere',
        'M': 'John Deere',
        'R': 'John Deere',
        '60': 'John Deere',
        '70': 'John Deere',
        '80': 'John Deere',
        '4020': 'John Deere',
        '4040': 'John Deere',
        '4050': 'John Deere',
        '4230': 'John Deere',
        '4240': 'John Deere',
        '4250': 'John Deere',
        '4430': 'John Deere',
        '4440': 'John Deere',
        '4450': 'John Deere',
        '4630': 'John Deere',
        '4640': 'John Deere',
        '4650': 'John Deere',
        '4840': 'John Deere',
        '4850': 'John Deere',
        '4955': 'John Deere',
        '4960': 'John Deere',
        '5055': 'John Deere',
        '5060': 'John Deere',
        '5075': 'John Deere',
        '5080': 'John Deere',
        '5090': 'John Deere',
        '5100': 'John Deere',
        '5200': 'John Deere',
        '5300': 'John Deere',
        '5400': 'John Deere',
        '5500': 'John Deere',
        '5600': 'John Deere',
        '5700': 'John Deere',
        '5800': 'John Deere',
        '5900': 'John Deere',
        '6000': 'John Deere',
        '6100': 'John Deere',
        '6200': 'John Deere',
        '6300': 'John Deere',
        '6400': 'John Deere',
        '6500': 'John Deere',
        '6600': 'John Deere',
        '6700': 'John Deere',
        '6800': 'John Deere',
        '6900': 'John Deere',
        '7000': 'John Deere',
        '7100': 'John Deere',
        '7200': 'John Deere',
        '7300': 'John Deere',
        '7400': 'John Deere',
        '7500': 'John Deere',
        '7600': 'John Deere',
        '7700': 'John Deere',
        '7800': 'John Deere',
        '7900': 'John Deere',
        '8000': 'John Deere',
        '8100': 'John Deere',
        '8200': 'John Deere',
        '8300': 'John Deere',
        '8400': 'John Deere',
        '8500': 'John Deere',
        '8600': 'John Deere',
        '8700': 'John Deere',
        '8800': 'John Deere',
        '8900': 'John Deere',
        '9000': 'John Deere',
        '9100': 'John Deere',
        '9200': 'John Deere',
        '9300': 'John Deere',
        '9400': 'John Deere',
        '9500': 'John Deere',
        '9600': 'John Deere',
        '9700': 'John Deere',
        '9800': 'John Deere',
        '9900': 'John Deere',
    }
    
    # Define the model-identifier relationships
    MODEL_TO_IDENTIFIER_MAPPING = {
        '8N': 'FORD-8N-001',
        '9N': 'FORD-9N-001',
        '2N': 'FORD-2N-001',
        '1066': 'IH-1066-001',
        '1086': 'IH-1086-001',
        '1486': 'IH-1486-001',
        '1586': 'IH-1586-001',
        '886': 'IH-886-001',
        '986': 'IH-986-001',
        'A': 'JD-A-001',
        'B': 'JD-B-001',
        'G': 'JD-G-001',
        'H': 'JD-H-001',
        'M': 'JD-M-001',
        'R': 'JD-R-001',
        '60': 'JD-60-001',
        '70': 'JD-70-001',
        '80': 'JD-80-001',
        '4020': 'JD-4020-001',
        '4040': 'JD-4040-001',
        '4050': 'JD-4050-001',
        '4230': 'JD-4230-001',
        '4240': 'JD-4240-001',
        '4250': 'JD-4250-001',
        '4430': 'JD-4430-001',
        '4440': 'JD-4440-001',
        '4450': 'JD-4450-001',
        '4630': 'JD-4630-001',
        '4640': 'JD-4640-001',
        '4650': 'JD-4650-001',
        '4840': 'JD-4840-001',
        '4850': 'JD-4850-001',
        '4955': 'JD-4955-001',
        '4960': 'JD-4960-001',
        '5055': 'JD-5055-001',
        '5060': 'JD-5060-001',
        '5075': 'JD-5075-001',
        '5080': 'JD-5080-001',
        '5090': 'JD-5090-001',
        '5100': 'JD-5100-001',
        '5200': 'JD-5200-001',
        '5300': 'JD-5300-001',
        '5400': 'JD-5400-001',
        '5500': 'JD-5500-001',
        '5600': 'JD-5600-001',
        '5700': 'JD-5700-001',
        '5800': 'JD-5800-001',
        '5900': 'JD-5900-001',
        '6000': 'JD-6000-001',
        '6100': 'JD-6100-001',
        '6200': 'JD-6200-001',
        '6300': 'JD-6300-001',
        '6400': 'JD-6400-001',
        '6500': 'JD-6500-001',
        '6600': 'JD-6600-001',
        '6700': 'JD-6700-001',
        '6800': 'JD-6800-001',
        '6900': 'JD-6900-001',
        '7000': 'JD-7000-001',
        '7100': 'JD-7100-001',
        '7200': 'JD-7200-001',
        '7300': 'JD-7300-001',
        '7400': 'JD-7400-001',
        '7500': 'JD-7500-001',
        '7600': 'JD-7600-001',
        '7700': 'JD-7700-001',
        '7800': 'JD-7800-001',
        '7900': 'JD-7900-001',
        '8000': 'JD-8000-001',
        '8100': 'JD-8100-001',
        '8200': 'JD-8200-001',
        '8300': 'JD-8300-001',
        '8400': 'JD-8400-001',
        '8500': 'JD-8500-001',
        '8600': 'JD-8600-001',
        '8700': 'JD-8700-001',
        '8800': 'JD-8800-001',
        '8900': 'JD-8900-001',
        '9000': 'JD-9000-001',
        '9100': 'JD-9100-001',
        '9200': 'JD-9200-001',
        '9300': 'JD-9300-001',
        '9400': 'JD-9400-001',
        '9500': 'JD-9500-001',
        '9600': 'JD-9600-001',
        '9700': 'JD-9700-001',
        '9800': 'JD-9800-001',
        '9900': 'JD-9900-001',
    }
    
    class Meta:
        model = SGEngine
        fields = ['sg_make', 'sg_model', 'identifier']
        widgets = {
            'sg_make': forms.TextInput(attrs={'class': 'form-control'}),
            'sg_model': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        sg_model = cleaned_data.get('sg_model')
        sg_make = cleaned_data.get('sg_make')
        identifier = cleaned_data.get('identifier')
        
        # Auto-populate make based on model if not provided
        if sg_model and not sg_make:
            if sg_model in self.MODEL_TO_MAKE_MAPPING:
                cleaned_data['sg_make'] = self.MODEL_TO_MAKE_MAPPING[sg_model]
        
        # Auto-populate identifier based on model if not provided
        if sg_model and not identifier:
            if sg_model in self.MODEL_TO_IDENTIFIER_MAPPING:
                cleaned_data['identifier'] = self.MODEL_TO_IDENTIFIER_MAPPING[sg_model]
        
        return cleaned_data


class MachineEngineForm(forms.ModelForm):
    """Form for creating and editing Machine-Engine relationships."""
    
    class Meta:
        model = MachineEngine
        fields = ['engine', 'notes', 'is_primary']
        widgets = {
            'engine': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, machine=None, **kwargs):
        super().__init__(*args, **kwargs)
        if machine:
            # Filter engines to exclude those already linked to this machine
            self.fields['engine'].queryset = (
                Engine.objects
                .exclude(machineengine__machine=machine)
                .order_by('engine_make', 'engine_model')
            )
            self.fields['engine'].empty_label = "Select an engine…"


class MachinePartForm(forms.ModelForm):
    """Form for creating and editing Machine-Part relationships."""
    
    class Meta:
        model = MachinePart
        fields = ['part', 'notes', 'is_primary']
        widgets = {
            'part': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, machine=None, **kwargs):
        super().__init__(*args, **kwargs)
        if machine:
            # Filter parts to exclude those already linked to this machine
            self.fields['part'].queryset = (
                Part.objects
                .exclude(machinepart__machine=machine)
                .order_by('part_number', 'name')
            )
            self.fields['part'].empty_label = "Select a part…"


class EngineMachineForm(forms.ModelForm):
    """Form for creating and editing Engine-Machine relationships."""
    
    class Meta:
        model = MachineEngine
        fields = ['machine', 'notes', 'is_primary']
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EnginePartForm(forms.ModelForm):
    """Form for creating and editing Engine-Part relationships."""
    
    class Meta:
        model = EnginePart
        fields = ['part', 'notes']
        widgets = {
            'part': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class EngineInterchangeForm(forms.Form):
    """Form for adding engine interchanges."""
    interchange_engine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': 'required'
        })
    )
    
    def __init__(self, *args, engine=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine
        
        if engine:
            # Get SG Engines that are NOT already interchanged with this engine
            existing_interchange_sg_ids = engine.interchanges.filter(sg_engine__isnull=False).values_list('sg_engine_id', flat=True)
            available_sg_engines = SGEngine.objects.exclude(id__in=existing_interchange_sg_ids).order_by('sg_make', 'sg_model')
            
            # Set up SG Engine choices
            engine_choices = [('', 'Choose an SG Engine...')]
            for sg_engine in available_sg_engines:
                display_name = f"{sg_engine.sg_make} {sg_engine.sg_model} ({sg_engine.identifier})"
                engine_choices.append((sg_engine.id, display_name))
            
            self.fields['interchange_engine'].choices = engine_choices
    
    def clean(self):
        cleaned_data = super().clean()
        interchange_sg_engine_id = cleaned_data.get('interchange_engine')
        
        if interchange_sg_engine_id and self.engine:
            try:
                sg_engine = SGEngine.objects.get(id=interchange_sg_engine_id)
                # Check if this interchange relationship already exists
                if self.engine.interchanges.filter(sg_engine=sg_engine).exists():
                    raise forms.ValidationError("This SG Engine is already interchanged with the selected engine.")
            except SGEngine.DoesNotExist:
                raise forms.ValidationError("Selected SG Engine does not exist.")
        
        return cleaned_data


class EngineCompatibleForm(forms.Form):
    """Form for adding engine compatibles."""
    compatible_engine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': 'required'
        })
    )
    
    def __init__(self, *args, engine=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine
        
        if engine:
            # Get SG Engines that are NOT already compatible with this engine
            existing_compatible_sg_ids = engine.compatibles.filter(sg_engine__isnull=False).values_list('sg_engine_id', flat=True)
            available_sg_engines = SGEngine.objects.exclude(id__in=existing_compatible_sg_ids).order_by('sg_make', 'sg_model')
            
            # Set up SG Engine choices
            engine_choices = [('', 'Choose an SG Engine...')]
            for sg_engine in available_sg_engines:
                display_name = f"{sg_engine.sg_make} {sg_engine.sg_model} ({sg_engine.identifier})"
                engine_choices.append((sg_engine.id, display_name))
            
            self.fields['compatible_engine'].choices = engine_choices
    
    def clean(self):
        cleaned_data = super().clean()
        compatible_sg_engine_id = cleaned_data.get('compatible_engine')
        
        if compatible_sg_engine_id and self.engine:
            try:
                sg_engine = SGEngine.objects.get(id=compatible_sg_engine_id)
                # Check if this compatible relationship already exists
                if self.engine.compatibles.filter(sg_engine=sg_engine).exists():
                    raise forms.ValidationError("This SG Engine is already compatible with the selected engine.")
            except SGEngine.DoesNotExist:
                raise forms.ValidationError("Selected SG Engine does not exist.")
        
        return cleaned_data


class EngineSupercessionForm(forms.Form):
    """Form for adding engine supercessions."""
    superseded_engine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': 'required'
        })
    )
    
    def __init__(self, *args, engine=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine
        
        if engine:
            # Get SG Engines that are NOT already superseded by this engine
            existing_superseded_sg_ids = engine.supersedes.filter(sg_engine__isnull=False).values_list('sg_engine_id', flat=True)
            available_sg_engines = SGEngine.objects.exclude(id__in=existing_superseded_sg_ids).order_by('sg_make', 'sg_model')
            
            # Set up SG Engine choices
            engine_choices = [('', 'Choose an SG Engine...')]
            for sg_engine in available_sg_engines:
                display_name = f"{sg_engine.sg_make} {sg_engine.sg_model} ({sg_engine.identifier})"
                engine_choices.append((sg_engine.id, display_name))
            
            self.fields['superseded_engine'].choices = engine_choices
    
    def clean(self):
        cleaned_data = super().clean()
        superseded_sg_engine_id = cleaned_data.get('superseded_engine')
        
        if superseded_sg_engine_id and self.engine:
            try:
                sg_engine = SGEngine.objects.get(id=superseded_sg_engine_id)
                # Check if this supercession relationship already exists
                if self.engine.supersedes.filter(sg_engine=sg_engine).exists():
                    raise forms.ValidationError("This engine already supersedes the selected SG Engine.")
            except SGEngine.DoesNotExist:
                raise forms.ValidationError("Selected SG Engine does not exist.")
        
        return cleaned_data


class KitItemForm(forms.ModelForm):
    """Form for creating and editing Kit Items with integer quantity validation."""
    
    class Meta:
        model = KitItem
        fields = ["part", "vendor", "quantity", "unit_cost", "notes"]
        widgets = {
            "quantity": forms.NumberInput(attrs={
                "step": "1",         # whole-number steppers
                "min": "1",
                "inputmode": "numeric",
                "pattern": r"\d+",   # mobile keyboards prefer digits only
            }),
        }

    def clean_quantity(self):
        q = self.cleaned_data.get("quantity")
        # Accept numbers but ensure integer only
        try:
            d = Decimal(q)
        except (TypeError, InvalidOperation):
            raise forms.ValidationError("Enter a whole number.")
        if d != d.to_integral_value():
            raise forms.ValidationError("Quantity must be a whole number.")
        if d <= 0:
            raise forms.ValidationError("Quantity must be at least 1.")
        return int(d)  # normalize to int for downstream use


class PartEngineLinkForm(forms.ModelForm):
    """Form for linking engines to parts."""
    
    class Meta:
        model = EnginePart
        fields = ["engine", "notes"]
        widgets = {
            'engine': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        part = kwargs.pop("part", None)
        super().__init__(*args, **kwargs)
        assert part is not None, "PartEngineLinkForm requires `part=`"
        # SG Engines NOT already linked to this part (via their associated Engine records)
        self.fields["engine"].queryset = (
            Engine.objects
            .filter(sg_engine__isnull=False)  # Only engines with SG Engine associations
            .exclude(enginepart__part=part)
            .order_by("sg_engine__sg_make", "sg_engine__sg_model", "sg_engine__identifier")
        )
        # Optional: placeholder text
        self.fields["engine"].empty_label = "Select an SG Engine…"
        
        # Update the choices to show SG Engine information
        choices = []
        for engine in self.fields["engine"].queryset:
            sg_engine = engine.sg_engine
            display_text = f"{sg_engine.sg_make} {sg_engine.sg_model} ({sg_engine.identifier})"
            choices.append((engine.id, display_text))
        
        self.fields["engine"].choices = [("", "Select an SG Engine…")] + choices


class PartMachineLinkForm(forms.ModelForm):
    """Form for linking machines to parts."""
    
    class Meta:
        model = MachinePart
        fields = ["machine", "is_primary", "notes"]
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        part = kwargs.pop("part", None)
        super().__init__(*args, **kwargs)
        assert part is not None, "PartMachineLinkForm requires `part=`"
        # Machines NOT already linked to this part
        self.fields["machine"].queryset = (
            Machine.objects
            .exclude(machinepart__part=part)
            .order_by("make", "model", "year", "id")
        )
        self.fields["machine"].empty_label = "Select a machine…"


class MachineForm(forms.ModelForm):
    """Form for creating and editing Machine objects."""
    
    class Meta:
        model = Machine
        fields = ["make", "model", "year", "machine_type", "market_type"]
        widgets = {
            "make": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "year": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "machine_type": forms.TextInput(attrs={"class": "form-control"}),
            "market_type": forms.TextInput(attrs={"class": "form-control"}),
        }


class EngineForm(forms.ModelForm):
    """Form for creating and editing Engine objects."""
    
    class Meta:
        model = Engine
        fields = [
            "engine_make", "engine_model", "status", "price",
            "sg_engine", "sg_engine_notes",
            "cpl_number", "ar_number", "build_list", "engine_code",
            "cylinder", "valves_per_cyl", "bore_stroke", "compression_ratio", "firing_order",
            "crankshaft_no", "piston_no", "piston_marked_no", "piston_notes", "oh_kit_no",
            "overview_comments", "interference", "camshaft", "valve_adjustment",
            "rod_journal_diameter", "main_journal_diameter_pos1", "main_journal_diameter_1",
            "big_end_housing_bore",
        ]
        widgets = {
            "engine_make": forms.TextInput(attrs={"class": "form-control"}),
            "engine_model": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "sg_engine": forms.Select(attrs={"class": "form-control"}),
            "sg_engine_notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            # specs…
            "cpl_number": forms.TextInput(attrs={"class": "form-control"}),
            "ar_number": forms.TextInput(attrs={"class": "form-control"}),
            "build_list": forms.TextInput(attrs={"class": "form-control"}),
            "engine_code": forms.TextInput(attrs={"class": "form-control"}),
            "cylinder": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "valves_per_cyl": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "bore_stroke": forms.TextInput(attrs={"class": "form-control"}),
            "compression_ratio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "firing_order": forms.TextInput(attrs={"class": "form-control"}),
            "crankshaft_no": forms.TextInput(attrs={"class": "form-control"}),
            "piston_no": forms.TextInput(attrs={"class": "form-control"}),
            "piston_marked_no": forms.TextInput(attrs={"class": "form-control"}),
            "piston_notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "oh_kit_no": forms.TextInput(attrs={"class": "form-control"}),
            "overview_comments": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "interference": forms.TextInput(attrs={"class": "form-control"}),
            "camshaft": forms.TextInput(attrs={"class": "form-control"}),
            "valve_adjustment": forms.TextInput(attrs={"class": "form-control"}),
            "rod_journal_diameter": forms.NumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0"}),
            "main_journal_diameter_pos1": forms.NumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0"}),
            "main_journal_diameter_1": forms.NumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0"}),
            "big_end_housing_bore": forms.NumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0"}),
        }


class PartForm(forms.ModelForm):
    """Form for editing Part basic information."""
    
    class Meta:
        model = Part
        fields = [
            "part_number", "name", "category", "manufacturer", "unit",
            "type", "manufacturer_type", "primary_vendor"
        ]
        widgets = {
            "part_number": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "manufacturer": forms.TextInput(attrs={"class": "form-control"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "type": forms.TextInput(attrs={"class": "form-control"}),
            "manufacturer_type": forms.TextInput(attrs={"class": "form-control"}),
            "primary_vendor": forms.Select(attrs={"class": "form-control"}),
        }


class PartSpecsForm(forms.Form):
    """
    Dynamic spec form built from the part's category attributes.
    Field names use 'attr_<id>'.
    """
    def __init__(self, *args, **kwargs):
        part = kwargs.pop("part")
        super().__init__(*args, **kwargs)
        self.part = part
        attrs = (PartAttribute.objects
                 .filter(category=part.category)
                 .order_by("sort_order", "name"))
        existing = {
            pav.attribute_id: pav for pav in
            PartAttributeValue.objects.filter(part=part, attribute__in=attrs)
        }
        for attr in attrs:
            name = f"attr_{attr.id}"
            initial = None
            widget = forms.TextInput(attrs={"class": "form-control"})
            field = None
            if attr.data_type == "int":
                field = forms.IntegerField(required=False, widget=widget, label=attr.name)
                initial = existing.get(attr.id).value_int if attr.id in existing and existing[attr.id] else None
            elif attr.data_type == "dec":
                field = forms.DecimalField(required=False, widget=widget, label=attr.name)
                initial = existing.get(attr.id).value_dec if attr.id in existing and existing[attr.id] else None
            elif attr.data_type == "bool":
                field = forms.BooleanField(required=False, label=attr.name)
                initial = existing.get(attr.id).value_bool if attr.id in existing and existing[attr.id] else False
            elif attr.data_type == "date":
                field = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}), label=attr.name)
                initial = existing.get(attr.id).value_date if attr.id in existing and existing[attr.id] else None
            elif attr.data_type == "choice":
                choices = [(c.value, c.value) for c in attr.choices.all()]
                field = forms.ChoiceField(required=False, choices=[("", "— Select —")] + choices,
                                          widget=forms.Select(attrs={"class": "form-control"}), label=attr.name)
                initial = existing.get(attr.id).choice.value if attr.id in existing and existing[attr.id] and existing[attr.id].choice else ""
            else:  # text
                field = forms.CharField(required=False, widget=widget, label=attr.name)
                initial = existing.get(attr.id).value_text if attr.id in existing and existing[attr.id] else ""
            self.fields[name] = field
            if initial is not None:
                self.fields[name].initial = initial


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "contact_name", "email", "phone", "website", "address", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }


class PartVendorForm(forms.ModelForm):
    part_id = forms.ChoiceField(
        label="Part",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    
    class Meta:
        model = PartVendor
        fields = ["vendor_sku", "cost", "stock_qty", "lead_time_days", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
    
    def __init__(self, *args, **kwargs):
        parts = kwargs.pop('parts', [])
        super().__init__(*args, **kwargs)
        
        # Set up the part choices
        part_choices = [("", "Select a part…")]
        for part in parts:
            part_choices.append((part.id, f"{part.part_number} — {part.name}"))
        self.fields['part_id'].choices = part_choices

