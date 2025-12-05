from django.urls import path
from . import views

app_name = 'settings_app'

urlpatterns = [
    # Main settings page
    path('', views.settings_index, name='settings_index'),
    
    # User management
    path('users/list/', views.users_list_data, name='users_list_data'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    
    # Role management
    path('roles/list/', views.roles_list_data, name='roles_list_data'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    
    # System configuration
    path('config/edit/', views.system_config_edit, name='system_config_edit'),
    
    # Job Selection Options
    path('selection-options/', views.selection_options_list, name='selection_options_list'),
    path('selection-options/create/modal/', views.selection_option_create_modal, name='selection_option_create_modal'),
    path('selection-options/create/', views.selection_option_create, name='selection_option_create'),
    path('selection-options/<int:pk>/edit/modal/', views.selection_option_update_modal, name='selection_option_update_modal'),
    path('selection-options/<int:pk>/edit/', views.selection_option_update, name='selection_option_update'),
    path('selection-options/<int:pk>/delete/', views.selection_option_delete, name='selection_option_delete'),
    
    # Selection Option Search Modals
    path('selection-options/search/part/', views.so_part_search_modal, name='so_part_search_modal'),
    path('selection-options/search/part/results/', views.so_part_search_results, name='so_part_search_results'),
    path('selection-options/search/kit/', views.so_kit_search_modal, name='so_kit_search_modal'),
    path('selection-options/search/kit/results/', views.so_kit_search_results, name='so_kit_search_results'),
    path('selection-options/search/buildlist/', views.so_buildlist_search_modal, name='so_buildlist_search_modal'),
    path('selection-options/search/buildlist/results/', views.so_buildlist_search_results, name='so_buildlist_search_results'),
    
    # Part Categories
    path('part-categories/', views.part_categories_list, name='part_categories_list'),
    path('part-categories/create/modal/', views.part_category_create_modal, name='part_category_create_modal'),
    path('part-categories/create/', views.part_category_create, name='part_category_create'),
    path('part-categories/<int:pk>/', views.part_category_detail, name='part_category_detail'),
    path('part-categories/<int:pk>/edit/modal/', views.part_category_edit_modal, name='part_category_edit_modal'),
    path('part-categories/<int:pk>/edit/', views.part_category_update, name='part_category_update'),
    path('part-categories/<int:pk>/delete/', views.part_category_delete, name='part_category_delete'),
    
    # Part Category Attributes
    path('part-categories/<int:category_pk>/attributes/create/modal/', views.part_attribute_create_modal, name='part_attribute_create_modal'),
    path('part-categories/<int:category_pk>/attributes/create/', views.part_attribute_create, name='part_attribute_create'),
    path('part-categories/<int:category_pk>/attributes/<int:attribute_pk>/edit/modal/', views.part_attribute_edit_modal, name='part_attribute_edit_modal'),
    path('part-categories/<int:category_pk>/attributes/<int:attribute_pk>/edit/', views.part_attribute_update, name='part_attribute_update'),
    path('part-categories/<int:category_pk>/attributes/<int:attribute_pk>/delete/', views.part_attribute_delete, name='part_attribute_delete'),
    
    # Part Attribute Choices
    path('part-categories/<int:category_pk>/attributes/<int:attribute_pk>/choices/create/modal/', views.part_attribute_choice_create_modal, name='part_attribute_choice_create_modal'),
    path('part-categories/<int:category_pk>/attributes/<int:attribute_pk>/choices/create/', views.part_attribute_choice_create, name='part_attribute_choice_create'),
    path('part-categories/<int:category_pk>/attributes/<int:attribute_pk>/choices/<int:choice_pk>/delete/', views.part_attribute_choice_delete, name='part_attribute_choice_delete'),
]




