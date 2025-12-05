from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Home
    path('home/', views.home, name='home'),
    
    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/events/', views.calendar_events_api, name='calendar_events_api'),
    
    # Job URLs (actual jobs, not tickets)
    path('', views.job_list, name='job_list'),
    path('<int:pk>/', views.job_detail, name='job_detail'),  # Combined view/edit page
    path('<int:pk>/delete/', views.job_delete, name='job_delete'),
    path('new/', views.job_create, name='job_create'),
    
    # Job Ticket URLs
    path('tickets/', views.job_ticket_list, name='ticket_list'),
    path('tickets/new/', views.JobTicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', views.JobTicketUpdateView.as_view(), name='ticket_detail'),  # Combined view/edit page
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/<int:pk>/create-job/', views.create_job_from_ticket, name='create_job_from_ticket'),
    
    # Customer Search & Selection
    path('tickets/<int:pk>/customer/search/', views.customer_search_modal, name='customer_search_modal'),
    path('tickets/<int:pk>/customer/search/results/', views.customer_search_results, name='customer_search_results'),
    path('tickets/<int:pk>/customer/<int:customer_id>/select/', views.customer_select, name='customer_select'),
    path('tickets/<int:pk>/customer/create/', views.customer_create_modal, name='customer_create_modal'),
    path('tickets/<int:pk>/customer/create/submit/', views.customer_create, name='customer_create'),
    
    # Ship-To Address Management
    path('customers/<int:customer_id>/ship-to/list/', views.customer_ship_to_list, name='customer_ship_to_list'),
    path('customers/<int:customer_id>/ship-to/create/', views.customer_ship_to_create_modal, name='customer_ship_to_create_modal'),
    path('customers/<int:customer_id>/ship-to/create/submit/', views.customer_ship_to_create, name='customer_ship_to_create'),
    path('tickets/<int:pk>/ship-to/<int:address_id>/select/', views.job_select_ship_to, name='job_select_ship_to'),
    path('<int:pk>/ship-to/<int:address_id>/select/', views.job_select_ship_to, name='job_ship_to_select'),  # For job edit page
    
    # Customer Management URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_create_page, name='customer_create_page'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customers/<int:customer_id>/ship-to/<int:address_id>/edit/', views.customer_ship_to_edit_modal, name='customer_ship_to_edit_modal'),
    path('customers/<int:customer_id>/ship-to/<int:address_id>/update/', views.customer_ship_to_update, name='customer_ship_to_update'),
    path('customers/<int:customer_id>/ship-to/<int:address_id>/delete/', views.customer_ship_to_delete, name='customer_ship_to_delete'),
    
    # Engine Search & Selection
    path('tickets/<int:pk>/engine/search/', views.engine_search_modal, name='engine_search_modal'),
    path('tickets/<int:pk>/engine/search/results/', views.engine_search_results, name='engine_search_results'),
    path('tickets/<int:pk>/engine/<int:engine_id>/select/', views.engine_select, name='engine_select'),
    path('tickets/<int:pk>/engine/create/', views.engine_create_modal, name='engine_create_modal'),
    path('tickets/<int:pk>/engine/create/submit/', views.engine_create, name='engine_create'),
    
    # Job User Assignment URLs
    path('<int:pk>/users/assign/modal/', views.job_user_assign_modal, name='job_user_assign_modal'),
    path('<int:pk>/users/assign/', views.job_user_assign, name='job_user_assign'),
    path('<int:job_pk>/users/<int:user_pk>/remove/', views.job_user_remove, name='job_user_remove'),
    
    # Job Build List URLs
    path('<int:pk>/buildlists/add/modal/', views.job_buildlist_add_modal, name='job_buildlist_add_modal'),
    path('<int:pk>/buildlists/add/modal/results/', views.job_buildlist_add_results, name='job_buildlist_add_results'),
    path('<int:pk>/buildlists/<int:buildlist_pk>/add/', views.job_buildlist_add, name='job_buildlist_add'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/remove/', views.job_buildlist_remove, name='job_buildlist_remove'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/toggle-select/', views.job_buildlist_toggle_select, name='job_buildlist_toggle_select'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/items/', views.job_buildlist_items_modal, name='job_buildlist_items_modal'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/items/<int:item_pk>/toggle-on-job/', views.job_buildlist_item_toggle_on_job, name='job_buildlist_item_toggle_on_job'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/items/<int:item_pk>/toggle-complete/', views.job_buildlist_item_toggle_complete, name='job_buildlist_item_toggle_complete'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/add-time/modal/', views.job_buildlist_quick_time_modal, name='job_buildlist_quick_time_modal'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/add-time/', views.job_buildlist_quick_time_submit, name='job_buildlist_quick_time_submit'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/items/<int:item_pk>/add-time/modal/', views.job_buildlist_item_quick_time_modal, name='job_buildlist_item_quick_time_modal'),
    path('<int:job_pk>/buildlists/<int:buildlist_pk>/items/<int:item_pk>/add-time/', views.job_buildlist_item_quick_time_submit, name='job_buildlist_item_quick_time_submit'),
    
    # Job Kit URLs
    path('<int:pk>/kits/add/modal/', views.job_kit_add_modal, name='job_kit_add_modal'),
    path('<int:pk>/kits/add/modal/results/', views.job_kit_add_results, name='job_kit_add_results'),
    path('<int:pk>/kits/<int:kit_pk>/add/', views.job_kit_add, name='job_kit_add'),
    path('<int:job_pk>/kits/<int:kit_pk>/remove/', views.job_kit_remove, name='job_kit_remove'),
    path('<int:job_pk>/kits/<int:kit_pk>/toggle-select/', views.job_kit_toggle_select, name='job_kit_toggle_select'),
    path('<int:job_pk>/kits/<int:kit_pk>/update-notes/', views.job_kit_update_notes, name='job_kit_update_notes'),
    path('<int:job_pk>/kits/<int:kit_pk>/items/', views.job_kit_items_modal, name='job_kit_items_modal'),
    path('<int:job_pk>/kits/<int:kit_pk>/items/<int:item_pk>/toggle-on-job/', views.job_kit_item_toggle_on_job, name='job_kit_item_toggle_on_job'),
    path('<int:job_pk>/kits/<int:kit_pk>/items/<int:item_pk>/toggle-complete/', views.job_kit_item_toggle_complete, name='job_kit_item_toggle_complete'),
    
    # Job Part URLs
    path('<int:pk>/parts/add/modal/', views.job_part_add_modal, name='job_part_add_modal'),
    path('<int:pk>/parts/add/modal/results/', views.job_part_add_results, name='job_part_add_results'),
    path('<int:pk>/parts/<int:part_pk>/add/', views.job_part_add, name='job_part_add'),
    path('<int:job_pk>/parts/<int:part_pk>/remove/', views.job_part_remove, name='job_part_remove'),
    path('<int:job_pk>/parts/<int:part_pk>/toggle-select/', views.job_part_toggle_select, name='job_part_toggle_select'),
    path('<int:job_pk>/parts/<int:part_pk>/update/', views.job_part_update, name='job_part_update'),
    
    # Job PO Creation URLs
    path('<int:pk>/create-po/modal/', views.job_create_po_modal, name='job_create_po_modal'),
    path('<int:pk>/create-po/', views.job_create_po, name='job_create_po'),
    
    # Job Attachment URLs
    path('<int:pk>/attachments/upload/', views.job_attachment_upload, name='job_attachment_upload'),
    path('<int:job_pk>/attachments/<int:attachment_pk>/delete/', views.job_attachment_delete, name='job_attachment_delete'),
    
    # Time Tracking URLs
    path('time-tracking/', views.time_tracking_page, name='time_tracking_page'),
    path('time-tracking/start/', views.time_tracking_start, name='time_tracking_start'),
    path('time-tracking/end/<int:time_entry_pk>/', views.time_tracking_end, name='time_tracking_end'),
    path('time-tracking/history/<int:user_pk>/', views.time_tracking_history, name='time_tracking_history'),
    path('time-tracking/job-buildlists/<int:job_pk>/', views.time_tracking_job_buildlists, name='time_tracking_job_buildlists'),
    path('time-tracking/buildlist-items/<int:buildlist_pk>/', views.time_tracking_buildlist_items, name='time_tracking_buildlist_items'),
    path('time-tracking/active-entry/', views.time_tracking_active_entry, name='time_tracking_active_entry'),
    path('time-tracking/entry/<int:time_entry_pk>/edit/', views.time_entry_edit_modal, name='time_entry_edit_modal'),
    path('time-tracking/entry/<int:time_entry_pk>/update/', views.time_entry_update, name='time_entry_update'),
    path('time-tracking/entry/<int:time_entry_pk>/delete/', views.time_entry_delete, name='time_entry_delete'),
    
    # Notification URLs
    path('notifications/', views.dashboard_notifications, name='dashboard_notifications'),
    path('notifications/sidebar/', views.sidebar_notification_indicator, name='sidebar_notification_indicator'),
    path('notifications/<int:pk>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/<int:pk>/mark-unread/', views.notification_mark_unread, name='notification_mark_unread'),
    path('notifications/<int:notification_pk>/reply/', views.notification_reply, name='notification_reply'),
    path('notifications/<int:notification_pk>/reply-all/', views.notification_reply_all, name='notification_reply_all'),
    path('<int:pk>/notify-team/modal/', views.job_notify_team_modal, name='job_notify_team_modal'),
    path('<int:pk>/notify-team/', views.job_notify_team, name='job_notify_team'),
    path('notifications/api/', views.notifications_api, name='notifications_api'),
    path('notifications/send/modal/', views.send_notification_modal, name='send_notification_modal'),
    path('notifications/send/', views.send_notification, name='send_notification'),
    path('notifications/job-search/', views.notification_job_search, name='notification_job_search'),
    
    # Purchase Order URLs
    path('pos/', views.purchase_order_list, name='purchase_order_list'),
    path('pos/new/', views.purchase_order_create, name='po_create'),
    path('pos/<int:pk>/', views.purchase_order_detail, name='po_detail'),
    path('pos/<int:pk>/delete/', views.purchase_order_delete, name='po_delete'),
    
    # PO Vendor Selection
    path('pos/<int:pk>/vendor/search/', views.po_vendor_search_modal, name='po_vendor_search_modal'),
    path('pos/<int:pk>/vendor/search/results/', views.po_vendor_search_results, name='po_vendor_search_results'),
    path('pos/<int:pk>/vendor/<int:vendor_id>/select/', views.po_vendor_select, name='po_vendor_select'),
    path('pos/<int:pk>/vendor/create/', views.po_vendor_create, name='po_vendor_create'),
    
    # PO Ship To Address
    path('pos/default-address/', views.po_get_default_address, name='po_get_default_address'),
    path('pos/<int:pk>/customer/search/', views.po_customer_search_modal, name='po_customer_search_modal'),
    path('pos/<int:pk>/customer/search/results/', views.po_customer_search_results, name='po_customer_search_results'),
    
    # PO Item Management
    path('pos/<int:pk>/items/add/modal/', views.po_item_add_modal, name='po_item_add_modal'),
    path('pos/<int:pk>/items/add/results/', views.po_item_add_results, name='po_item_add_results'),
    path('pos/<int:pk>/items/<int:part_pk>/add/', views.po_item_add, name='po_item_add'),
    path('pos/<int:pk>/items/custom/add/', views.po_custom_item_add, name='po_custom_item_add'),
    path('pos/<int:pk>/items/<int:item_pk>/edit/modal/', views.po_item_edit_modal, name='po_item_edit_modal'),
    path('pos/<int:pk>/items/<int:item_pk>/remove/', views.po_item_remove, name='po_item_remove'),
    path('pos/<int:pk>/items/<int:item_pk>/update/', views.po_item_update, name='po_item_update'),
    
    # PO Receiving
    path('pos/<int:pk>/items/<int:item_pk>/receive/modal/', views.po_item_receive_modal, name='po_item_receive_modal'),
    path('pos/<int:pk>/items/<int:item_pk>/receive/', views.po_item_receive_submit, name='po_item_receive_submit'),
    path('pos/<int:pk>/items/<int:item_pk>/receive/history/', views.po_item_receive_history, name='po_item_receive_history'),
    path('pos/<int:pk>/items/<int:item_pk>/receive/<int:receive_pk>/edit/modal/', views.po_receive_edit_modal, name='po_receive_edit_modal'),
    path('pos/<int:pk>/items/<int:item_pk>/receive/<int:receive_pk>/update/', views.po_receive_update, name='po_receive_update'),
    path('pos/<int:pk>/items/<int:item_pk>/receive/<int:receive_pk>/delete/', views.po_receive_delete, name='po_receive_delete'),
    
    # PO Attachments
    path('pos/<int:pk>/attachments/upload/', views.po_attachment_upload, name='po_attachment_upload'),
    path('pos/<int:pk>/attachments/<int:attachment_pk>/delete/', views.po_attachment_delete, name='po_attachment_delete'),
]
