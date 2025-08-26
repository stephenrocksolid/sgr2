from django.contrib import admin
from .models import (
    SGEngine, Engine, EngineSupercession, Machine, MachineEngine, MachinePart,
    Vendor, Part, EnginePart, PartVendor, PartCategory, PartAttribute, 
    PartAttributeChoice, PartAttributeValue, BuildList, Kit, KitItem
)


@admin.register(SGEngine)
class SGEngineAdmin(admin.ModelAdmin):
    list_display = ['sg_make', 'sg_model', 'identifier', 'created_at']
    list_filter = ['sg_make', 'created_at']
    search_fields = ['sg_make', 'sg_model', 'identifier']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['sg_make', 'sg_model']


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    list_display = ['engine_make', 'engine_model', 'sg_engine', 'cpl_number', 'price', 'status']
    list_filter = ['engine_make', 'status', 'created_at']
    search_fields = ['engine_make', 'engine_model', 'cpl_number', 'ar_number']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['sg_engine']
    ordering = ['engine_make', 'engine_model']


@admin.register(EngineSupercession)
class EngineSupercessionAdmin(admin.ModelAdmin):
    list_display = ['from_engine', 'to_engine', 'effective_date', 'created_at']
    list_filter = ['effective_date', 'created_at']
    search_fields = [
        'from_engine__engine_make', 'from_engine__engine_model',
        'to_engine__engine_make', 'to_engine__engine_model'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['from_engine', 'to_engine']


@admin.register(PartAttributeChoice)
class PartAttributeChoiceAdmin(admin.ModelAdmin):
    list_display = ['attribute', 'value', 'label', 'sort_order']
    list_filter = ['attribute__category', 'attribute__data_type']
    search_fields = ['value', 'label', 'attribute__name']
    list_editable = ['sort_order']
    autocomplete_fields = ['attribute']
    ordering = ['attribute', 'sort_order', 'label']


class PartAttributeChoiceInline(admin.TabularInline):
    model = PartAttributeChoice
    extra = 1
    fields = ['value', 'label', 'sort_order']


@admin.register(PartAttribute)
class PartAttributeAdmin(admin.ModelAdmin):
    list_display = ['category', 'name', 'code', 'data_type', 'is_required', 'sort_order']
    list_filter = ['category', 'data_type', 'is_required']
    search_fields = ['name', 'code', 'category__name']
    list_editable = ['sort_order']
    inlines = [PartAttributeChoiceInline]
    ordering = ['category', 'sort_order', 'name']


class PartAttributeInline(admin.TabularInline):
    model = PartAttribute
    extra = 1
    fields = ['name', 'code', 'data_type', 'unit', 'is_required', 'sort_order', 'help_text']


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parts_count']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PartAttributeInline]
    
    def parts_count(self, obj):
        return obj.parts.count()
    parts_count.short_description = 'Parts'


@admin.register(PartAttributeValue)
class PartAttributeValueAdmin(admin.ModelAdmin):
    list_display = ['part', 'attribute', 'get_value', 'attribute_type']
    list_filter = ['attribute__category', 'attribute__data_type']
    search_fields = [
        'part__part_number', 'part__name', 
        'attribute__name', 'attribute__category__name'
    ]
    autocomplete_fields = ['part', 'attribute', 'choice']
    
    def get_value(self, obj):
        if obj.attribute.data_type == PartAttribute.DataType.TEXT:
            return obj.value_text
        elif obj.attribute.data_type == PartAttribute.DataType.INTEGER:
            return obj.value_int
        elif obj.attribute.data_type == PartAttribute.DataType.DECIMAL:
            return obj.value_dec
        elif obj.attribute.data_type == PartAttribute.DataType.BOOLEAN:
            return obj.value_bool
        elif obj.attribute.data_type == PartAttribute.DataType.DATE:
            return obj.value_date
        elif obj.attribute.data_type == PartAttribute.DataType.CHOICE:
            return obj.choice
        return None
    get_value.short_description = 'Value'
    
    def attribute_type(self, obj):
        return obj.attribute.get_data_type_display()
    attribute_type.short_description = 'Type'


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['make', 'model', 'year', 'machine_type', 'market_type', 'created_at']
    list_filter = ['make', 'machine_type', 'market_type', 'year', 'created_at']
    search_fields = ['make', 'model', 'machine_type', 'market_type']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['year', 'make', 'model']


class MachineEngineInline(admin.TabularInline):
    model = MachineEngine
    extra = 1
    autocomplete_fields = ['engine']


class MachinePartInline(admin.TabularInline):
    model = MachinePart
    extra = 1
    autocomplete_fields = ['part']


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_name', 'email', 'phone', 'website', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'contact_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['name']


class EnginePartInline(admin.TabularInline):
    model = EnginePart
    extra = 1
    autocomplete_fields = ['engine']


class PartVendorInline(admin.TabularInline):
    model = PartVendor
    extra = 1
    fields = ['vendor', 'vendor_sku', 'cost', 'stock_qty', 'lead_time_days', 'notes']
    autocomplete_fields = ['vendor']
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['set_as_primary_vendor'] = self.set_as_primary_vendor
        return actions
    
    def set_as_primary_vendor(self, request, queryset):
        updated = 0
        for part_vendor in queryset:
            part_vendor.part.primary_vendor = part_vendor.vendor
            part_vendor.part.save()
            updated += 1
        
        if updated == 1:
            self.message_user(request, f"Set {updated} part's primary vendor.")
        else:
            self.message_user(request, f"Set {updated} parts' primary vendors.")
    set_as_primary_vendor.short_description = "Set as Primary Vendor"


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'name', 'category', 'manufacturer', 'primary_vendor', 'created_at']
    list_filter = ['category', 'manufacturer', 'type', 'created_at']
    search_fields = ['part_number', 'name', 'manufacturer', 'category']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['primary_vendor']
    inlines = [EnginePartInline, PartVendorInline]
    ordering = ['part_number']


