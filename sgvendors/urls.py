from django.urls import path
from . import views

app_name = 'sgvendors'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.create, name='create'),
    path('<int:sg_vendor_id>/', views.detail, name='detail'),
    path('<int:sg_vendor_id>/edit/', views.edit, name='edit'),
    path('create/', views.create_ajax, name='create_ajax'),
    path('search/', views.search, name='search'),
]


