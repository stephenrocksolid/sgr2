from django import forms
from inventory.models import SGVendor


class SGVendorForm(forms.ModelForm):
    """Form for creating and editing SG Vendors."""
    
    class Meta:
        model = SGVendor
        fields = ['name', 'website', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter SG Vendor name'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this SG Vendor'
            })
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            # Check for case-insensitive duplicates
            existing = SGVendor.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError('An SG Vendor with this name already exists.')
        return name