@admin.register(EnginePart)
class EnginePartAdmin(admin.ModelAdmin):
    list_display = ['engine', 'part', 'created_at']
    list_filter = ['created_at']
    search_fields = [
        'engine__engine_make', 'engine__engine_model',
        'part__part_number', 'part__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['engine', 'part']


@admin.register(PartVendor)
class PartVendorAdmin(admin.ModelAdmin):
    list_display = ['part', 'vendor', 'vendor_sku', 'cost', 'stock_qty', 'lead_time_days', 'notes', 'created_at']
    list_filter = ['created_at']
    search_fields = [
        'part__part_number', 'part__name',
        'vendor__name', 'vendor_sku'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['part', 'vendor']
    
    actions = ['set_as_primary_vendor']
    
    def set_as_primary_vendor(self, request, queryset):
        updated = 0
        for part_vendor in queryset:
            part_vendor.part.primary_vendor = part_vendor.vendor
            part_vendor.part.save()
            updated += 1
        
        if updated == 1:
            self.message_user(request, f"Set {updated} part's primary vendor.")
        else:
            self.message_user(request, f"Set {updated} parts' primary vendors.")
    set_as_primary_vendor.short_description = "Set as Primary Vendor"


@admin.register(MachineEngine)
class MachineEngineAdmin(admin.ModelAdmin):
    list_display = ['machine', 'engine', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = [
        'machine__make', 'machine__model',
        'engine__engine_make', 'engine__engine_model'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['machine', 'engine']


@admin.register(MachinePart)
class MachinePartAdmin(admin.ModelAdmin):
    list_display = ['machine', 'part', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = [
        'machine__make', 'machine__model',
        'part__part_number', 'part__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    autocomplete_fields = ['machine', 'part']


@admin.register(BuildList)
class BuildListAdmin(admin.ModelAdmin):
    list_display = ['engine', 'name', 'kits_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'engine__engine_make', 'engine__engine_model', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['engine']
    ordering = ['-updated_at']
    
    def kits_count(self, obj):
        return obj.kits.count()
    kits_count.short_description = 'Kits'


class KitItemInline(admin.TabularInline):
    model = KitItem
    extra = 1
    autocomplete_fields = ['part', 'vendor']
    fields = ['part', 'vendor', 'quantity', 'unit_cost', 'notes']


@admin.register(Kit)
class KitAdmin(admin.ModelAdmin):
    list_display = ['build_list', 'name', 'cost_total', 'margin_pct', 'sale_price', 'items_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'build_list__name', 'build_list__engine__engine_make', 'notes']
    readonly_fields = ['cost_total', 'sale_price', 'created_at', 'updated_at']
    autocomplete_fields = ['build_list']
    inlines = [KitItemInline]
    ordering = ['-updated_at']
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'


@admin.register(KitItem)
class KitItemAdmin(admin.ModelAdmin):
    list_display = ['kit', 'part', 'vendor', 'quantity', 'unit_cost', 'line_total']
    search_fields = [
        'kit__name', 'kit__build_list__name',
        'part__part_number', 'part__name',
        'vendor__name'
    ]
    autocomplete_fields = ['kit', 'part', 'vendor']
    
    def line_total(self, obj):
        return obj.unit_cost * obj.quantity
    line_total.short_description = 'Line Total'
