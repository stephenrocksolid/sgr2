from django import forms
from django.contrib.auth.models import User
from .models import UserRole, UserProfile, SystemConfiguration


class UserForm(forms.ModelForm):
    """Form for creating and editing users."""
    
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep current password (when editing)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirm Password"
    )
    role = forms.ModelChoiceField(
        queryset=UserRole.objects.all(),
        required=False,
        empty_label="Select Role"
    )
    department = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=50, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    is_active = forms.BooleanField(required=False, initial=True)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
    
    def __init__(self, *args, **kwargs):
        self.instance_id = kwargs.pop('instance_id', None)
        super().__init__(*args, **kwargs)
        
        # If editing existing user, load profile data
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, 'profile', None)
            if profile:
                self.fields['role'].initial = profile.role
                self.fields['department'].initial = profile.department
                self.fields['phone'].initial = profile.phone
                self.fields['notes'].initial = profile.notes
            
            # Password not required for editing
            self.fields['password'].help_text = "Leave blank to keep current password"
        else:
            # Password required for new users
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Validate passwords match
        if password or confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match")
        
        # For new users, password is required
        if not self.instance.pk and not password:
            raise forms.ValidationError("Password is required for new users")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set password if provided
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        if commit:
            user.save()
            
            # Create or update profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data.get('role')
            profile.department = self.cleaned_data.get('department')
            profile.phone = self.cleaned_data.get('phone')
            profile.notes = self.cleaned_data.get('notes')
            profile.save()
        
        return user


class UserRoleForm(forms.ModelForm):
    """Form for creating and editing user roles."""
    
    class Meta:
        model = UserRole
        fields = [
            'name', 'description', 'is_system_role',
            'can_view_jobs', 'can_edit_jobs', 'can_delete_jobs', 'can_manage_job_options',
            'can_view_inventory', 'can_edit_inventory', 'can_delete_inventory',
            'can_view_imports', 'can_create_imports', 'can_revert_imports',
            'can_view_employees', 'can_edit_employees', 'can_delete_employees',
            'can_manage_users', 'can_manage_roles', 'can_manage_system_config',
            'can_view_reports', 'can_export_reports'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class SystemConfigurationForm(forms.ModelForm):
    """Form for editing system configuration."""
    
    class Meta:
        model = SystemConfiguration
        fields = [
            'company_name', 'company_address', 'company_city', 'company_state', 
            'company_zip', 'company_phone', 'company_email', 'company_website',
            'default_po_ship_to_name', 'default_po_ship_to_address', 'default_po_ship_to_city',
            'default_po_ship_to_state', 'default_po_ship_to_zip', 'default_po_ship_to_phone',
            'email_notifications_enabled', 'notification_email_from'
        ]
        widgets = {
            'company_address': forms.TextInput(),
            'default_po_ship_to_address': forms.TextInput(),
        }
        labels = {
            'default_po_ship_to_name': 'Recipient Name',
            'default_po_ship_to_address': 'Street Address',
            'default_po_ship_to_city': 'City',
            'default_po_ship_to_state': 'State',
            'default_po_ship_to_zip': 'ZIP Code',
            'default_po_ship_to_phone': 'Phone',
        }

