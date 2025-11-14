from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Index view
    path('', views.index, name='index'),
    
    # Machine views
    path('machines/', views.machines_list, name='machines_list'),
    path('machines/<int:machine_id>/', views.machine_detail, name='machine_detail'),
    
    # Machine edit routes
    path('machines/<int:pk>/edit/', views.machine_edit, name='machine_edit'),
    path('machines/<int:pk>/update/', views.machine_update, name='machine_update'),
    
    # Machine-Engine relationship HTMX endpoints (legacy - kept for compatibility)
    path('machines/<int:machine_id>/engines/', views.machine_engines_list, name='machine_engines_list'),
    path('machines/<int:machine_id>/engines/add-form/', views.machine_add_engine_form, name='machine_add_engine_form'),
    
    # New stable container endpoints
    path('machines/<int:machine_id>/engines/partial/', views.machine_engines_partial, name='machine_engines_partial'),
    path('machines/<int:machine_id>/engines/add/', views.machine_engine_add, name='machine_engine_add'),
    path('machines/<int:machine_id>/engines/<int:link_id>/remove/', views.machine_engine_remove, name='machine_engine_remove'),
    
    # Machine-Part relationship HTMX endpoints (stable container)
    path('machines/<int:machine_id>/parts/partial/', views.machine_parts_partial, name='machine_parts_partial'),
    path('machines/<int:machine_id>/parts/add/', views.machine_part_add, name='machine_part_add'),
    path('machines/<int:machine_id>/parts/<int:link_id>/remove/', views.machine_part_remove, name='machine_part_remove'),
    
    # Engine views
    path('engines/', views.engines_list, name='engines_list'),
    path('engines/<int:engine_id>/', views.engine_detail, name='engine_detail'),
    
    # Engine edit routes
    path('engines/<int:pk>/edit/', views.engine_edit, name='engine_edit'),
    path('engines/<int:pk>/update/', views.engine_update, name='engine_update'),
    
    # Engine-Machine relationship HTMX endpoints (stable container)
    path('engines/<int:engine_id>/machines/partial/', views.engine_machines_partial, name='engine_machines_partial'),
    path('engines/<int:engine_id>/machines/add/', views.engine_machine_add, name='engine_machine_add'),
    path('engines/<int:engine_id>/machines/<int:link_id>/remove/', views.engine_machine_remove, name='engine_machine_remove'),
    
    # NEW: inline add forms + create
    path('engines/<int:engine_id>/machines/add/form/', views.engine_machine_add_form, name='engine_machine_add_form'),
    
    # Engine-Part relationship HTMX endpoints (stable container)
    path('engines/<int:engine_id>/parts/partial/', views.engine_parts_partial, name='engine_parts_partial'),
    path('engines/<int:engine_id>/parts/add/', views.engine_part_add, name='engine_part_add'),
    path('engines/<int:engine_id>/parts/<int:link_id>/remove/', views.engine_part_remove, name='engine_part_remove'),
    
    # NEW: inline add forms + create
    path('engines/<int:engine_id>/parts/add/form/', views.engine_part_add_form, name='engine_part_add_form'),
    
    # Engine-Engine relationship HTMX endpoints
    # Engine-Interchange relationship HTMX endpoints (stable container)
    path('engines/<int:engine_id>/interchanges/partial/', views.engine_interchanges_partial, name='engine_interchanges_partial'),
    path('engines/<int:engine_id>/interchanges/add/', views.engine_interchange_add, name='engine_interchange_add'),
    path('engines/<int:engine_id>/interchanges/<int:interchange_id>/remove/', views.engine_interchange_remove, name='engine_interchange_remove'),
    
    # Engine-Compatible relationship HTMX endpoints (stable container)
    path('engines/<int:engine_id>/compatibles/partial/', views.engine_compatibles_partial, name='engine_compatibles_partial'),
    path('engines/<int:engine_id>/compatibles/add/', views.engine_compatible_add, name='engine_compatible_add'),
    path('engines/<int:engine_id>/compatibles/<int:compatible_id>/remove/', views.engine_compatible_remove, name='engine_compatible_remove'),
    
    # Engine-Supercession relationship HTMX endpoints (stable container)
    path('engines/<int:engine_id>/supercessions/partial/', views.engine_supercessions_partial, name='engine_supercessions_partial'),
    path('engines/<int:engine_id>/supercessions/form/<str:direction>/', views.engine_supercession_form, name='engine_supercession_form'),
    path('engines/<int:engine_id>/supercessions/add/<str:direction>/', views.engine_supercession_add, name='engine_supercession_add'),
    path('engines/<int:engine_id>/supercessions/<int:superseded_id>/remove/', views.engine_supercession_remove, name='engine_supercession_remove'),
    
    # Part views
    path('parts/', views.parts_list, name='parts_list'),
    path('parts/new/', views.part_create, name='part_create'),
    path('parts/<int:part_id>/', views.part_detail, name='part_detail'),
    
    # Part edit routes
    path('parts/<int:pk>/edit/', views.part_edit, name='part_edit'),
    path('parts/<int:pk>/update/', views.part_update, name='part_update'),
    path('parts/<int:pk>/category/preview/', views.part_category_preview, name='part_category_preview'),
    
    # Part custom fields HTMX endpoints
    path('parts/<int:part_id>/specs/partial/', views.part_specs_form, name='part_specs_form'),
    path('parts/<int:part_id>/specs/save/', views.part_specs_save, name='part_specs_save'),
    path('parts/<int:part_id>/specs/table/', views.part_specs_table, name='part_specs_table'),
    path('parts/<int:part_id>/specs/add/', views.part_specs_add, name='part_specs_add'),
    path('parts/<int:part_id>/specs/<int:pav_id>/edit/', views.part_specs_edit, name='part_specs_edit'),
    path('parts/<int:part_id>/specs/<int:pav_id>/remove/', views.part_specs_remove, name='part_specs_remove'),
    path('parts/<int:part_id>/category/change/', views.part_category_change, name='part_category_change'),
    path('parts/<int:part_id>/specs/value-input/', views.part_specs_value_input, name='part_specs_value_input'),
    
    # New Part specs endpoints
    path('parts/<int:part_id>/specs/read/', views.part_specs_read, name='part_specs_read'),
    path('parts/<int:part_id>/specs/edit/', views.part_specs_edit_form, name='part_specs_edit_form'),
    path('parts/<int:part_id>/specs/save/', views.part_specs_save_all, name='part_specs_save_all'),
    path('parts/<int:part_id>/category/confirm-change/', views.part_category_confirm_change, name='part_category_confirm_change'),
    
    path('parts/filters/value-control/', views.filter_value_control, name='filter_value_control'),
    
    # Part-Engine relationship HTMX endpoints
    path('parts/<int:part_id>/engines/partial/', views.part_engines_partial, name='part_engines_partial'),
    path('parts/<int:part_id>/engines/add/', views.part_engine_add, name='part_engine_add'),
    path('parts/<int:part_id>/engines/<int:link_id>/remove/', views.part_engine_remove, name='part_engine_remove'),
    
    # Part-Machine relationship HTMX endpoints
    path('parts/<int:part_id>/machines/partial/', views.part_machines_partial, name='part_machines_partial'),
    path('parts/<int:part_id>/machines/add/', views.part_machine_add, name='part_machine_add'),
    path('parts/<int:part_id>/machines/<int:link_id>/remove/', views.part_machine_remove, name='part_machine_remove'),
    
    # Part-Kit relationship HTMX endpoints
    path('parts/<int:part_id>/kits/partial/', views.part_kits_partial, name='part_kits_partial'),
    
    # Part-Vendor relationship HTMX endpoints
    path('parts/<int:part_id>/vendors/', views.part_vendors_section, name='part_vendors_section'),
    path('parts/<int:part_id>/vendors/add/', views.part_vendor_add, name='part_vendor_add'),
    path('parts/<int:part_id>/vendors/add-form/', views.part_vendor_add_form, name='part_vendor_add_form'),
    path('parts/<int:part_id>/vendors/<int:part_vendor_id>/edit/', views.part_vendor_edit, name='part_vendor_edit'),
    path('parts/<int:part_id>/vendors/<int:part_vendor_id>/delete/', views.part_vendor_delete, name='part_vendor_delete'),
    path('parts/<int:part_id>/vendors/<int:part_vendor_id>/set-primary/', views.part_vendor_set_primary, name='part_vendor_set_primary'),
    
    # Build Lists
    path('build-lists/', views.build_lists_list, name='build_lists_list'),
    path('build-lists/new/', views.build_list_create, name='build_list_create'),
    path('build-lists/<int:build_list_id>/', views.build_list_detail, name='build_list_detail'),
    path('build-lists/<int:build_list_id>/edit/', views.build_list_edit, name='build_list_edit'),
    path('build-lists/<int:build_list_id>/delete/', views.build_list_delete, name='build_list_delete'),
    
    # Build list items (HTMX)
    path('build-lists/<int:build_list_id>/items/partial/', views.build_list_items_partial, name='build_list_items_partial'),
    path('build-lists/<int:build_list_id>/items/add/form/', views.build_list_item_add_form, name='build_list_item_add_form'),
    path('build-lists/<int:build_list_id>/items/add/', views.build_list_item_add, name='build_list_item_add'),
    path('build-lists/<int:build_list_id>/items/<int:item_id>/edit/form/', views.build_list_item_edit_form, name='build_list_item_edit_form'),
    path('build-lists/<int:build_list_id>/items/<int:item_id>/edit/', views.build_list_item_edit, name='build_list_item_edit'),
    path('build-lists/<int:build_list_id>/items/<int:item_id>/delete/', views.build_list_item_delete, name='build_list_item_delete'),
    
    # Engine assignments from build list side (HTMX)
    path('build-lists/<int:build_list_id>/engines/partial/', views.build_list_engines_partial, name='build_list_engines_partial'),
    path('build-lists/<int:build_list_id>/engines/add/form/', views.build_list_engine_add_form, name='build_list_engine_add_form'),
    path('build-lists/<int:build_list_id>/engines/add/', views.build_list_engine_add, name='build_list_engine_add'),
    path('build-lists/<int:build_list_id>/engines/<int:engine_id>/remove/', views.build_list_engine_remove, name='build_list_engine_remove'),
    
    # Build lists on engine side (HTMX)
    path('engines/<int:engine_id>/build-lists/partial/', views.engine_build_lists_partial, name='engine_build_lists_partial'),
    path('engines/<int:engine_id>/build-lists/add/form/', views.engine_build_list_add_form, name='engine_build_list_add_form'),
    path('engines/<int:engine_id>/build-lists/add/', views.engine_build_list_add, name='engine_build_list_add'),
    path('engines/<int:engine_id>/build-lists/<int:build_list_id>/remove/', views.engine_build_list_remove, name='engine_build_list_remove'),
    
    # Kits
    path('kits/', views.kits_list, name='kits_list'),
    path('kits/new/', views.kit_create, name='kit_create'),
    path('kits/<int:kit_id>/', views.kit_detail, name='kit_detail'),
    path('kits/<int:kit_id>/edit/', views.kit_edit, name='kit_edit'),
    path('kits/<int:kit_id>/delete/', views.kit_delete, name='kit_delete'),
    
    # Kit items (HTMX)
    path('kits/<int:kit_id>/items/partial/', views.kit_items_partial, name='kit_items_partial'),
    path('kits/<int:kit_id>/items/add/form/', views.kit_item_add_form, name='kit_item_add_form'),
    path('kits/<int:kit_id>/items/add/', views.kit_item_add, name='kit_item_add'),
    path('kits/<int:kit_id>/items/<int:item_id>/edit/form/', views.kit_item_edit_form, name='kit_item_edit_form'),
    path('kits/<int:kit_id>/items/<int:item_id>/edit/', views.kit_item_edit, name='kit_item_edit'),
    path('kits/<int:kit_id>/items/<int:item_id>/delete/', views.kit_item_delete, name='kit_item_delete'),
    
    # Engine assignments from kit side (HTMX)
    path('kits/<int:kit_id>/engines/partial/', views.kit_engines_partial, name='kit_engines_partial'),
    path('kits/<int:kit_id>/engines/add/form/', views.kit_engine_add_form, name='kit_engine_add_form'),
    path('kits/<int:kit_id>/engines/add/', views.kit_engine_add, name='kit_engine_add'),
    path('kits/<int:kit_id>/engines/<int:engine_id>/remove/', views.kit_engine_remove, name='kit_engine_remove'),
    
    # Kits on engine side (HTMX)
    path('engines/<int:engine_id>/kits/partial/', views.engine_kits_partial, name='engine_kits_partial'),
    path('engines/<int:engine_id>/kits/add/form/', views.engine_kit_add_form, name='engine_kit_add_form'),
    path('engines/<int:engine_id>/kits/add/', views.engine_kit_add, name='engine_kit_add'),
    path('engines/<int:engine_id>/kits/<int:kit_id>/remove/', views.engine_kit_remove, name='engine_kit_remove'),
    
    # Castings (HTMX)
    path('engines/<int:engine_id>/castings/partial/', views.engine_castings_partial, name='engine_castings_partial'),
    path('engines/<int:engine_id>/castings/add/form/', views.engine_casting_add_form, name='engine_casting_add_form'),
    path('engines/<int:engine_id>/castings/add/', views.engine_casting_add, name='engine_casting_add'),
    path('engines/<int:engine_id>/castings/<int:casting_id>/edit/form/', views.engine_casting_edit_form, name='engine_casting_edit_form'),
    path('engines/<int:engine_id>/castings/<int:casting_id>/edit/', views.engine_casting_edit, name='engine_casting_edit'),
    path('engines/<int:engine_id>/castings/<int:casting_id>/delete/', views.engine_casting_delete, name='engine_casting_delete'),
    
    # Vendors
    path("vendors/", views.vendor_index, name="vendor_index"),
    path("vendors/new/", views.vendor_create, name="vendor_create"),
    path("vendors/<int:vendor_id>/", views.vendor_detail, name="vendor_detail"),
    path("vendors/<int:vendor_id>/edit/", views.vendor_edit, name="vendor_edit"),
    path("vendors/<int:vendor_id>/delete/", views.vendor_delete, name="vendor_delete"),
    
    # Vendor contacts
    path("vendors/<int:vendor_id>/contacts/new/", views.vendor_contact_create, name="vendor_contact_create"),
    path("vendors/<int:vendor_id>/contacts/<int:contact_id>/edit/", views.vendor_contact_edit, name="vendor_contact_edit"),
    path("vendors/<int:vendor_id>/contacts/<int:contact_id>/delete/", views.vendor_contact_delete_confirm, name="vendor_contact_delete_confirm"),
    path("vendors/<int:vendor_id>/contacts/<int:contact_id>/delete/confirm/", views.vendor_contact_delete, name="vendor_contact_delete"),
    path("vendors/<int:vendor_id>/contacts/<int:contact_id>/set-primary/", views.vendor_contact_set_primary, name="vendor_contact_set_primary"),

    # Vendor detail partials (HTMX)
    path("vendors/<int:vendor_id>/parts/partial/", views.vendor_parts_partial, name="vendor_parts_partial"),
                path("vendors/<int:vendor_id>/parts/add/form/", views.vendor_part_add_form, name="vendor_part_add_form"),
            path("vendors/<int:vendor_id>/parts/add/", views.vendor_part_add, name="vendor_part_add"),
            path("vendors/<int:vendor_id>/parts/options/", views.vendor_part_options, name="vendor_part_options"),
    path("vendors/<int:vendor_id>/parts/<int:link_id>/edit/form/", views.vendor_part_edit_form, name="vendor_part_edit_form"),
    path("vendors/<int:vendor_id>/parts/<int:link_id>/edit/", views.vendor_part_edit, name="vendor_part_edit"),
    path("vendors/<int:vendor_id>/parts/<int:link_id>/remove/", views.vendor_part_remove, name="vendor_part_remove"),

    # Set primary vendor for a part (works from either page)
    path("parts/<int:part_id>/primary-vendor/<int:vendor_id>/set/", views.part_set_primary_vendor, name="part_set_primary_vendor"),
    
    # Build List HTMX endpoints (legacy - deprecated)
    path('engines/<int:engine_id>/build-lists/', views.engine_build_lists_section, name='engine_build_lists_section'),
    path('engines/<int:engine_id>/build-lists/create/', views.build_list_create, name='build_list_create'),
    path('engines/<int:engine_id>/build-lists/add-form/', views.build_list_add_form, name='build_list_add_form'),
    path('build-lists/<int:build_list_id>/rename/', views.build_list_rename, name='build_list_rename'),
    path('build-lists/<int:build_list_id>/delete/', views.build_list_delete, name='build_list_delete'),
    path('engines/<int:engine_id>/build-lists/<int:build_list_id>/', views.build_list_detail_redirect, name='build_list_detail'),
    
    # Backwards compatibility redirects
    path('build-lists/<int:build_list_id>/', views.build_list_redirect, name='build_list_redirect'),
    
    # Kit HTMX endpoints (legacy build-list based)
    path('build-lists/<int:build_list_id>/kits/', views.build_list_kits_section, name='build_list_kits_section'),
    path('build-lists/<int:build_list_id>/kits/create/', views.kit_create, name='kit_create'),
    
    # Kit HTMX endpoints (new engine-based)
    path('engines/<int:engine_id>/kits/', views.engine_kits_section, name='engine_kits_section'),
    path('engines/<int:engine_id>/kits/create/', views.engine_kit_create, name='engine_kit_create'),
    path('engines/<int:engine_id>/kits/add-form/', views.engine_kit_add_form, name='engine_kit_add_form'),
    path('kits/<int:kit_id>/rename/', views.kit_rename, name='kit_rename'),
    path('kits/<int:kit_id>/delete/', views.kit_delete, name='kit_delete'),
    path('kits/<int:kit_id>/duplicate/', views.kit_duplicate, name='kit_duplicate'),
    path('kits/<int:kit_id>/', views.kit_detail, name='kit_detail'),
    path('kits/<int:kit_id>/set-margin/', views.kit_set_margin, name='kit_set_margin'),
    
    # Kit Item HTMX endpoints
    path('kits/<int:kit_id>/items/', views.kit_items_section, name='kit_items_section'),
    path('kits/<int:kit_id>/items/add/', views.kit_item_add, name='kit_item_add'),
    path('kits/<int:kit_id>/items/<int:item_id>/edit/', views.kit_item_edit, name='kit_item_edit'),
    path('kits/<int:kit_id>/items/<int:item_id>/remove/', views.kit_item_remove, name='kit_item_remove'),
    
    # Vendor selection for parts
    path('parts/<int:part_id>/vendors/options/', views.get_vendors_for_part, name='get_vendors_for_part'),
    
    # Settings routes
    path('settings/parts/categories/', views.part_categories_list, name='part_categories_list'),
    path('settings/parts/categories/new/', views.part_category_create, name='part_category_create'),
    path('settings/parts/categories/<int:category_id>/', views.part_category_detail, name='part_category_detail'),
    path('settings/parts/categories/<int:category_id>/edit/', views.part_category_edit, name='part_category_edit'),
    path('settings/parts/categories/<int:category_id>/delete/', views.part_category_delete, name='part_category_delete'),
    
    # Settings HTMX endpoints
    path('settings/parts/categories/<int:category_id>/attributes/add/', views.part_attribute_add, name='part_attribute_add'),
    path('settings/parts/categories/<int:category_id>/attributes/<int:attribute_id>/edit/', views.part_attribute_edit, name='part_attribute_edit'),
    path('settings/parts/categories/<int:category_id>/attributes/<int:attribute_id>/delete/', views.part_attribute_delete, name='part_attribute_delete'),
    path('settings/parts/categories/<int:category_id>/attributes/<int:attribute_id>/choices/add/', views.part_attribute_choice_add, name='part_attribute_choice_add'),
    path('settings/parts/categories/<int:category_id>/attributes/<int:attribute_id>/choices/<int:choice_id>/edit/', views.part_attribute_choice_edit, name='part_attribute_choice_edit'),
    path('settings/parts/categories/<int:category_id>/attributes/<int:attribute_id>/choices/<int:choice_id>/delete/', views.part_attribute_choice_delete, name='part_attribute_choice_delete'),
    
    # SG Engine views
    path('sg-engines/', views.sg_engines_list, name='sg_engines_list'),
    path('sg-engines/<int:pk>/', views.sg_engine_detail, name='sg_engine_detail'),
    path('sg-engines/<int:pk>/edit/', views.sg_engine_edit, name='sg_engine_edit'),
    
    # Import views - commented out for now as they're not implemented
    # path('imports/', views.imports_list, name='imports_list'),
    # path('imports/new/', views.import_new, name='import_new'),
    # path('imports/<int:pk>/', views.import_detail, name='import_detail'),
    # path('imports/<int:pk>/process/', views.import_process, name='import_process'),
    
    # Unmatched items views - commented out for now as they're not implemented
    # path('unmatched/', views.unmatched_list, name='unmatched_list'),
]
