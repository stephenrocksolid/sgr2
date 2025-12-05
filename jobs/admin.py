from django.contrib import admin
from .models import (
    PurchaseOrder, 
    PurchaseOrderItem, 
    PurchaseOrderReceiving, 
    PurchaseOrderAttachment
)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    fields = ('part', 'quantity_ordered', 'quantity_received', 'unit_price', 'status')
    readonly_fields = ('quantity_received',)


class PurchaseOrderAttachmentInline(admin.TabularInline):
    model = PurchaseOrderAttachment
    extra = 0
    fields = ('file', 'original_name', 'description')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'vendor', 'status', 'po_date', 'total_amount', 'created_at')
    list_filter = ('status', 'is_urgent', 'po_date', 'vendor')
    search_fields = ('po_number', 'vendor__name', 'notes')
    date_hierarchy = 'po_date'
    inlines = [PurchaseOrderItemInline, PurchaseOrderAttachmentInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('po_number', 'status', 'po_date', 'requested_by')
        }),
        ('Vendor Information', {
            'fields': ('vendor', 'vendor_contact', 'vendor_po_number')
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'shipping_cost', 
                      'other_charges', 'discount_amount', 'total_amount', 'currency')
        }),
        ('Dates', {
            'fields': ('submitted_date', 'expected_delivery_date', 
                      'actual_delivery_date', 'closed_date')
        }),
        ('Terms & Shipping', {
            'fields': ('payment_terms', 'shipping_method', 'shipping_account_number')
        }),
        ('Shipping Address', {
            'fields': ('ship_to_name', 'ship_to_address', 'ship_to_city', 
                      'ship_to_state', 'ship_to_zip', 'ship_to_phone')
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'carrier')
        }),
        ('Notes', {
            'fields': ('notes', 'vendor_notes', 'receiving_notes')
        }),
        ('Flags', {
            'fields': ('is_urgent', 'is_drop_ship')
        }),
    )


class PurchaseOrderReceivingInline(admin.TabularInline):
    model = PurchaseOrderReceiving
    extra = 0
    fields = ('received_date', 'quantity_received', 'received_by', 'condition', 'notes')


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'part_number', 'part_name', 'quantity_ordered', 
                   'quantity_received', 'unit_price', 'status')
    list_filter = ('status', 'purchase_order__vendor')
    search_fields = ('part_number', 'part_name', 'purchase_order__po_number')
    inlines = [PurchaseOrderReceivingInline]


@admin.register(PurchaseOrderReceiving)
class PurchaseOrderReceivingAdmin(admin.ModelAdmin):
    list_display = ('purchase_order_item', 'received_date', 'quantity_received', 
                   'received_by', 'condition')
    list_filter = ('condition', 'received_date')
    search_fields = ('purchase_order_item__purchase_order__po_number',)
    date_hierarchy = 'received_date'


@admin.register(PurchaseOrderAttachment)
class PurchaseOrderAttachmentAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'original_name', 'description', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('purchase_order__po_number', 'original_name', 'description')




