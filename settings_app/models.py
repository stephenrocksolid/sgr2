from django.db import models
from django.contrib.auth.models import User
from core.models import AuditMixin


class UserRole(AuditMixin):
    """User roles with custom permissions."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted"
    )
    
    # Permission flags for different modules
    # Jobs permissions
    can_view_jobs = models.BooleanField(default=True)
    can_edit_jobs = models.BooleanField(default=False)
    can_delete_jobs = models.BooleanField(default=False)
    can_manage_job_options = models.BooleanField(default=False)
    
    # Inventory permissions
    can_view_inventory = models.BooleanField(default=True)
    can_edit_inventory = models.BooleanField(default=False)
    can_delete_inventory = models.BooleanField(default=False)
    
    # Import permissions
    can_view_imports = models.BooleanField(default=False)
    can_create_imports = models.BooleanField(default=False)
    can_revert_imports = models.BooleanField(default=False)
    
    # Employee permissions
    can_view_employees = models.BooleanField(default=True)
    can_edit_employees = models.BooleanField(default=False)
    can_delete_employees = models.BooleanField(default=False)
    
    # Settings permissions
    can_manage_users = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    can_manage_system_config = models.BooleanField(default=False)
    
    # Reports permissions
    can_view_reports = models.BooleanField(default=True)
    can_export_reports = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(AuditMixin):
    """Extended user profile with role and additional information."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.ForeignKey(
        UserRole,
        on_delete=models.PROTECT,
        related_name='user_profiles',
        null=True,
        blank=True
    )
    department = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self):
        return f"Profile for {self.user.username}"


class SystemConfiguration(AuditMixin):
    """System-wide configuration settings (singleton model)."""
    
    # Company Information
    company_name = models.CharField(max_length=255, null=True, blank=True)
    company_address = models.CharField(max_length=255, null=True, blank=True)
    company_city = models.CharField(max_length=100, null=True, blank=True)
    company_state = models.CharField(max_length=50, null=True, blank=True)
    company_zip = models.CharField(max_length=20, null=True, blank=True)
    company_phone = models.CharField(max_length=50, null=True, blank=True)
    company_email = models.EmailField(null=True, blank=True)
    company_website = models.URLField(null=True, blank=True)
    
    # Default PO Ship To Address
    default_po_ship_to_name = models.CharField(max_length=255, null=True, blank=True, help_text="Default recipient name for PO shipping")
    default_po_ship_to_address = models.CharField(max_length=255, null=True, blank=True)
    default_po_ship_to_city = models.CharField(max_length=100, null=True, blank=True)
    default_po_ship_to_state = models.CharField(max_length=50, null=True, blank=True)
    default_po_ship_to_zip = models.CharField(max_length=20, null=True, blank=True)
    default_po_ship_to_phone = models.CharField(max_length=50, null=True, blank=True)
    
    # Email Configuration
    email_notifications_enabled = models.BooleanField(
        default=False,
        help_text="Enable email notifications for job updates"
    )
    notification_email_from = models.EmailField(
        null=True,
        blank=True,
        help_text="From address for system emails"
    )
    
    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configuration'
    
    def __str__(self):
        return f"System Configuration"
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get or create the single configuration instance."""
        config, created = cls.objects.get_or_create(pk=1)
        return config
