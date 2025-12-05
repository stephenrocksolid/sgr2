from django.urls import path
from . import views

app_name = 'sgvendors'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.create, name='create'),
    path('<int:sg_vendor_id>/', views.edit, name='detail'),  # Combined view/edit page
    path('<int:sg_vendor_id>/edit/', views.edit, name='edit'),  # Also accessible via /edit/
    path('<int:sg_vendor_id>/delete/', views.delete, name='delete'),  # Delete action
    path('create/', views.create_ajax, name='create_ajax'),
    path('search/', views.search, name='search'),
]















