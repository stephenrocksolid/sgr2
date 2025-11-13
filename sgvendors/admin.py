from django.contrib import admin
from inventory.models import SGVendor


@admin.register(SGVendor)
class SGVendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'created', 'updated']
    list_filter = ['created', 'updated']
    search_fields = ['name', 'website', 'notes']
    readonly_fields = ['created', 'updated']





