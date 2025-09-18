import os
import json
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

class ImportBatch(models.Model):
    """Represents a file upload for import processing."""
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('mapped', 'Mapped'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    file = models.FileField(upload_to='imports/')
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=10)  # 'csv' or 'xlsx'
    
    # CSV specific fields
    encoding = models.CharField(max_length=20, default='utf-8')
    delimiter = models.CharField(max_length=5, default=',')
    
    # XLSX specific fields
    worksheet_name = models.CharField(max_length=255, blank=True, null=True)
    available_worksheets = models.JSONField(default=list, blank=True)
    
    # Processing info
    total_rows = models.IntegerField(default=0)
    preview_data = models.JSONField(default=list)  # First ~200 rows
    discovered_headers = models.JSONField(default=list)
    
    # Status and progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    progress_percentage = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    celery_id = models.CharField(max_length=255, blank=True, null=True, help_text="Celery task ID for tracking async processing")
    
    # Mapping
    mapping = models.ForeignKey('SavedImportMapping', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_status_display()})"
    
    def clean(self):
        if self.file_size and self.file_size > 50 * 1024 * 1024:  # 50MB limit
            raise ValidationError("File size must be less than 50MB")
        
        if self.total_rows and self.total_rows > 100000:  # 100k rows limit
            raise ValidationError("File must have less than 100,000 rows")
    
    def save(self, *args, **kwargs):
        # Set file size if not already set and file exists
        if not self.file_size and self.file:
            try:
                self.file_size = self.file.size
            except (OSError, AttributeError):
                pass
        super().save(*args, **kwargs)
    
    def get_file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower()
    
    def is_csv(self):
        return self.file_type == 'csv'
    
    def is_xlsx(self):
        return self.file_type == 'xlsx'

class SavedImportMapping(models.Model):
    """Saved mapping configuration for import fields."""
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Mapping configuration
    machine_mapping = models.JSONField(default=dict)  # field_name -> header_name
    engine_mapping = models.JSONField(default=dict)
    part_mapping = models.JSONField(default=dict)
    vendor_mapping = models.JSONField(default=dict, blank=True)  # field_name -> header_name
    part_attribute_mappings = models.JSONField(default=dict, blank=True)  # attr_id -> header_name
    
    # Processing options
    chunk_size = models.IntegerField(default=2000)
    skip_duplicates = models.BooleanField(default=True)
    update_existing = models.BooleanField(default=False)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_mapping_for_section(self, section):
        """Get mapping for a specific section (machines, engines, parts, vendors)."""
        mapping_fields = {
            'machines': self.machine_mapping,
            'engines': self.engine_mapping,
            'parts': self.part_mapping,
            'vendors': self.vendor_mapping,
        }
        return mapping_fields.get(section, {})

class ImportRow(models.Model):
    """Tracks processed import rows with normalized data and errors."""
    
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='rows')
    row_number = models.IntegerField()
    
    # Original data
    original_data = models.JSONField()  # Raw row data from file
    
    # Normalized data
    normalized_machine_data = models.JSONField(default=dict, blank=True)
    normalized_engine_data = models.JSONField(default=dict, blank=True)
    normalized_part_data = models.JSONField(default=dict, blank=True)
    normalized_vendor_data = models.JSONField(default=dict, blank=True)
    
    # Processing results
    machine_created = models.BooleanField(default=False)
    machine_updated = models.BooleanField(default=False)
    machine_id = models.IntegerField(null=True, blank=True)
    
    engine_created = models.BooleanField(default=False)
    engine_updated = models.BooleanField(default=False)
    engine_id = models.IntegerField(null=True, blank=True)
    
    part_created = models.BooleanField(default=False)
    part_updated = models.BooleanField(default=False)
    part_id = models.IntegerField(null=True, blank=True)
    
    vendor_created = models.BooleanField(default=False)
    vendor_updated = models.BooleanField(default=False)
    vendor_id = models.IntegerField(null=True, blank=True)
    
    # Relationships created
    machine_engine_created = models.BooleanField(default=False)
    engine_part_created = models.BooleanField(default=False)
    part_vendor_created = models.BooleanField(default=False)
    engine_vendor_linked = models.BooleanField(default=False)
    
    # Duplicate tracking
    engine_duplicate_skipped = models.BooleanField(default=False)
    engine_duplicate_updated = models.BooleanField(default=False)
    
    # Error tracking
    has_errors = models.BooleanField(default=False)
    error_messages = models.JSONField(default=list, blank=True)
    
    # Processing metadata
    processing_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['batch', 'row_number']
        unique_together = ['batch', 'row_number']
        indexes = [
            models.Index(fields=['batch', 'row_number']),
            models.Index(fields=['has_errors']),
        ]
    
    def __str__(self):
        return f"Row {self.row_number} - {self.batch.original_filename}"
    
    def add_error(self, error_message):
        """Add an error message to this row."""
        self.has_errors = True
        if not self.error_messages:
            self.error_messages = []
        self.error_messages.append(error_message)
        self.save(update_fields=['has_errors', 'error_messages'])

class ImportLog(models.Model):
    """Log of import processing events."""
    
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='logs')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    message = models.TextField()
    row_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.batch.original_filename} - {self.level}: {self.message[:50]}"
