from django.urls import path
from . import views

app_name = 'imports'

urlpatterns = [
    path('', views.index, name='index'),
    
    # Import wizard steps
    path('upload/', views.upload_step, name='upload_step'),
    path('<int:batch_id>/options/', views.options_step, name='options_step'),
    path('<int:batch_id>/mapping/', views.mapping_step, name='mapping_step'),
    path('<int:batch_id>/processing/', views.processing_step, name='processing_step'),
    
    # Batch management
    path('<int:batch_id>/', views.batch_detail, name='batch_detail'),
    path('<int:batch_id>/status/', views.batch_status, name='batch_status'),
    path('<int:batch_id>/rows/', views.batch_rows, name='batch_rows'),
    
    # Saved mappings
    path('mappings/', views.saved_mappings_list, name='saved_mappings_list'),
    path('mappings/<int:mapping_id>/load/', views.load_saved_mapping, name='load_saved_mapping'),
    
    # Unmatched items
    path('unmatched/', views.unmatched_index, name='unmatched_index'),
    path('unmatched/engines/', views.unmatched_engines, name='unmatched_engines'),
    path('unmatched/machines/', views.unmatched_machines, name='unmatched_machines'),
    path('unmatched/parts/', views.unmatched_parts, name='unmatched_parts'),
    path('unmatched/models-for-make/', views.models_for_make, name='models_for_make'),
    path('unmatched/match-single/', views.match_single, name='match_single'),
    path('unmatched/sg-models-by-letter/', views.sg_models_by_letter, name='sg_models_by_letter'),
    path('unmatched/sg-make-for-model/', views.sg_make_for_model, name='sg_make_for_model'),
    path('unmatched/engines/identifiers/', views.engine_identifiers, name='engine_identifiers'),
    path('unmatched/search-sg-engines/', views.search_sg_engines, name='search_sg_engines'),
    path('unmatched/create-sg-engine/', views.create_sg_engine, name='create_sg_engine'),
]
