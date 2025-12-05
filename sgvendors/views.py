from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from inventory.models import SGVendor, Vendor
from .forms import SGVendorForm


@login_required
def index(request):
    """List all SG Vendors."""
    # Get filter parameters
    search = request.GET.get('search', '')
    sort = request.GET.get('sort', 'name')  # Default sort by name
    
    # Build query
    sg_vendors = SGVendor.objects.all()
    
    if search:
        sg_vendors = sg_vendors.filter(
            Q(name__icontains=search) |
            Q(website__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Annotate with linked vendors count
    sg_vendors = sg_vendors.annotate(
        linked_vendors_count=Count('vendors', distinct=True)
    )
    
    # Handle sorting (support multi-column sorting)
    if sort:
        sort_fields = [s.strip() for s in sort.split(',') if s.strip()]
        valid_fields = ['name', '-name', 'website', '-website', 'created', '-created', 
                       'linked_vendors_count', '-linked_vendors_count']
        # Filter to only valid sort fields
        sort_fields = [f for f in sort_fields if f in valid_fields]
        if sort_fields:
            sg_vendors = sg_vendors.order_by(*sort_fields)
        else:
            sg_vendors = sg_vendors.order_by('name')
    else:
        sg_vendors = sg_vendors.order_by('name')
    
    # Pagination
    paginator = Paginator(sg_vendors, 50)  # Reduced from 200 for better UX
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'sort': sort,
        'total_count': paginator.count,
    }
    return render(request, 'sgvendors/index.html', context)


@login_required
def create(request):
    """Create a new SG Vendor."""
    if request.method == 'POST':
        form = SGVendorForm(request.POST)
        if form.is_valid():
            sg_vendor = form.save()
            messages.success(request, f'SG Vendor "{sg_vendor.name}" created successfully.')
            return redirect('sgvendors:detail', sg_vendor_id=sg_vendor.id)
    else:
        form = SGVendorForm()
    
    context = {
        'form': form,
        'sg_vendor': None,
        'linked_vendors': [],
        'is_new': True,
    }
    return render(request, 'sgvendors/edit.html', context)


@login_required
def edit(request, sg_vendor_id):
    """Edit an existing SG Vendor (combined view/edit page)."""
    sg_vendor = get_object_or_404(SGVendor, id=sg_vendor_id)
    
    # Get linked vendors
    linked_vendors = sg_vendor.vendors.all().order_by('name')
    
    if request.method == 'POST':
        form = SGVendorForm(request.POST, instance=sg_vendor)
        if form.is_valid():
            sg_vendor = form.save()
            messages.success(request, f'SG Vendor "{sg_vendor.name}" updated successfully.')
            return redirect('sgvendors:detail', sg_vendor_id=sg_vendor.id)
    else:
        form = SGVendorForm(instance=sg_vendor)
    
    context = {
        'form': form,
        'sg_vendor': sg_vendor,
        'linked_vendors': linked_vendors,
        'is_new': False,
    }
    return render(request, 'sgvendors/edit.html', context)


@login_required
@require_http_methods(["POST"])
def delete(request, sg_vendor_id):
    """Delete an SG Vendor."""
    sg_vendor = get_object_or_404(SGVendor, id=sg_vendor_id)
    
    # Check if there are linked vendors
    if sg_vendor.vendors.exists():
        messages.error(request, f'Cannot delete "{sg_vendor.name}" because it has linked vendors.')
        return redirect('sgvendors:detail', sg_vendor_id=sg_vendor.id)
    
    name = sg_vendor.name
    sg_vendor.delete()
    messages.success(request, f'SG Vendor "{name}" deleted successfully.')
    return redirect('sgvendors:index')


@login_required
@require_http_methods(["POST"])
def create_ajax(request):
    """Create SG Vendor via AJAX (for use in modals)."""
    form = SGVendorForm(request.POST)
    if form.is_valid():
        sg_vendor = form.save()
        return JsonResponse({
            'success': True,
            'sg_vendor_id': sg_vendor.id,
            'name': sg_vendor.name,
            'website': sg_vendor.website or '',
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid form data',
            'errors': form.errors
        })


@login_required
def search(request):
    """Search SG Vendors via AJAX."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse([])
    
    sg_vendors = SGVendor.objects.filter(
        name__icontains=query
    ).order_by('name')[:10]
    
    results = []
    for sgv in sg_vendors:
        results.append({
            'id': sgv.id,
            'name': sgv.name,
            'website': sgv.website or '',
        })
    
    return JsonResponse(results, safe=False)







