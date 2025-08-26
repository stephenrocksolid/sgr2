from django.shortcuts import render
from django.http import HttpResponse
from imports.tasks import test_task

# Create your views here.

def home(request):
    # Test Celery task (disabled for now to avoid Redis connection issues)
    # result = test_task.delay()
    
    # Sample data for demo table
    sample_data = [
        {'id': 1, 'name': 'John Deere 4020', 'type': 'Tractor', 'year': 1965, 'status': 'Active'},
        {'id': 2, 'name': 'Ford 8N', 'type': 'Tractor', 'year': 1952, 'status': 'Active'},
        {'id': 3, 'name': 'International Harvester 1066', 'type': 'Tractor', 'year': 1971, 'status': 'Active'},
        {'id': 4, 'name': 'Case IH Magnum 340', 'type': 'Tractor', 'year': 2005, 'status': 'Active'},
        {'id': 5, 'name': 'New Holland T4.75', 'type': 'Tractor', 'year': 2018, 'status': 'Active'},
        {'id': 6, 'name': 'Kubota L3901', 'type': 'Tractor', 'year': 2020, 'status': 'Active'},
        {'id': 7, 'name': 'Massey Ferguson 135', 'type': 'Tractor', 'year': 1964, 'status': 'Active'},
        {'id': 8, 'name': 'Allis-Chalmers WD45', 'type': 'Tractor', 'year': 1953, 'status': 'Active'},
        {'id': 9, 'name': 'Oliver 77', 'type': 'Tractor', 'year': 1948, 'status': 'Active'},
        {'id': 10, 'name': 'Farmall M', 'type': 'Tractor', 'year': 1939, 'status': 'Active'},
        {'id': 11, 'name': 'McCormick-Deering 10-20', 'type': 'Tractor', 'year': 1923, 'status': 'Active'},
        {'id': 12, 'name': 'Minneapolis-Moline U', 'type': 'Tractor', 'year': 1934, 'status': 'Active'},
        {'id': 13, 'name': 'Cockshutt 30', 'type': 'Tractor', 'year': 1946, 'status': 'Active'},
        {'id': 14, 'name': 'David Brown 990', 'type': 'Tractor', 'year': 1965, 'status': 'Active'},
        {'id': 15, 'name': 'Ferguson TO-20', 'type': 'Tractor', 'year': 1948, 'status': 'Active'},
    ]
    
    context = {
        'celery_task_id': 'Demo Mode - Celery disabled',
        'sample_data': sample_data,
    }
    
    return render(request, 'core/home.html', context)
