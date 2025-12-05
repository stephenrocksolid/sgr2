"""
View utilities for reusable list view functionality.
Provides common functionality for search, sorting, and pagination.
"""

from django.core.paginator import Paginator
from django.db.models import Q


def apply_search(queryset, search_query, search_fields):
    """
    Apply search filtering to a queryset across multiple fields.
    
    Args:
        queryset: Django queryset to filter
        search_query: Search string from user
        search_fields: List of field names to search (supports __ lookups)
        
    Returns:
        Filtered queryset
        
    Example:
        queryset = apply_search(
            queryset, 
            "john", 
            ['name', 'customer__name', 'description']
        )
    """
    if not search_query or not search_fields:
        return queryset
    
    # Build Q objects for each field
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": search_query})
    
    return queryset.filter(q_objects)


def apply_sorting(queryset, sort_param, allowed_fields, default_sort=None):
    """
    Apply multi-column sorting to a queryset.
    
    Args:
        queryset: Django queryset to sort
        sort_param: Comma-separated sort fields (e.g., "name,-date")
        allowed_fields: Set/list of allowed field names (with and without '-')
        default_sort: Default sort field(s) if none specified
        
    Returns:
        Sorted queryset
        
    Example:
        queryset = apply_sorting(
            queryset,
            "name,-created_at",
            {'name', '-name', 'created_at', '-created_at'},
            default_sort=['name']
        )
    """
    if default_sort is None:
        default_sort = []
    
    sort_fields = []
    
    # Parse sort parameter
    if sort_param:
        for field in sort_param.split(','):
            field = field.strip()
            if field in allowed_fields:
                sort_fields.append(field)
    
    # Use default if no valid sort fields
    if not sort_fields:
        sort_fields = default_sort if isinstance(default_sort, list) else [default_sort]
    
    if sort_fields:
        return queryset.order_by(*sort_fields)
    
    return queryset


def paginate_queryset(queryset, page_number, per_page=50):
    """
    Paginate a queryset and return pagination context.
    
    Args:
        queryset: Django queryset to paginate
        page_number: Current page number
        per_page: Items per page (default: 50)
        
    Returns:
        Dictionary with pagination context:
        {
            'page_obj': Page object,
            'object_list': List of objects on current page,
            'total_count': Total number of items
        }
        
    Example:
        context = paginate_queryset(queryset, request.GET.get('page'), per_page=25)
    """
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page_number)
    
    return {
        'page_obj': page_obj,
        'object_list': page_obj.object_list,
        'total_count': paginator.count,
    }


def get_list_context(queryset, request, search_fields, sort_fields, 
                     default_sort=None, per_page=50):
    """
    Complete list view context builder.
    Combines search, sorting, and pagination in one convenient function.
    
    Args:
        queryset: Base Django queryset
        request: Django request object
        search_fields: List of fields to search across
        sort_fields: Set/list of allowed sort fields
        default_sort: Default sort field(s)
        per_page: Items per page
        
    Returns:
        Dictionary with complete context for list views:
        {
            'page_obj': Page object,
            'object_list': List of objects on current page,
            'total_count': Total number of items,
            'search': Current search query,
            'sort': Current sort parameter
        }
        
    Example:
        def my_list_view(request):
            queryset = MyModel.objects.all()
            context = get_list_context(
                queryset,
                request,
                search_fields=['name', 'description'],
                sort_fields={'name', '-name', 'created_at', '-created_at'},
                default_sort=['name'],
                per_page=25
            )
            return render(request, 'my_list.html', context)
    """
    # Get parameters from request
    search_query = request.GET.get('search', '').strip()
    sort_param = request.GET.get('sort', '').strip()
    page_number = request.GET.get('page')
    
    # Apply search
    queryset = apply_search(queryset, search_query, search_fields)
    
    # Apply sorting
    queryset = apply_sorting(queryset, sort_param, sort_fields, default_sort)
    
    # Paginate
    pagination_context = paginate_queryset(queryset, page_number, per_page)
    
    # Build complete context
    context = {
        **pagination_context,
        'search': search_query,
        'sort': sort_param,
    }
    
    return context






