from django.contrib import admin
from .models import ImportBatch, SavedImportMapping, ImportLog, ImportRow

@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'file_type', 'status', 'total_rows', 'created_at', 'created_by']
    list_filter = ['status', 'file_type', 'created_at']
    search_fields = ['original_filename']
    readonly_fields = ['file_size', 'total_rows', 'progress_percentage', 'processed_rows', 'created_at', 'updated_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('file', 'original_filename', 'file_type', 'file_size')
        }),
        ('Processing Options', {
            'fields': ('encoding', 'delimiter', 'worksheet_name', 'available_worksheets')
        }),
        ('Data Information', {
            'fields': ('total_rows', 'discovered_headers', 'preview_data')
        }),
        ('Status', {
            'fields': ('status', 'progress_percentage', 'processed_rows', 'error_message')
        }),
        ('Configuration', {
            'fields': ('mapping',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SavedImportMapping)
class SavedImportMappingAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'created_by']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Mapping Configuration', {
            'fields': ('machine_mapping', 'engine_mapping', 'part_mapping'),
            'classes': ('collapse',)
        }),
        ('Processing Options', {
            'fields': ('chunk_size', 'skip_duplicates', 'update_existing')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ['batch', 'row_number', 'has_errors', 'machine_created', 'engine_created', 'part_created', 'processing_time_ms']
    list_filter = ['has_errors', 'machine_created', 'engine_created', 'part_created', 'created_at', 'batch__status']
    search_fields = ['batch__original_filename', 'error_messages']
    readonly_fields = ['created_at', 'processing_time_ms']
    
    fieldsets = (
        ('Row Information', {
            'fields': ('batch', 'row_number', 'has_errors', 'processing_time_ms')
        }),
        ('Original Data', {
            'fields': ('original_data',),
            'classes': ('collapse',)
        }),
        ('Normalized Data', {
            'fields': ('normalized_machine_data', 'normalized_engine_data', 'normalized_part_data'),
            'classes': ('collapse',)
        }),
        ('Processing Results', {
            'fields': (
                'machine_created', 'machine_updated', 'machine_id',
                'engine_created', 'engine_updated', 'engine_id',
                'part_created', 'part_updated', 'part_id'
            )
        }),
        ('Relationships Created', {
            'fields': ('machine_engine_created', 'engine_part_created', 'part_vendor_created')
        }),
        ('Errors', {
            'fields': ('error_messages',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ['batch', 'level', 'message', 'row_number', 'created_at']
    list_filter = ['level', 'created_at', 'batch__status']
    search_fields = ['message', 'batch__original_filename']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Log Information', {
            'fields': ('batch', 'level', 'message', 'row_number')
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
