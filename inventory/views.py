import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.views.decorators.http import require_http_methods, require_POST
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse
from .models import Machine, Engine, Part, PartVendor, MachineEngine, EnginePart, SGEngine, MachinePart, PartAttribute, PartAttributeValue, PartAttributeChoice, PartCategory, Vendor, VendorContact, BuildList, BuildListItem, Kit, KitItem, Casting, EngineSupercession
from .forms import SGEngineForm, EngineInterchangeForm, EngineCompatibleForm, EngineSupercessionForm, KitForm, KitItemForm, MachineForm, EngineForm, PartForm, PartSpecsForm, VendorForm, VendorContactForm, VendorContactFormSet, PartVendorForm, PartVendorFormSet, BuildListForm, BuildListItemForm, CastingForm
from django.contrib.auth.decorators import login_required
from io import StringIO
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction, IntegrityError
from django.http import HttpResponseBadRequest, HttpResponse
from django.template.loader import render_to_string


@login_required
def index(request):
    return HttpResponse("""
    <h1>Inventory Management</h1>
    <p>Inventory management features will be implemented here.</p>
    <a href="/machines/">Machines</a> | <a href="/engines/">Engines</a> | <a href="/parts/">Parts</a> | <a href="/">Back to Home</a>
    """)


@login_required
def machines_list(request):
    """Display a list of machines with advanced search and filtering."""
    from .search_utils import parse_query, apply_tokens, apply_generics
    
    # Map tokens → lookups
    MACHINES_KEY_MAP = {
        'make': 'make__icontains',
        'model': 'model__icontains',
        'year': 'year__icontains',
        'type': 'machine_type__icontains',
        'market': 'market_type__icontains',
    }
    
    MACHINES_GENERIC_FIELDS = [
        'make__icontains',
        'model__icontains', 
        'year__icontains',
        'machine_type__icontains',
        'market_type__icontains',
    ]
    
    # Get search query and sorting parameters
    qtext = request.GET.get('q', '').strip()
    sort_param = request.GET.get('sort', 'make').strip()
    type_filter = request.GET.get('type_filter', 'all').strip()
    
    # Base queryset
    machines = Machine.objects.all()
    
    # Calculate stats for all machines (before filtering)
    stats = {
        'crawler': Machine.objects.filter(machine_type__icontains='crawler').count(),
        'wheel': Machine.objects.filter(machine_type__icontains='wheel').count(),
        'skid_steer': Machine.objects.filter(machine_type__icontains='skid').count(),
    }
    
    # Get unique machine types for filter tabs
    machine_types = Machine.objects.values_list('machine_type', flat=True).distinct().order_by('machine_type')
    unique_types = [t for t in machine_types if t][:5]  # Top 5 types for tabs
    
    # Apply type filter if specified
    if type_filter and type_filter != 'all':
        machines = machines.filter(machine_type__icontains=type_filter)
    
    # Apply advanced search if query provided
    if qtext:
        tokens, generic = parse_query(qtext)
        machines = apply_tokens(machines, tokens, MACHINES_KEY_MAP)
        machines = apply_generics(machines, generic, MACHINES_GENERIC_FIELDS)
        machines = machines.distinct()
    
    # Multi-column sorting
    allowed_sort_fields = {
        'make', '-make', 'model', '-model', 'year', '-year',
        'machine_type', '-machine_type', 'market_type', '-market_type',
        'created_at', '-created_at'
    }
    sort_fields = []
    for field in sort_param.split(','):
        field = field.strip()
        if field in allowed_sort_fields:
            sort_fields.append(field)
    
    if not sort_fields:
        sort_fields = ['make', 'model']
    
    machines = machines.order_by(*sort_fields)
    
    # Pagination
    paginator = Paginator(machines, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="machines.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Make', 'Model', 'Year', 'Machine Type', 'Market Type'])
        
        for machine in machines:
            writer.writerow([
                machine.make,
                machine.model,
                machine.year,
                machine.machine_type,
                machine.market_type
            ])
        
        return response
    
    context = {
        'page_obj': page_obj,
        'machines': page_obj.object_list,
        'total_count': paginator.count,
        'q': qtext,
        'sort': sort_param,
        'stats': stats,
        'type_filter': type_filter,
        'unique_types': unique_types,
    }
    
    return render(request, 'inventory/machines_list.html', context)


@login_required
def machine_detail(request, machine_id):
    """Redirect to machine edit page (combined view/edit)."""
    return redirect("inventory:machine_edit", pk=machine_id)


@login_required
def machine_create(request):
    """Create a new machine."""
    if request.method == 'POST':
        form = MachineForm(request.POST)
        if form.is_valid():
            machine = form.save()
            return redirect('inventory:machine_edit', pk=machine.pk)
    else:
        form = MachineForm()
    
    return render(request, 'inventory/machines/edit.html', {
        'form': form,
        'machine': None,
        'is_new': True,
        'engine_count': 0,
        'part_count': 0,
    })


@login_required
@require_http_methods(["GET"])
def machine_edit(request, pk):
    """Display the machine edit form (combined view/edit page)."""
    machine = get_object_or_404(Machine, pk=pk)
    form = MachineForm(instance=machine)
    
    # Get related counts for quick stats
    engine_count = MachineEngine.objects.filter(machine=machine).count()
    part_count = MachinePart.objects.filter(machine=machine).count()
    
    context = {
        "machine": machine,
        "form": form,
        "is_new": False,
        "engine_count": engine_count,
        "part_count": part_count,
    }
    return render(request, "inventory/machines/edit.html", context)


@login_required
@require_http_methods(["POST"])
def machine_update(request, pk):
    """Handle machine update form submission."""
    machine = get_object_or_404(Machine, pk=pk)
    form = MachineForm(request.POST, instance=machine)
    if form.is_valid():
        form.save()
        return redirect("inventory:machine_edit", pk=machine.pk)
    # on errors, re-render edit page with validation messages
    engine_count = MachineEngine.objects.filter(machine=machine).count()
    part_count = MachinePart.objects.filter(machine=machine).count()
    context = {
        "machine": machine,
        "form": form,
        "engine_count": engine_count,
        "part_count": part_count,
    }
    return render(request, "inventory/machines/edit.html", context, status=400)


@login_required
@require_http_methods(["POST"])
def machine_delete(request, pk):
    """Delete a machine."""
    machine = get_object_or_404(Machine, pk=pk)
    machine_name = f"{machine.year} {machine.make} {machine.model}"
    machine.delete()
    messages.success(request, f"Machine '{machine_name}' deleted successfully.")
    return redirect("inventory:machines_list")


@login_required
def engines_list(request):
    """Display a list of engines with advanced search and filtering."""
    import re
    from django.db.models import Q
    
    # Token parsing regex for key:value pairs
    TOKEN_RE = re.compile(r'''(?P<key>\w+):(?P<val>"[^"]+"|\S+)''')
    
    def parse_query(q):
        """Parse search query into tokens and generic terms."""
        q = (q or "").strip()
        tokens = [(m.group('key').lower(), m.group('val').strip('"')) for m in TOKEN_RE.finditer(q)]
        consumed = set(m.span() for m in TOKEN_RE.finditer(q))
        generic = [w for i,w in enumerate(q.split()) if not any(s<=q.find(w)<e for s,e in consumed)]
        return tokens, generic
    
    # Field mapping for supported search keys
    KEY_MAP = {
        'make': 'engine_make__icontains',
        'model': 'engine_model__icontains',
        'identifier': 'identifier__icontains',
        'id': 'identifier__icontains',
        'sg_identifier': 'sg_engine__identifier__icontains',
        'sg_make': 'sg_engine__sg_make__icontains',
        'sg_model': 'sg_engine__sg_model__icontains',
        'cpl': 'cpl_number__icontains',
        'status': 'status__icontains',
        'sn': 'serial_number__icontains',
    }
    
    # Get search query and sorting parameters
    qtext = request.GET.get('q', '').strip()
    sort_param = request.GET.get('sort', 'engine_make').strip()
    make_filter = request.GET.get('make_filter', 'all').strip()
    
    # Base queryset with select_related for performance
    engines = Engine.objects.select_related('sg_engine').all()
    
    # Get unique engine makes for filter tabs (top 5 by count)
    engine_makes = (Engine.objects
        .values_list('engine_make', flat=True)
        .exclude(engine_make__isnull=True)
        .exclude(engine_make='')
        .distinct()
        .order_by('engine_make'))
    unique_makes = list(engine_makes)[:5]  # Top 5 makes for tabs
    
    # Apply advanced search if query provided
    if qtext:
        tokens, generic = parse_query(qtext)
        expr = Q()
        
        # Process fielded tokens (key:value pairs)
        for k, v in tokens:
            field = KEY_MAP.get(k)
            if field:
                expr &= Q(**{field: v})
        
        # Process generic terms (OR across multiple fields)
        if generic:
            g = Q()
            for term in generic:
                g |= (Q(engine_make__icontains=term) |
                      Q(engine_model__icontains=term) |
                      Q(identifier__icontains=term) |
                      Q(sg_engine_identifier__icontains=term) |
                      Q(sg_engine__sg_make__icontains=term) |
                      Q(sg_engine__sg_model__icontains=term) |
                      Q(cpl_number__icontains=term) |
                      Q(status__icontains=term) |
                      Q(serial_number__icontains=term))
            expr &= g
        
        engines = engines.filter(expr).distinct()
    
    # Apply make filter
    if make_filter and make_filter != 'all':
        engines = engines.filter(engine_make__iexact=make_filter)
    
    # Multi-column sorting
    allowed_sort_fields = {
        'engine_make', '-engine_make', 'engine_model', '-engine_model',
        'cpl_number', '-cpl_number', 'ar_number', '-ar_number',
        'status', '-status', 'created_at', '-created_at',
        'serial_number', '-serial_number', 'identifier', '-identifier',
        'price', '-price', 'injection_type', '-injection_type',
        'valve_config', '-valve_config', 'fuel_system_type', '-fuel_system_type',
        'sg_engine__sg_make', '-sg_engine__sg_make',
        'sg_engine__sg_model', '-sg_engine__sg_model',
        'sg_engine__identifier', '-sg_engine__identifier'
    }
    sort_fields = []
    for field in sort_param.split(','):
        field = field.strip()
        if field in allowed_sort_fields:
            sort_fields.append(field)
    
    if not sort_fields:
        sort_fields = ['engine_make', 'engine_model']
    
    engines = engines.order_by(*sort_fields)
    
    # Pagination
    paginator = Paginator(engines, 200)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="engines.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Make', 'Model', 'CPL Number', 'AR Number', 'SG Identifier', 'SG Notes', 'Price', 'Status'])
        
        for engine in engines:
            writer.writerow([
                engine.engine_make,
                engine.engine_model,
                engine.cpl_number or '',
                engine.ar_number or '',
                engine.sg_engine_identifier or '',
                engine.sg_engine_notes or '',
                engine.price or '',
                engine.status or ''
            ])
        
        return response
    
    context = {
        'page_obj': page_obj,
        'engines': page_obj.object_list,
        'total_count': paginator.count,
        'q': qtext,
        'sort': sort_param,
        'make_filter': make_filter,
        'unique_makes': unique_makes,
    }
    
    return render(request, 'inventory/engines_list.html', context)


@login_required
def engine_detail(request, engine_id):
    """Display the engine edit form (combined view/edit page)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    form = EngineForm(instance=engine)
    
    # Get related counts for quick stats
    machine_count = MachineEngine.objects.filter(engine=engine).count()
    part_count = EnginePart.objects.filter(engine=engine).count()
    
    context = {
        'engine': engine,
        'form': form,
        'is_new': False,
        'machine_count': machine_count,
        'part_count': part_count,
        'interchanges': engine.interchanges.all(),
        'compatibles': engine.compatibles.all(),
        'supersedes': engine.supersedes,
        'superseded_by': engine.superseded_by,
    }
    
    return render(request, 'inventory/engines/edit.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def engine_create(request):
    """Create a new engine."""
    if request.method == 'POST':
        form = EngineForm(request.POST)
        if form.is_valid():
            engine = form.save()
            return redirect('inventory:engine_detail', engine_id=engine.pk)
    else:
        form = EngineForm()
    
    return render(request, 'inventory/engines/edit.html', {
        'form': form,
        'engine': None,
        'is_new': True,
        'machine_count': 0,
        'part_count': 0,
    })


@login_required
@require_http_methods(["GET"])
def engine_edit(request, pk):
    """Redirect to engine_detail (which is now the edit page)."""
    return redirect("inventory:engine_detail", engine_id=pk)


@login_required
@require_http_methods(["POST"])
def engine_update(request, pk):
    """Handle engine update form submission."""
    engine = get_object_or_404(Engine, pk=pk)
    form = EngineForm(request.POST, instance=engine)
    if form.is_valid():
        form.save()
        return redirect("inventory:engine_detail", engine_id=engine.pk)
    # on errors, re-render edit page with validation messages
    machine_count = MachineEngine.objects.filter(engine=engine).count()
    part_count = EnginePart.objects.filter(engine=engine).count()
    context = {
        "engine": engine,
        "is_new": False,
        "form": form,
        "machine_count": machine_count,
        "part_count": part_count,
    }
    return render(request, "inventory/engines/edit.html", context, status=400)


@login_required
@require_http_methods(["POST"])
def engine_delete(request, pk):
    """Delete an engine."""
    engine = get_object_or_404(Engine, pk=pk)
    engine_name = f"{engine.engine_make} {engine.engine_model}"
    engine.delete()
    messages.success(request, f"Engine '{engine_name}' deleted successfully.")
    return redirect("inventory:engines_list")


@login_required
def parts_list(request):
    """Display a list of parts with advanced search and filtering."""
    from .search_utils import parse_query, apply_tokens, apply_generics
    
    # Map tokens → lookups
    PARTS_KEY_MAP = {
        'number': 'part_number__icontains',
        'name': 'name__icontains',
        'mfr': 'manufacturer__icontains',
        'manufacturer': 'manufacturer__icontains',
        'category': 'category__name__icontains',
        'unit': 'unit__icontains',
        'type': 'type__icontains',
        'vendor': 'primary_vendor__name__icontains',
    }
    
    PARTS_GENERIC_FIELDS = [
        'part_number__icontains',
        'name__icontains',
        'manufacturer__icontains',
        'category__name__icontains',
        'unit__icontains',
        'type__icontains',
        'primary_vendor__name__icontains',
    ]
    
    # Get search query, sorting, and filter parameters
    qtext = request.GET.get('q', '').strip()
    sort_param = request.GET.get('sort', 'part_number').strip()
    category_filter = request.GET.get('category_filter', '').strip()
    
    # Get unique categories for filter tabs
    unique_categories = list(
        PartCategory.objects.filter(parts__isnull=False)
        .distinct()
        .order_by('name')
        .values_list('name', flat=True)[:10]
    )
    
    # Base queryset with select_related for performance
    parts = Part.objects.select_related('category', 'primary_vendor').prefetch_related('attribute_values__attribute', 'vendor_links__vendor').all()
    
    # Apply category filter
    if category_filter and category_filter != 'all':
        parts = parts.filter(category__name=category_filter)
    
    # Apply advanced search if query provided
    if qtext:
        tokens, generic = parse_query(qtext)
        parts = apply_tokens(parts, tokens, PARTS_KEY_MAP)
        parts = apply_generics(parts, generic, PARTS_GENERIC_FIELDS)
        parts = parts.distinct()
    
    # Multi-column sorting
    allowed_sort_fields = {
        'part_number', '-part_number', 'name', '-name',
        'manufacturer', '-manufacturer', 'type', '-type',
        'created_at', '-created_at', 'category__name', '-category__name'
    }
    sort_fields = []
    for field in sort_param.split(','):
        field = field.strip()
        if field in allowed_sort_fields:
            sort_fields.append(field)
    
    if not sort_fields:
        sort_fields = ['part_number']
    
    parts = parts.order_by(*sort_fields)
    
    # Pagination
    paginator = Paginator(parts, 200)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="parts.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Part Number', 'Name', 'Category', 'Manufacturer', 'Type', 'Primary Vendor'])
        
        for part in parts:
            writer.writerow([
                part.part_number,
                part.name,
                part.category.name if part.category else '',
                part.manufacturer or '',
                part.type or '',
                part.primary_vendor.name if part.primary_vendor else ''
            ])
        
        return response
    
    context = {
        'page_obj': page_obj,
        'parts': page_obj.object_list,
        'total_count': paginator.count,
        'q': qtext,
        'sort': sort_param,
        'category_filter': category_filter,
        'unique_categories': unique_categories,
    }
    
    return render(request, 'inventory/parts_list.html', context)


@login_required
def part_detail(request, part_id):
    """Redirect to the part edit page - view and edit are now combined."""
    return redirect("inventory:part_edit", pk=part_id)


@login_required
@require_http_methods(["GET", "POST"])
def part_create(request):
    """Create a new part."""
    if request.method == 'POST':
        form = PartForm(request.POST)
        if form.is_valid():
            part = form.save()
            return redirect('inventory:part_edit', pk=part.id)
    else:
        form = PartForm()
    
    vendors = Vendor.objects.all().order_by('name')
    categories = PartCategory.objects.all().order_by('name')
    
    return render(request, 'inventory/parts/edit.html', {
        'form': form,
        'part': None,
        'is_new': True,
        'vendors': vendors,
        'categories': categories,
        'engine_count': 0,
        'machine_count': 0,
        'kit_count': 0,
        'vendor_count': 0,
        'total_stock': 0,
    })


@login_required
@require_http_methods(["GET"])
def part_edit(request, pk):
    """Display the part edit form with basic info, specifications, and vendor relationships."""
    part = get_object_or_404(Part, pk=pk)
    form = PartForm(instance=part)
    specs_form = PartSpecsForm(part=part)
    vset = PartVendorFormSet(instance=part, prefix='vendors')
    vendors = Vendor.objects.all().order_by('name')
    categories = PartCategory.objects.all().order_by('name')
    
    # Get counts for stats
    engine_count = EnginePart.objects.filter(part=part).count()
    machine_count = MachinePart.objects.filter(part=part).count()
    kit_count = KitItem.objects.filter(part=part).count()
    vendor_count = PartVendor.objects.filter(part=part).count()
    total_stock = PartVendor.objects.filter(part=part).aggregate(total=Sum('stock_qty'))['total'] or 0
    
    return render(request, "inventory/parts/edit.html", {
        "part": part, 
        "form": form,
        "is_new": False,
        "specs_form": specs_form,
        "vset": vset,
        "vendors": vendors,
        "categories": categories,
        "engine_count": engine_count,
        "machine_count": machine_count,
        "kit_count": kit_count,
        "vendor_count": vendor_count,
        "total_stock": total_stock,
    })


@login_required
@require_http_methods(["POST"])
@transaction.atomic
@login_required
def part_update(request, pk):
    """Handle part update form submission with basic info, specifications, and vendor relationships."""
    part = get_object_or_404(Part, pk=pk)
    old_category = part.category_id
    form = PartForm(request.POST, instance=part)
    vset = PartVendorFormSet(request.POST, instance=part, prefix='vendors')
    
    # Use the current (possibly changed) category to build specs_form
    # but guard confirmation.
    vendors = Vendor.objects.all().order_by('name')
    categories = PartCategory.objects.all().order_by('name')
    engine_count = EnginePart.objects.filter(part=part).count()
    machine_count = MachinePart.objects.filter(part=part).count()
    kit_count = KitItem.objects.filter(part=part).count()
    vendor_count = PartVendor.objects.filter(part=part).count()
    total_stock = PartVendor.objects.filter(part=part).aggregate(total=Sum('stock_qty'))['total'] or 0
    
    if not form.is_valid() or not vset.is_valid():
        specs_form = PartSpecsForm(request.POST, part=part)
        return render(request, "inventory/parts/edit.html", {
            "part": part, 
            "form": form,
            "is_new": False,
            "specs_form": specs_form,
            "vset": vset,
            "vendors": vendors,
            "categories": categories,
            "engine_count": engine_count,
            "machine_count": machine_count,
            "kit_count": kit_count,
            "vendor_count": vendor_count,
            "total_stock": total_stock,
        }, status=400)

    new_category = form.cleaned_data["category"].id
    changing = (new_category != old_category)

    # If category changed but no confirmation flag, block save with message
    if changing and request.POST.get("confirm_category_change") != "1":
        messages.error(request, "Please review the category change preview and confirm before saving.")
        specs_form = PartSpecsForm(request.POST, part=part)
        return render(request, "inventory/parts/edit.html", {
            "part": part, 
            "form": form,
            "is_new": False,
            "specs_form": specs_form,
            "vset": vset,
            "vendors": vendors,
            "categories": categories,
            "engine_count": engine_count,
            "machine_count": machine_count,
            "kit_count": kit_count,
            "vendor_count": vendor_count,
            "total_stock": total_stock,
        }, status=400)

    # Save basic fields (including category)
    form.save()
    
    # Save vendor relationships
    vset.save()
    
    # Auto-set primary vendor if only one vendor exists
    part.auto_set_primary_vendor()

    # Build specs form for the (new) category and validate
    specs_form = PartSpecsForm(request.POST, part=part)
    if not specs_form.is_valid():
        return render(request, "inventory/parts/edit.html", {
            "part": part, 
            "form": form,
            "is_new": False,
            "specs_form": specs_form,
            "vset": vset,
            "vendors": vendors,
            "categories": categories,
            "engine_count": engine_count,
            "machine_count": machine_count,
            "kit_count": kit_count,
            "vendor_count": vendor_count,
            "total_stock": total_stock,
        }, status=400)

    # If changing: carry over values with the same code; drop the rest
    if changing:
        old_vals = PartAttributeValue.objects.select_related("attribute").filter(part=part)
        new_attrs = {a.code: a for a in PartAttribute.objects.filter(category=part.category)}
        # migrate compatible
        for pav in old_vals:
            code = pav.attribute.code or pav.attribute.name
            if code in new_attrs:
                # upsert into the new attribute
                new_attr = new_attrs[code]
                npav, _ = PartAttributeValue.objects.get_or_create(part=part, attribute=new_attr)
                npav.value_text = pav.value_text
                npav.value_int = pav.value_int
                npav.value_dec = pav.value_dec
                npav.value_bool = pav.value_bool
                npav.value_date = pav.value_date
                npav.choice = pav.choice
                npav.save()
        # remove all values not in new category
        PartAttributeValue.objects.filter(part=part).exclude(attribute__category=part.category).delete()

    # Finally, apply posted values for the new category (these win)
    for name, value in specs_form.cleaned_data.items():
        attr_id = int(name.split("_", 1)[1])
        attr = PartAttribute.objects.get(pk=attr_id, category=part.category)
        pav, _ = PartAttributeValue.objects.get_or_create(part=part, attribute=attr)
        pav.value_text = pav.value_int = pav.value_dec = None
        pav.value_bool = None
        pav.value_date = None
        pav.choice = None
        if attr.data_type == "int":
            pav.value_int = value
        elif attr.data_type == "dec":
            pav.value_dec = value
        elif attr.data_type == "bool":
            pav.value_bool = bool(value)
        elif attr.data_type == "date":
            pav.value_date = value
        elif attr.data_type == "choice":
            pav.choice = attr.choices.filter(value=value).first() if value else None
        else:
            pav.value_text = value
        pav.save()

    messages.success(request, "Part updated successfully.")
    return redirect("inventory:parts_list")


@login_required
@require_http_methods(["POST"])
def part_delete(request, pk):
    """Delete a part."""
    part = get_object_or_404(Part, pk=pk)
    part_number = part.part_number
    part.delete()
    messages.success(request, f"Part '{part_number}' has been deleted.")
    return redirect("inventory:parts_list")


def _values_by_code(part):
    """Helper function to get current attribute values organized by code."""
    vals = (PartAttributeValue.objects
            .select_related("attribute")
            .filter(part=part))
    by_code = {}
    for v in vals:
        code = v.attribute.code or v.attribute.name  # fallback
        by_code[code] = v
    return by_code


@login_required
def part_category_preview(request, pk):
    """Preview the impact of changing a part's category."""
    part = get_object_or_404(Part, pk=pk)
    try:
        new_cat_id = int(request.GET.get("category_id"))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("category_id required")

    new_cat = get_object_or_404(PartCategory, pk=new_cat_id)
    new_attrs = PartAttribute.objects.filter(category=new_cat).order_by("sort_order", "name")
    current_by_code = _values_by_code(part)

    will_carry = []
    will_drop = []
    for old_code, pav in current_by_code.items():
        # keep if any attr in new category has same code
        if new_attrs.filter(code=old_code).exists():
            will_carry.append((old_code, pav))
        else:
            will_drop.append((old_code, pav))

    # Render the specs form as it would look for the new category
    # (we pass an ephemeral Part-like object with category=new_cat)
    part.category = new_cat
    specs_form = PartSpecsForm(part=part)  # unbound preview

    html = render_to_string("inventory/parts/_category_change_preview.html", {
        "part": part,
        "new_category": new_cat,
        "specs_form": specs_form,
        "will_carry": will_carry,
        "will_drop": will_drop,
    }, request=request)
    return HttpResponse(html)


@login_required
def part_specs_form(request, part_id):
    """HTMX endpoint to render the specifications form for a part."""
    part = get_object_or_404(Part, pk=part_id)
    
    # Check if a specific category was requested
    category_id = request.GET.get('category_id')
    if category_id:
        try:
            category = PartCategory.objects.get(id=category_id)
            # Update the part's category
            part.category = category
            part.save()
        except PartCategory.DoesNotExist:
            pass
    
    # Get attributes for the part's category
    attributes = []
    if part.category:
        attributes = part.category.attributes.all()
    
    # Get current attribute values
    attribute_values = {}
    for attr_value in part.attribute_values.select_related('attribute', 'choice').all():
        attribute_values[attr_value.attribute_id] = attr_value
    
    context = {
        'part': part,
        'attributes': attributes,
        'attribute_values': attribute_values,
    }
    
    return render(request, 'inventory/partials/_part_specs_form.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_specs_save(request, part_id):
    """HTMX endpoint to save part specifications."""
    part = get_object_or_404(Part, pk=part_id)
    
    if not part.category:
        return HttpResponse("No category selected", status=400)
    
    # Get all attributes for this category
    attributes = part.category.attributes.all()
    
    for attribute in attributes:
        field_name = f"attr_{attribute.id}"
        value = request.POST.get(field_name, '').strip()
        
        # Get or create the attribute value
        attr_value, created = PartAttributeValue.objects.get_or_create(
            part=part,
            attribute=attribute,
            defaults={
                'value_text': '',
                'value_int': None,
                'value_dec': None,
                'value_bool': None,
                'value_date': None,
                'choice': None,
            }
        )
        
        # Clear all value fields first
        attr_value.value_text = ''
        attr_value.value_int = None
        attr_value.value_dec = None
        attr_value.value_bool = None
        attr_value.value_date = None
        attr_value.choice = None
        
        # Set the appropriate value field based on data type
        if attribute.data_type == PartAttribute.DataType.TEXT:
            attr_value.value_text = value
        elif attribute.data_type == PartAttribute.DataType.INTEGER:
            if value:
                try:
                    attr_value.value_int = int(value)
                except ValueError:
                    pass
        elif attribute.data_type == PartAttribute.DataType.DECIMAL:
            if value:
                try:
                    attr_value.value_dec = float(value)
                except ValueError:
                    pass
        elif attribute.data_type == PartAttribute.DataType.BOOLEAN:
            attr_value.value_bool = value.lower() in ('true', '1', 'yes', 'on')
        elif attribute.data_type == PartAttribute.DataType.DATE:
            if value:
                try:
                    attr_value.value_date = datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    pass
        elif attribute.data_type == PartAttribute.DataType.CHOICE:
            if value:
                try:
                    choice = PartAttributeChoice.objects.get(attribute=attribute, value=value)
                    attr_value.choice = choice
                except PartAttributeChoice.DoesNotExist:
                    pass
        
        attr_value.save()
    
    # Re-render the specs form
    return part_specs_form(request, part_id)


@login_required
def filter_value_control(request):
    """HTMX endpoint to render the appropriate value control for a selected attribute."""
    attribute_id = request.GET.get('attribute_id')
    if not attribute_id:
        return HttpResponse("No attribute selected")
    
    try:
        attribute = PartAttribute.objects.get(id=attribute_id)
    except PartAttribute.DoesNotExist:
        return HttpResponse("Attribute not found")
    
    context = {
        'attribute': attribute,
    }
    
    return render(request, 'inventory/partials/_parts_filter_value_control.html', context)


@login_required
def machine_engines_partial(request, machine_id):
    """HTMX endpoint to render the machine engines section (table only)."""
    machine = get_object_or_404(Machine, pk=machine_id)
    machine_engines = machine.machineengine_set.select_related('engine', 'engine__sg_engine').all()
    
    context = {
        'machine': machine,
        'machine_engines': machine_engines,
    }
    
    return render(request, 'inventory/partials/machine_engines_partial.html', context)


@login_required
def engine_search_modal(request, machine_id):
    """HTMX endpoint to render the engine search modal."""
    machine = get_object_or_404(Machine, pk=machine_id)
    
    # Get engines not already associated with this machine
    # Show first 50 by default
    engines = Engine.objects.exclude(
        machineengine__machine=machine
    ).select_related('sg_engine').order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'machine': machine,
        'engines': engines,
        'query': '',
    }
    
    return render(request, 'inventory/partials/engine_search_modal.html', context)


@login_required
def engine_search_results(request, machine_id):
    """HTMX endpoint to return filtered engine search results."""
    machine = get_object_or_404(Machine, pk=machine_id)
    query = request.GET.get('q', '').strip()
    
    # Get engines not already associated with this machine
    engines = Engine.objects.exclude(
        machineengine__machine=machine
    ).select_related('sg_engine')
    
    # Apply search filter
    if query:
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(identifier__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query) |
            Q(sg_engine__identifier__icontains=query)
        )
    
    # Limit results to prevent performance issues
    engines = engines.order_by('engine_make', 'engine_model')[:100]
    
    context = {
        'machine': machine,
        'engines': engines,
        'query': query,
    }
    
    return render(request, 'inventory/partials/engine_search_results.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def machine_engine_add(request, machine_id):
    """HTMX endpoint to add an engine to a machine."""
    machine = get_object_or_404(Machine, pk=machine_id)
    
    if request.method != 'POST':
        return HttpResponseBadRequest()
    
    engine_id = request.POST.get('engine_id')
    if not engine_id:
        return HttpResponseBadRequest("engine_id is required")
    
    try:
        engine = Engine.objects.get(pk=engine_id)
    except Engine.DoesNotExist:
        return HttpResponseBadRequest("Invalid engine_id")
    
    is_primary = str(request.POST.get('is_primary', 'false')).lower() in ('true', '1', 'yes', 'on')
    notes = request.POST.get('notes', '').strip()
    
    try:
        link, created = MachineEngine.objects.get_or_create(
            machine=machine,
            engine=engine,
            defaults={
                'is_primary': is_primary,
                'notes': notes
            }
        )
        if not created and (link.is_primary != is_primary or link.notes != notes):
            link.is_primary = is_primary
            link.notes = notes
            link.save(update_fields=['is_primary', 'notes'])
    except IntegrityError:
        pass
    
    return machine_engines_partial(request, machine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def machine_engine_remove(request, machine_id, link_id):
    """HTMX endpoint to remove an engine from a machine."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    machine = get_object_or_404(Machine, pk=machine_id)
    link = get_object_or_404(MachineEngine, pk=link_id, machine=machine)
    link.delete()
    
    return machine_engines_partial(request, machine_id)


# Machine-Part relationship views
@login_required
def machine_parts_list(request, machine_id):
    """HTMX endpoint to list parts for a machine."""
    machine = get_object_or_404(Machine, pk=machine_id)
    parts = machine.machinepart_set.select_related('part').all()
    
    context = {
        'machine': machine,
        'parts': parts,
    }
    
    return render(request, 'inventory/partials/machine_parts_list.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def add_machine_part(request, machine_id):
    """HTMX endpoint to add a part to a machine."""
    machine = get_object_or_404(Machine, pk=machine_id)
    part_id = request.POST.get('part')
    notes = request.POST.get('notes', '')
    is_primary = request.POST.get('is_primary') == 'on'
    
    if not part_id:
        return HttpResponse("Part is required", status=400)
    
    try:
        part = Part.objects.get(id=part_id)
    except Part.DoesNotExist:
        return HttpResponse("Part not found", status=400)
    
    # Check if this combination already exists
    if MachinePart.objects.filter(machine=machine, part=part).exists():
        return HttpResponse("This part is already assigned to this machine", status=400)
    
    # Create the relationship
    MachinePart.objects.create(
        machine=machine,
        part=part,
        notes=notes,
        is_primary=is_primary
    )
    
    # Return the updated parts list
    return machine_parts_list(request, machine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def remove_machine_part(request, machine_id, part_id):
    """HTMX endpoint to remove a part from a machine."""
    machine = get_object_or_404(Machine, pk=machine_id)
    
    try:
        machine_part = MachinePart.objects.get(machine=machine, part_id=part_id)
        machine_part.delete()
    except MachinePart.DoesNotExist:
        return HttpResponse("Part not found on this machine", status=404)
    
    # Return the updated parts list
    return machine_parts_list(request, machine_id)


@login_required
def machine_add_part_form(request, machine_id):
    """HTMX endpoint to render the add part form."""
    machine = get_object_or_404(Machine, pk=machine_id)
    parts = Part.objects.all().order_by('part_number')
    
    context = {
        'machine': machine,
        'parts': parts,
    }
    
    return render(request, 'inventory/partials/machine_add_part_form.html', context)


# New stable container Machine-Part relationship views
@login_required
def machine_parts_partial(request, machine_id):
    """HTMX endpoint to render the machine parts partial."""
    machine = get_object_or_404(Machine, pk=machine_id)
    machine_parts = machine.machinepart_set.select_related('part', 'part__category').all()
    
    context = {
        'machine': machine,
        'machine_parts': machine_parts,
    }
    
    return render(request, 'inventory/partials/_machine_parts_partial.html', context)


@login_required
def part_search_modal(request, machine_id):
    """HTMX endpoint to render the part search modal."""
    machine = get_object_or_404(Machine, pk=machine_id)
    
    # Get parts not already associated with this machine
    # Show first 50 by default
    parts = Part.objects.exclude(
        machinepart__machine=machine
    ).select_related('category').order_by('part_number')[:50]
    
    context = {
        'machine': machine,
        'parts': parts,
        'query': '',
    }
    
    return render(request, 'inventory/partials/part_search_modal.html', context)


@login_required
def part_search_results(request, machine_id):
    """HTMX endpoint to return filtered part search results."""
    machine = get_object_or_404(Machine, pk=machine_id)
    query = request.GET.get('q', '').strip()
    
    # Get parts not already associated with this machine
    parts = Part.objects.exclude(
        machinepart__machine=machine
    ).select_related('category')
    
    # Apply search filter
    if query:
        parts = parts.filter(
            Q(part_number__icontains=query) |
            Q(name__icontains=query) |
            Q(manufacturer__icontains=query) |
            Q(type__icontains=query) |
            Q(manufacturer_type__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Limit results to prevent performance issues
    parts = parts.order_by('part_number')[:100]
    
    context = {
        'machine': machine,
        'parts': parts,
        'query': query,
    }
    
    return render(request, 'inventory/partials/part_search_results.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def machine_part_add(request, machine_id):
    """HTMX endpoint to add a part to a machine."""
    machine = get_object_or_404(Machine, pk=machine_id)
    
    part_id = request.POST.get('part_id')
    if not part_id:
        return HttpResponseBadRequest("part_id is required")
    
    try:
        part = Part.objects.get(pk=part_id)
    except Part.DoesNotExist:
        return HttpResponseBadRequest("Invalid part_id")
    
    is_primary = str(request.POST.get('is_primary', 'false')).lower() in ('true', '1', 'yes', 'on')
    notes = request.POST.get('notes', '').strip()
    
    try:
        link, created = MachinePart.objects.get_or_create(
            machine=machine,
            part=part,
            defaults={
                'is_primary': is_primary,
                'notes': notes
            }
        )
        if not created and (link.is_primary != is_primary or link.notes != notes):
            link.is_primary = is_primary
            link.notes = notes
            link.save(update_fields=['is_primary', 'notes'])
    except IntegrityError:
        pass
    
    return machine_parts_partial(request, machine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def machine_part_remove(request, machine_id, link_id):
    """HTMX endpoint to remove a part from a machine."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    machine = get_object_or_404(Machine, pk=machine_id)
    link = get_object_or_404(MachinePart, pk=link_id, machine=machine)
    link.delete()
    
    return machine_parts_partial(request, machine_id)


# New stable container Engine-Machine relationship views
@login_required
def engine_machines_partial(request, engine_id):
    """HTMX endpoint to render the engine machines partial (table only)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    machine_engines = engine.machineengine_set.select_related('machine').all()
    
    context = {
        'engine': engine,
        'machine_engines': machine_engines,
    }
    
    return render(request, 'inventory/partials/_engine_machines_partial.html', context)


@login_required
def machine_search_modal(request, engine_id):
    """HTMX endpoint to render the machine search modal."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Get machines not already associated with this engine
    # Show first 50 by default
    machines = Machine.objects.exclude(
        machineengine__engine=engine
    ).order_by('make', 'model', 'year')[:50]
    
    context = {
        'engine': engine,
        'machines': machines,
        'query': '',
    }
    
    return render(request, 'inventory/partials/machine_search_modal.html', context)


@login_required
def machine_search_results(request, engine_id):
    """HTMX endpoint to return filtered machine search results."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    # Get machines not already associated with this engine
    machines = Machine.objects.exclude(
        machineengine__engine=engine
    )
    
    # Apply search filter
    if query:
        machines = machines.filter(
            Q(make__icontains=query) |
            Q(model__icontains=query) |
            Q(year__icontains=query) |
            Q(machine_type__icontains=query) |
            Q(market_type__icontains=query)
        )
    
    # Limit results to prevent performance issues
    machines = machines.order_by('make', 'model', 'year')[:100]
    
    context = {
        'engine': engine,
        'machines': machines,
        'query': query,
    }
    
    return render(request, 'inventory/partials/machine_search_results.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def engine_machine_add(request, engine_id):
    """HTMX endpoint to add a machine to an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest()
    
    engine = get_object_or_404(Engine, pk=engine_id)
    
    machine_id = request.POST.get('machine_id')
    if not machine_id:
        return HttpResponseBadRequest("machine_id is required")
    
    try:
        machine = Machine.objects.get(pk=machine_id)
    except Machine.DoesNotExist:
        return HttpResponseBadRequest("Invalid machine_id")
    
    is_primary = str(request.POST.get('is_primary', 'false')).lower() in ('true', '1', 'yes', 'on')
    notes = request.POST.get('notes', '').strip()
    
    try:
        link, created = MachineEngine.objects.get_or_create(
            engine=engine,
            machine=machine,
            defaults={
                'is_primary': is_primary,
                'notes': notes
            }
        )
        if not created and (link.is_primary != is_primary or link.notes != notes):
            link.is_primary = is_primary
            link.notes = notes
            link.save(update_fields=['is_primary', 'notes'])
    except IntegrityError:
        pass
    
    return engine_machines_partial(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def engine_machine_remove(request, engine_id, link_id):
    """HTMX endpoint to remove a machine from an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    engine = get_object_or_404(Engine, pk=engine_id)
    link = get_object_or_404(MachineEngine, pk=link_id, engine=engine)
    link.delete()
    
    machine_engines = engine.machineengine_set.select_related('machine').all()
    ctx = {
        "engine": engine,
        "machine_engines": machine_engines,
    }
    return render(request, "inventory/partials/_engine_machines_partial.html", ctx)


# New stable container Engine-Part relationship views
@login_required
def engine_parts_partial(request, engine_id):
    """HTMX endpoint to render the engine parts partial (table only)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    engine_parts = engine.enginepart_set.select_related('part', 'part__category').all()
    
    context = {
        'engine': engine,
        'engine_parts': engine_parts,
    }
    
    return render(request, 'inventory/partials/_engine_parts_partial.html', context)


@login_required
def part_search_modal_for_engine(request, engine_id):
    """HTMX endpoint to render the part search modal for engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Get parts not already associated with this engine
    # Show first 50 by default
    parts = Part.objects.exclude(
        enginepart__engine=engine
    ).select_related('category').order_by('part_number')[:50]
    
    context = {
        'engine': engine,
        'parts': parts,
        'query': '',
    }
    
    return render(request, 'inventory/partials/part_search_modal_for_engine.html', context)


@login_required
def part_search_results_for_engine(request, engine_id):
    """HTMX endpoint to return filtered part search results for engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    # Get parts not already associated with this engine
    parts = Part.objects.exclude(
        enginepart__engine=engine
    ).select_related('category')
    
    # Apply search filter
    if query:
        parts = parts.filter(
            Q(part_number__icontains=query) |
            Q(name__icontains=query) |
            Q(manufacturer__icontains=query) |
            Q(type__icontains=query) |
            Q(manufacturer_type__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Limit results to prevent performance issues
    parts = parts.order_by('part_number')[:100]
    
    context = {
        'engine': engine,
        'parts': parts,
        'query': query,
    }
    
    return render(request, 'inventory/partials/part_search_results_for_engine.html', context)



@login_required
@require_http_methods(["POST"])
@transaction.atomic
def engine_part_add(request, engine_id):
    engine = get_object_or_404(Engine, pk=engine_id)
    
    part_id = request.POST.get("part_id")
    notes = (request.POST.get("notes") or "").strip()

    if not part_id:
        return HttpResponseBadRequest("part_id is required")

    try:
        ep, created = EnginePart.objects.get_or_create(
            engine=engine, part_id=part_id,
            defaults={"notes": notes},
        )
        if not created:
            ep.notes = notes
            ep.save()
    except IntegrityError:
        pass

    return engine_parts_partial(request, engine_id)


@login_required
@require_http_methods(["POST"])
def engine_part_remove(request, engine_id, link_id):
    """HTMX endpoint to remove a part from an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    link = get_object_or_404(EnginePart, pk=link_id, engine=engine)
    link.delete()
    
    engine_parts = engine.enginepart_set.select_related('part', 'part__category').all()
    ctx = {
        "engine": engine,
        "engine_parts": engine_parts,
    }
    return render(request, "inventory/partials/_engine_parts_partial.html", ctx)


# Part-Engine relationship views
@login_required
def part_engines_partial(request, part_id):
    """HTMX endpoint to render the part engines partial."""
    part = get_object_or_404(Part, pk=part_id)
    links = (EnginePart.objects
             .select_related("engine")
             .filter(part=part)
             .order_by("engine__engine_make", "engine__engine_model"))
    
    context = {
        'part': part,
        'links': links,
    }
    
    return render(request, 'inventory/partials/_part_engines_partial.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_engine_add(request, part_id):
    """HTMX endpoint to add an engine to a part."""
    part = get_object_or_404(Part, pk=part_id)
    
    engine_id = request.POST.get('engine_id')
    if not engine_id:
        return HttpResponseBadRequest("engine_id is required")
    
    try:
        engine = Engine.objects.get(pk=engine_id)
        EnginePart.objects.get_or_create(
            part=part,
            engine=engine
        )
    except Engine.DoesNotExist:
        return HttpResponseBadRequest("Invalid engine_id")
    
    return part_engines_partial(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_engine_remove(request, part_id, link_id):
    """HTMX endpoint to remove an engine from a part."""
    part = get_object_or_404(Part, pk=part_id)
    EnginePart.objects.filter(pk=link_id, part=part).delete()
    return part_engines_partial(request, part_id)





# Part-Machine relationship views
@login_required
def part_machines_partial(request, part_id):
    """HTMX endpoint to render the part machines partial."""
    part = get_object_or_404(Part, pk=part_id)
    links = (MachinePart.objects
             .select_related("machine")
             .filter(part=part)
             .order_by("machine__make", "machine__model", "machine__year"))
    
    context = {
        'part': part,
        'links': links,
    }
    
    return render(request, 'inventory/partials/_part_machines_partial.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_machine_add(request, part_id):
    """HTMX endpoint to add a machine to a part."""
    part = get_object_or_404(Part, pk=part_id)
    
    machine_id = request.POST.get('machine_id')
    if not machine_id:
        return HttpResponseBadRequest("machine_id is required")
    
    try:
        machine = Machine.objects.get(pk=machine_id)
        MachinePart.objects.get_or_create(
            part=part,
            machine=machine
        )
    except Machine.DoesNotExist:
        return HttpResponseBadRequest("Invalid machine_id")
    
    return part_machines_partial(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_machine_remove(request, part_id, link_id):
    """HTMX endpoint to remove a machine from a part."""
    part = get_object_or_404(Part, pk=part_id)
    MachinePart.objects.filter(pk=link_id, part=part).delete()
    return part_machines_partial(request, part_id)


@login_required
def part_kits_partial(request, part_id):
    """HTMX endpoint to render the part kits partial (read-only table)."""
    part = get_object_or_404(Part, pk=part_id)
    kit_items = (KitItem.objects
                 .select_related("kit")
                 .filter(part=part)
                 .order_by("kit__name"))
    
    context = {
        'part': part,
        'kit_items': kit_items,
    }
    
    return render(request, 'inventory/partials/_part_kits_partial.html', context)


@login_required
def engine_search_modal_for_part(request, part_id):
    """Renders the engine search modal for adding engines to a part."""
    part = get_object_or_404(Part, pk=part_id)
    # Get already linked engines to exclude them from search
    linked_engine_ids = EnginePart.objects.filter(part=part).values_list('engine_id', flat=True)
    engines = Engine.objects.exclude(id__in=linked_engine_ids)[:20]
    
    context = {
        'part': part,
        'engines': engines,
    }
    return render(request, 'inventory/partials/engine_search_modal_for_part.html', context)


@login_required
def engine_search_results_for_part(request, part_id):
    """Handles the search query for engines to add to a part."""
    part = get_object_or_404(Part, pk=part_id)
    query = request.GET.get('q', '').strip()
    
    # Get already linked engines to exclude them
    linked_engine_ids = EnginePart.objects.filter(part=part).values_list('engine_id', flat=True)
    
    engines = Engine.objects.exclude(id__in=linked_engine_ids)
    
    if query:
        from django.db.models import Q
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(identifier__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query) |
            Q(sg_engine__identifier__icontains=query)
        ).select_related('sg_engine')
    
    engines = engines[:50]  # Limit results
    
    context = {
        'part': part,
        'engines': engines,
    }
    return render(request, 'inventory/partials/engine_search_results_for_part.html', context)


@login_required
def machine_search_modal_for_part(request, part_id):
    """Renders the machine search modal for adding machines to a part."""
    part = get_object_or_404(Part, pk=part_id)
    # Get already linked machines to exclude them from search
    linked_machine_ids = MachinePart.objects.filter(part=part).values_list('machine_id', flat=True)
    machines = Machine.objects.exclude(id__in=linked_machine_ids)[:20]
    
    context = {
        'part': part,
        'machines': machines,
    }
    return render(request, 'inventory/partials/machine_search_modal_for_part.html', context)


@login_required
def machine_search_results_for_part(request, part_id):
    """Handles the search query for machines to add to a part."""
    part = get_object_or_404(Part, pk=part_id)
    query = request.GET.get('q', '').strip()
    
    # Get already linked machines to exclude them
    linked_machine_ids = MachinePart.objects.filter(part=part).values_list('machine_id', flat=True)
    
    machines = Machine.objects.exclude(id__in=linked_machine_ids)
    
    if query:
        from django.db.models import Q
        q_filters = (
            Q(make__icontains=query) |
            Q(model__icontains=query) |
            Q(machine_type__icontains=query) |
            Q(market_type__icontains=query)
        )
        # Try to search year as integer if query is numeric
        if query.isdigit():
            q_filters |= Q(year=int(query))
        machines = machines.filter(q_filters)
    
    machines = machines[:50]  # Limit results
    
    context = {
        'part': part,
        'machines': machines,
    }
    return render(request, 'inventory/partials/machine_search_results_for_part.html', context)




# Engine-Engine relationship views
@login_required
def engine_interchanges_list(request, engine_id):
    """HTMX endpoint to list interchanges for an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    interchanges = engine.interchanges.all()
    
    context = {
        'engine': engine,
        'interchanges': interchanges,
    }
    
    return render(request, 'inventory/partials/engine_interchanges_list.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def add_engine_interchange(request, engine_id):
    """HTMX endpoint to add an interchange to an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    interchange_id = request.POST.get('interchange')
    
    if not interchange_id:
        return HttpResponse("Interchange engine is required", status=400)
    
    try:
        interchange = Engine.objects.get(id=interchange_id)
    except Engine.DoesNotExist:
        return HttpResponse("Engine not found", status=400)
    
    if engine == interchange:
        return HttpResponse("Cannot add self as interchange", status=400)
    
    # Add the interchange (symmetrical relationship)
    engine.interchanges.add(interchange)
    
    # Return the updated interchanges list
    return engine_interchanges_list(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def remove_engine_interchange(request, engine_id, interchange_id):
    """HTMX endpoint to remove an interchange from an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    try:
        interchange = Engine.objects.get(id=interchange_id)
        engine.interchanges.remove(interchange)
    except Engine.DoesNotExist:
        return HttpResponse("Engine not found", status=404)
    
    # Return the updated interchanges list
    return engine_interchanges_list(request, engine_id)


@login_required
def engine_add_interchange_form(request, engine_id):
    """HTMX endpoint to render the add interchange form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    engines = Engine.objects.exclude(id=engine_id).order_by('engine_make', 'engine_model')
    
    context = {
        'engine': engine,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_add_interchange_form.html', context)


@login_required
def engine_compatibles_list(request, engine_id):
    """HTMX endpoint to list compatibles for an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    compatibles = engine.compatibles.all()
    
    context = {
        'engine': engine,
        'compatibles': compatibles,
    }
    
    return render(request, 'inventory/partials/engine_compatibles_list.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def add_engine_compatible(request, engine_id):
    """HTMX endpoint to add a compatible to an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    compatible_id = request.POST.get('compatible')
    
    if not compatible_id:
        return HttpResponse("Compatible engine is required", status=400)
    
    try:
        compatible = Engine.objects.get(id=compatible_id)
    except Engine.DoesNotExist:
        return HttpResponse("Engine not found", status=400)
    
    if engine == compatible:
        return HttpResponse("Cannot add self as compatible", status=400)
    
    # Add the compatible (symmetrical relationship)
    engine.compatibles.add(compatible)
    
    # Return the updated compatibles list
    return engine_compatibles_list(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def remove_engine_compatible(request, engine_id, compatible_id):
    """HTMX endpoint to remove a compatible from an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    try:
        compatible = Engine.objects.get(id=compatible_id)
        engine.compatibles.remove(compatible)
    except Engine.DoesNotExist:
        return HttpResponse("Engine not found", status=404)
    
    # Return the updated compatibles list
    return engine_compatibles_list(request, engine_id)


@login_required
def engine_add_compatible_form(request, engine_id):
    """HTMX endpoint to render the add compatible form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    engines = Engine.objects.exclude(id=engine_id).order_by('engine_make', 'engine_model')
    
    context = {
        'engine': engine,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_add_compatible_form.html', context)


@login_required
def engine_supercession_list(request, engine_id):
    """HTMX endpoint to list supercessions for an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    supersedes = engine.supersedes
    superseded_by = engine.superseded_by
    
    context = {
        'engine': engine,
        'supersedes': supersedes,
        'superseded_by': superseded_by,
    }
    
    return render(request, 'inventory/partials/engine_supercession_list.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def add_engine_supercession_from(request, engine_id):
    """HTMX endpoint to add an engine that this engine supersedes (older predecessor)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    older_engine_id = request.POST.get('older_engine')
    notes = request.POST.get('notes', '')
    effective_date = request.POST.get('effective_date', '')
    
    if not older_engine_id:
        return HttpResponse("Older engine is required", status=400)
    
    try:
        older_engine = Engine.objects.get(id=older_engine_id)
    except Engine.DoesNotExist:
        return HttpResponse("Engine not found", status=400)
    
    if engine == older_engine:
        return HttpResponse("Cannot supersede self", status=400)
    
    # Check if this supercession already exists
    if EngineSupercession.objects.filter(from_engine=older_engine, to_engine=engine).exists():
        return HttpResponse("This supercession already exists", status=400)
    
    # Create the supercession (older_engine → engine)
    supercession = EngineSupercession.objects.create(
        from_engine=older_engine,
        to_engine=engine,
        notes=notes,
        effective_date=effective_date if effective_date else None
    )
    
    # Return the updated supercession list
    return engine_supercession_list(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def add_engine_supercession_to(request, engine_id):
    """HTMX endpoint to add an engine that supersedes this one (newer replacement)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    newer_engine_id = request.POST.get('newer_engine')
    notes = request.POST.get('notes', '')
    effective_date = request.POST.get('effective_date', '')
    
    if not newer_engine_id:
        return HttpResponse("Newer engine is required", status=400)
    
    try:
        newer_engine = Engine.objects.get(id=newer_engine_id)
    except Engine.DoesNotExist:
        return HttpResponse("Engine not found", status=400)
    
    if engine == newer_engine:
        return HttpResponse("Cannot be superseded by self", status=400)
    
    # Check if this supercession already exists
    if EngineSupercession.objects.filter(from_engine=engine, to_engine=newer_engine).exists():
        return HttpResponse("This supercession already exists", status=400)
    
    # Create the supercession (engine → newer_engine)
    supercession = EngineSupercession.objects.create(
        from_engine=engine,
        to_engine=newer_engine,
        notes=notes,
        effective_date=effective_date if effective_date else None
    )
    
    # Return the updated supercession list
    return engine_supercession_list(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def remove_engine_supercession(request, engine_id, supercession_id):
    """HTMX endpoint to remove a supercession."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    try:
        supercession = EngineSupercession.objects.get(id=supercession_id)
        # Check if this supercession involves the current engine
        if supercession.from_engine != engine and supercession.to_engine != engine:
            return HttpResponse("Supercession not found for this engine", status=404)
        supercession.delete()
    except EngineSupercession.DoesNotExist:
        return HttpResponse("Supercession not found", status=404)
    
    # Return the updated supercession list
    return engine_supercession_list(request, engine_id)


@login_required
def engine_add_supercession_from_form(request, engine_id):
    """HTMX endpoint to render the add supercession from form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    engines = Engine.objects.exclude(id=engine_id).order_by('engine_make', 'engine_model')
    
    context = {
        'engine': engine,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_add_supercession_from_form.html', context)


@login_required
def engine_add_supercession_to_form(request, engine_id):
    """HTMX endpoint to render the add supercession to form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    engines = Engine.objects.exclude(id=engine_id).order_by('engine_make', 'engine_model')
    
    context = {
        'engine': engine,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_add_supercession_to_form.html', context)


# SG Engine Catalog Views
@login_required
def sg_engines_list(request):
    """SG Engines catalog page with filtering, sorting, and pagination."""
    sg_engines = SGEngine.objects.all()
    
    # Apply filters
    sg_make_filter = request.GET.get('sg_make', '').strip()
    sg_model_filter = request.GET.get('sg_model', '').strip()
    
    if sg_make_filter:
        sg_engines = sg_engines.filter(sg_make__icontains=sg_make_filter)
    if sg_model_filter:
        sg_engines = sg_engines.filter(sg_model__icontains=sg_model_filter)
    
    # Apply sorting
    sort_by = request.GET.get('sort', 'sg_make')
    sort_order = request.GET.get('order', 'asc')
    
    valid_sort_fields = ['sg_make', 'sg_model', 'created_at']
    if sort_by in valid_sort_fields:
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        sg_engines = sg_engines.order_by(sort_by)
    else:
        sg_engines = sg_engines.order_by('sg_make', 'sg_model')
    
    # Pagination
    paginator = Paginator(sg_engines, 200)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter choices for dropdowns
    all_sg_engines = SGEngine.objects.all()
    sg_makes = all_sg_engines.values_list('sg_make', flat=True).distinct().order_by('sg_make')
    sg_models = all_sg_engines.values_list('sg_model', flat=True).distinct().order_by('sg_model')
    
    context = {
        'page_obj': page_obj,
        'sg_engines': page_obj.object_list,
        'total_count': paginator.count,
        'sg_makes': sg_makes,
        'sg_models': sg_models,
        'current_filters': {
            'sg_make': sg_make_filter,
            'sg_model': sg_model_filter,
        },
        'current_sort': sort_by.lstrip('-'),
        'current_order': sort_order,
    }
    
    return render(request, 'inventory/sg_engines_list.html', context)


@login_required
def sg_engine_create(request):
    """Create a new SG Engine."""
    if request.method == 'POST':
        form = SGEngineForm(request.POST)
        if form.is_valid():
            sg_engine = form.save(commit=False)
            sg_engine.created_by = request.user if request.user.is_authenticated else None
            sg_engine.save()
            messages.success(request, f'SG Engine "{sg_engine.sg_make} {sg_engine.sg_model}" created successfully.')
            return redirect('inventory:sg_engine_detail', pk=sg_engine.pk)
    else:
        form = SGEngineForm()
    
    context = {
        'form': form,
        'title': 'Create SG Engine',
        'submit_text': 'Create SG Engine',
    }
    
    return render(request, 'inventory/sg_engine_form.html', context)


@login_required
def sg_engine_detail(request, pk):
    """SG Engine detail page."""
    sg_engine = get_object_or_404(SGEngine, pk=pk)
    
    # Get engines that use this SG Engine
    engines = Engine.objects.filter(sg_engine=sg_engine)
    
    context = {
        'sg_engine': sg_engine,
        'engines': engines,
    }
    
    return render(request, 'inventory/sg_engine_detail.html', context)


@login_required
def sg_engine_edit(request, pk):
    """Edit an SG Engine."""
    sg_engine = get_object_or_404(SGEngine, pk=pk)
    
    if request.method == 'POST':
        form = SGEngineForm(request.POST, instance=sg_engine)
        if form.is_valid():
            sg_engine = form.save(commit=False)
            sg_engine.updated_by = request.user if request.user.is_authenticated else None
            sg_engine.save()
            messages.success(request, f'SG Engine "{sg_engine.sg_make} {sg_engine.sg_model}" updated successfully.')
            return redirect('inventory:sg_engine_detail', pk=sg_engine.pk)
    else:
        form = SGEngineForm(instance=sg_engine)
    
    context = {
        'form': form,
        'sg_engine': sg_engine,
        'title': f'Edit SG Engine: {sg_engine.sg_make} {sg_engine.sg_model}',
        'submit_text': 'Update SG Engine',
    }
    
    return render(request, 'inventory/sg_engine_form.html', context)


@login_required
def sg_engine_delete(request, pk):
    """Delete an SG Engine."""
    sg_engine = get_object_or_404(SGEngine, pk=pk)
    
    if request.method == 'POST':
        sg_make = sg_engine.sg_make
        sg_model = sg_engine.sg_model
        sg_engine.delete()
        messages.success(request, f'SG Engine "{sg_make} {sg_model}" deleted successfully.')
        return redirect('inventory:sg_engines_list')
    
    # Get engines that use this SG Engine
    engines = Engine.objects.filter(sg_engine=sg_engine)
    
    context = {
        'sg_engine': sg_engine,
        'engines': engines,
    }
    
    return render(request, 'inventory/sg_engine_confirm_delete.html', context)


@login_required
def sg_engine_quick_create(request):
    """Quick create modal for SG Engine from Engine detail page."""
    if request.method == 'POST':
        form = SGEngineForm(request.POST)
        if form.is_valid():
            sg_engine = form.save(commit=False)
            sg_engine.created_by = request.user if request.user.is_authenticated else None
            sg_engine.save()
            
            # Check if we need to update an engine's sg_engine field
            engine_id = request.POST.get('engine_id')
            if engine_id:
                try:
                    engine = Engine.objects.get(pk=engine_id)
                    engine.sg_engine = sg_engine
                    engine.updated_by = request.user if request.user.is_authenticated else None
                    engine.save()
                except Engine.DoesNotExist:
                    pass
            
            # Return JSON response for HTMX
            return JsonResponse({
                'success': True,
                'sg_engine_id': sg_engine.pk,
                'sg_engine_name': f'{sg_engine.sg_make} {sg_engine.sg_model}',
                'message': f'SG Engine "{sg_engine.sg_make} {sg_engine.sg_model}" created successfully and assigned to engine.',
                'engine_updated': bool(engine_id)
            })
        else:
            # Return form errors
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = SGEngineForm()
        engine_id = request.GET.get('engine_id')
    
    context = {
        'form': form,
        'modal_title': 'Quick Create SG Engine',
        'engine_id': engine_id,
    }
    
    return render(request, 'inventory/partials/sg_engine_quick_create_modal.html', context)


def export_machines_csv(machines_queryset, request):
    """Export machines to CSV with current filters applied."""
    # Apply the same filters that were used in the list view
    make_filter = request.GET.get('make', '').strip()
    model_filter = request.GET.get('model', '').strip()
    year_filter = request.GET.get('year', '').strip()
    machine_type_filter = request.GET.get('machine_type', '').strip()
    market_type_filter = request.GET.get('market_type', '').strip()

    machines = Machine.objects.all()

    if make_filter:
        machines = machines.filter(make__icontains=make_filter)
    if model_filter:
        machines = machines.filter(model__icontains=model_filter)
    if year_filter:
        try:
            year_value = int(year_filter)
            machines = machines.filter(year=year_value)
        except ValueError:
            pass
    if machine_type_filter:
        machines = machines.filter(machine_type__icontains=machine_type_filter)
    if market_type_filter:
        machines = machines.filter(market_type__icontains=market_type_filter)

    # Apply sorting
    sort_by = request.GET.get('sort', 'year')
    sort_order = request.GET.get('order', 'desc')

    valid_sort_fields = ['make', 'model', 'year', 'machine_type', 'market_type', 'created_at']
    if sort_by in valid_sort_fields:
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        machines = machines.order_by(sort_by)
    else:
        machines = machines.order_by('-year')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="machines_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Make', 'Model', 'Year', 'Machine Type', 'Market Type', 'Created At', 'Updated At'])

    for machine in machines:
        writer.writerow([
            machine.id,
            machine.make,
            machine.model,
            machine.year,
            machine.machine_type,
            machine.market_type,
            machine.created_at.strftime('%Y-%m-%d %H:%M:%S') if machine.created_at else '',
            machine.updated_at.strftime('%Y-%m-%d %H:%M:%S') if machine.updated_at else '',
        ])

    return response


def export_engines_csv(engines_queryset, request):
    """Export engines to CSV with current filters applied."""
    # Apply the same filters that were used in the list view
    engine_make_filter = request.GET.get('engine_make', '').strip()
    engine_model_filter = request.GET.get('engine_model', '').strip()
    sg_make_filter = request.GET.get('sg_make', '').strip()
    sg_model_filter = request.GET.get('sg_model', '').strip()
    status_filter = request.GET.get('status', '').strip()
    keyword_search = request.GET.get('search', '').strip()

    engines = Engine.objects.select_related('sg_engine').all()

    if engine_make_filter:
        engines = engines.filter(engine_make__icontains=engine_make_filter)
    if engine_model_filter:
        engines = engines.filter(engine_model__icontains=engine_model_filter)
    if sg_make_filter:
        engines = engines.filter(sg_engine__sg_make__icontains=sg_make_filter)
    if sg_model_filter:
        engines = engines.filter(sg_engine__sg_model__icontains=sg_model_filter)
    if status_filter:
        engines = engines.filter(status__icontains=status_filter)
    
    if keyword_search:
        engines = engines.filter(
            Q(engine_make__icontains=keyword_search) |
            Q(engine_model__icontains=keyword_search) |
            Q(sg_engine__sg_make__icontains=keyword_search) |
            Q(sg_engine__sg_model__icontains=keyword_search) |
            Q(cpl_number__icontains=keyword_search) |
            Q(ar_number__icontains=keyword_search) |
            Q(build_list__icontains=keyword_search) |
            Q(engine_code__icontains=keyword_search) |
            Q(status__icontains=keyword_search)
        )

    # Apply sorting
    sort_by = request.GET.get('sort', 'engine_make')
    sort_order = request.GET.get('order', 'asc')

    valid_sort_fields = ['engine_make', 'engine_model', 'sg_engine__sg_make', 'sg_engine__sg_model', 'status', 'price', 'created_at']
    if sort_by in valid_sort_fields:
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        engines = engines.order_by(sort_by)
    else:
        engines = engines.order_by('engine_make', 'engine_model')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="engines_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Engine Make', 'Engine Model', 'SG Make', 'SG Model', 'SG Identifier', 'SG Notes', 'CPL Number', 
        'AR Number', 'Build List', 'Engine Code', 'Status', 'Price', 'Created At', 'Updated At'
    ])

    for engine in engines:
        writer.writerow([
            engine.id,
            engine.engine_make,
            engine.engine_model,
            engine.sg_engine.sg_make if engine.sg_engine else '',
            engine.sg_engine.sg_model if engine.sg_engine else '',
            engine.sg_engine.identifier if engine.sg_engine else '',
            engine.sg_engine.notes if engine.sg_engine else '',
            engine.cpl_number or '',
            engine.ar_number or '',
            engine.build_list or '',
            engine.engine_code or '',
            engine.status or '',
            engine.price or '',
            engine.created_at.strftime('%Y-%m-%d %H:%M:%S') if engine.created_at else '',
            engine.updated_at.strftime('%Y-%m-%d %H:%M:%S') if engine.updated_at else '',
        ])

    return response


def export_parts_csv(parts_queryset, request):
    """Export parts to CSV with current filters applied."""
    # Apply the same filters that were used in the list view
    part_number_filter = request.GET.get('part_number', '').strip()
    name_filter = request.GET.get('name', '').strip()
    manufacturer_filter = request.GET.get('manufacturer', '').strip()
    category_filter = request.GET.get('category', '').strip()

    parts = Part.objects.select_related('primary_vendor').all()

    if part_number_filter:
        parts = parts.filter(part_number__icontains=part_number_filter)
    if name_filter:
        parts = parts.filter(name__icontains=name_filter)
    if manufacturer_filter:
        parts = parts.filter(manufacturer__icontains=manufacturer_filter)
    if category_filter:
        parts = parts.filter(category__icontains=category_filter)

    # Apply sorting
    sort_by = request.GET.get('sort', 'part_number')
    sort_order = request.GET.get('order', 'asc')

    valid_sort_fields = ['part_number', 'name', 'manufacturer', 'category', 'type', 'created_at']
    if sort_by in valid_sort_fields:
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        parts = parts.order_by(sort_by)
    else:
        parts = parts.order_by('part_number')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="parts_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Part Number', 'Name', 'Category', 'Manufacturer', 'Unit', 'Type', 
        'Manufacturer Type', 'Primary Vendor', 'Created At', 'Updated At'
    ])

    for part in parts:
        writer.writerow([
            part.id,
            part.part_number,
            part.name,
            part.category or '',
            part.manufacturer or '',
            part.unit or '',
            part.type or '',
            part.manufacturer_type or '',
            part.primary_vendor.name if part.primary_vendor else '',
            part.created_at.strftime('%Y-%m-%d %H:%M:%S') if part.created_at else '',
            part.updated_at.strftime('%Y-%m-%d %H:%M:%S') if part.updated_at else '',
        ])

    return response


def export_sg_engines_csv(sg_engines_queryset, request):
    """Export SG engines to CSV with current filters applied."""
    # Apply the same filters that were used in the list view
    sg_make_filter = request.GET.get('sg_make', '').strip()
    sg_model_filter = request.GET.get('sg_model', '').strip()
    identifier_filter = request.GET.get('identifier', '').strip()
    keyword_search = request.GET.get('search', '').strip()

    sg_engines = SGEngine.objects.all()

    if sg_make_filter:
        sg_engines = sg_engines.filter(sg_make__icontains=sg_make_filter)
    if sg_model_filter:
        sg_engines = sg_engines.filter(sg_model__icontains=sg_model_filter)
    if identifier_filter:
        sg_engines = sg_engines.filter(identifier__icontains=identifier_filter)
    
    # Global keyword search
    if keyword_search:
        sg_engines = sg_engines.filter(
            Q(sg_make__icontains=keyword_search) |
            Q(sg_model__icontains=keyword_search) |
            Q(identifier__icontains=keyword_search) |
            Q(notes__icontains=keyword_search)
        )

    # Apply sorting
    sort_by = request.GET.get('sort', 'sg_make')
    sort_order = request.GET.get('order', 'asc')

    valid_sort_fields = ['sg_make', 'sg_model', 'identifier', 'created_at']
    if sort_by in valid_sort_fields:
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        sg_engines = sg_engines.order_by(sort_by)
    else:
        sg_engines = sg_engines.order_by('sg_make', 'sg_model')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sg_engines_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'SG Engine Make', 'SG Engine Model', 'SG Engine Identifier', 'SG Engine Notes', 
        'Created At', 'Updated At'
    ])

    for sg_engine in sg_engines:
        writer.writerow([
            sg_engine.id,
            sg_engine.sg_make,
            sg_engine.sg_model,
            sg_engine.identifier,
            sg_engine.notes or '',
            sg_engine.created_at.strftime('%Y-%m-%d %H:%M:%S') if sg_engine.created_at else '',
            sg_engine.updated_at.strftime('%Y-%m-%d %H:%M:%S') if sg_engine.updated_at else '',
        ])

    return response


@login_required
def part_specs_table(request, part_id):
    """HTMX endpoint to render the specifications table for a part."""
    part = get_object_or_404(Part, pk=part_id)
    
    # Get all categories for the dropdown
    categories = PartCategory.objects.all().order_by('name')
    
    # Get current attribute values with related data
    attribute_values = part.attribute_values.select_related('attribute', 'choice').all()
    
    # Get available attributes for the "Add row" dropdown (excluding already used ones)
    available_attributes = []
    if part.category:
        used_attribute_ids = set(av.attribute_id for av in attribute_values)
        available_attributes = part.category.attributes.exclude(id__in=used_attribute_ids).order_by('sort_order', 'name')
    
    context = {
        'part': part,
        'categories': categories,
        'attribute_values': attribute_values,
        'available_attributes': available_attributes,
    }
    
    return render(request, 'inventory/partials/_part_specs_table.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_specs_add(request, part_id):
    """HTMX endpoint to add a new specification row."""
    part = get_object_or_404(Part, pk=part_id)
    
    attribute_id = request.POST.get('attribute_id')
    value = request.POST.get('value', '').strip()
    
    if not attribute_id:
        return HttpResponse("Attribute is required", status=400)
    
    try:
        attribute = PartAttribute.objects.get(id=attribute_id, category=part.category)
    except PartAttribute.DoesNotExist:
        return HttpResponse("Invalid attribute", status=400)
    
    # Check if this attribute is already used for this part
    if PartAttributeValue.objects.filter(part=part, attribute=attribute).exists():
        return HttpResponse("This specification already exists", status=400)
    
    # Create the attribute value
    attr_value = PartAttributeValue.objects.create(
        part=part,
        attribute=attribute,
        value_text='',
        value_int=None,
        value_dec=None,
        value_bool=None,
        value_date=None,
        choice=None,
    )
    
    # Set the appropriate value field based on data type
    if attribute.data_type == PartAttribute.DataType.TEXT:
        attr_value.value_text = value
    elif attribute.data_type == PartAttribute.DataType.INTEGER:
        if value:
            try:
                attr_value.value_int = int(value)
            except ValueError:
                return HttpResponse("Invalid integer value", status=400)
    elif attribute.data_type == PartAttribute.DataType.DECIMAL:
        if value:
            try:
                attr_value.value_dec = float(value)
            except ValueError:
                return HttpResponse("Invalid decimal value", status=400)
    elif attribute.data_type == PartAttribute.DataType.BOOLEAN:
        attr_value.value_bool = value.lower() in ('true', '1', 'yes', 'on')
    elif attribute.data_type == PartAttribute.DataType.DATE:
        if value:
            try:
                attr_value.value_date = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return HttpResponse("Invalid date value", status=400)
    elif attribute.data_type == PartAttribute.DataType.CHOICE:
        if value:
            try:
                choice = PartAttributeChoice.objects.get(attribute=attribute, value=value)
                attr_value.choice = choice
            except PartAttributeChoice.DoesNotExist:
                return HttpResponse("Invalid choice value", status=400)
    
    attr_value.save()
    
    # Re-render the specs table
    return part_specs_table(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_specs_edit(request, part_id, pav_id):
    """HTMX endpoint to edit an existing specification value."""
    part = get_object_or_404(Part, pk=part_id)
    
    try:
        attr_value = PartAttributeValue.objects.get(id=pav_id, part=part)
    except PartAttributeValue.DoesNotExist:
        return HttpResponse("Specification not found", status=404)
    
    value = request.POST.get('value', '').strip()
    attribute = attr_value.attribute
    
    # Clear all value fields first
    attr_value.value_text = ''
    attr_value.value_int = None
    attr_value.value_dec = None
    attr_value.value_bool = None
    attr_value.value_date = None
    attr_value.choice = None
    
    # Set the appropriate value field based on data type
    if attribute.data_type == PartAttribute.DataType.TEXT:
        attr_value.value_text = value
    elif attribute.data_type == PartAttribute.DataType.INTEGER:
        if value:
            try:
                attr_value.value_int = int(value)
            except ValueError:
                return HttpResponse("Invalid integer value", status=400)
    elif attribute.data_type == PartAttribute.DataType.DECIMAL:
        if value:
            try:
                attr_value.value_dec = float(value)
            except ValueError:
                return HttpResponse("Invalid decimal value", status=400)
    elif attribute.data_type == PartAttribute.DataType.BOOLEAN:
        attr_value.value_bool = value.lower() in ('true', '1', 'yes', 'on')
    elif attribute.data_type == PartAttribute.DataType.DATE:
        if value:
            try:
                attr_value.value_date = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return HttpResponse("Invalid date value", status=400)
    elif attribute.data_type == PartAttribute.DataType.CHOICE:
        if value:
            try:
                choice = PartAttributeChoice.objects.get(attribute=attribute, value=value)
                attr_value.choice = choice
            except PartAttributeChoice.DoesNotExist:
                return HttpResponse("Invalid choice value", status=400)
    
    attr_value.save()
    
    # Re-render the specs table
    return part_specs_table(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_specs_remove(request, part_id, pav_id):
    """HTMX endpoint to remove a specification row."""
    part = get_object_or_404(Part, pk=part_id)
    
    try:
        attr_value = PartAttributeValue.objects.get(id=pav_id, part=part)
    except PartAttributeValue.DoesNotExist:
        return HttpResponse("Specification not found", status=404)
    
    # Check if the attribute is required
    if attr_value.attribute.is_required:
        return HttpResponse("Cannot remove required specification", status=400)
    
    attr_value.delete()
    
    # Re-render the specs table
    return part_specs_table(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_category_change(request, part_id):
    """HTMX endpoint to handle category change and reconcile specifications."""
    part = get_object_or_404(Part, pk=part_id)
    
    category_id = request.POST.get('category_id')
    reconciliation_option = request.POST.get('reconciliation_option', 'clear')  # 'keep_matching' or 'clear'
    
    if not category_id:
        return HttpResponse("Category is required", status=400)
    
    try:
        new_category = PartCategory.objects.get(id=category_id)
    except PartCategory.DoesNotExist:
        return HttpResponse("Invalid category", status=400)
    
    # Get current attribute values
    current_values = {}
    for attr_value in part.attribute_values.select_related('attribute').all():
        current_values[attr_value.attribute.code] = attr_value
    
    # Update the part's category
    part.category = new_category
    part.save()
    
    # Handle reconciliation based on option
    if reconciliation_option == 'keep_matching':
        # Keep values for attributes whose code exists in the new category
        new_attributes = {attr.code: attr for attr in new_category.attributes.all()}
        
        for code, attr_value in current_values.items():
            if code in new_attributes:
                # Update the attribute reference to the new category's attribute
                new_attr = new_attributes[code]
                attr_value.attribute = new_attr
                attr_value.save()
            else:
                # Remove values for attributes that don't exist in new category
                attr_value.delete()
    else:
        # Clear all specifications
        part.attribute_values.all().delete()
    
    # Re-render the specs table
    return part_specs_table(request, part_id)


@login_required
def part_specs_value_input(request, part_id):
    """HTMX endpoint to render the appropriate value input for an attribute."""
    attribute_id = request.GET.get('attribute_id')
    current_value = request.GET.get('current_value', '')
    
    if not attribute_id:
        return HttpResponse("Attribute is required", status=400)
    
    try:
        # For edit mode, the attribute_id might be a PartAttributeValue ID
        # For add mode, it's a PartAttribute ID
        if attribute_id.isdigit():
            # Try to get the attribute from a PartAttributeValue first (edit mode)
            try:
                attr_value = PartAttributeValue.objects.select_related('attribute').get(id=attribute_id)
                attribute = attr_value.attribute
            except PartAttributeValue.DoesNotExist:
                # Fall back to direct PartAttribute lookup (add mode)
                attribute = PartAttribute.objects.prefetch_related('choices').get(id=attribute_id)
        else:
            attribute = PartAttribute.objects.prefetch_related('choices').get(id=attribute_id)
    except PartAttribute.DoesNotExist:
        return HttpResponse("Attribute not found", status=404)
    
    context = {
        'attribute': attribute,
        'current_value': current_value,
    }
    
    return render(request, 'inventory/partials/_part_specs_value_input.html', context)


# OLD part_edit function removed - replaced with new app-native edit functionality


@login_required
def part_specs_read(request, part_id):
    """HTMX endpoint to render read-only specifications."""
    part = get_object_or_404(Part, pk=part_id)
    
    # Get current attribute values with related data
    attribute_values = part.attribute_values.select_related('attribute', 'choice').all()
    
    context = {
        'part': part,
        'attribute_values': attribute_values,
    }
    
    return render(request, 'inventory/partials/_part_specs_read.html', context)


@login_required
def part_specs_edit_form(request, part_id):
    """HTMX endpoint to render edit form for specifications."""
    part = get_object_or_404(Part, pk=part_id)
    
    # Get all categories for the dropdown
    categories = PartCategory.objects.all().order_by('name')
    
    # Get current attribute values with related data
    attribute_values = part.attribute_values.select_related('attribute', 'choice').all()
    
    # Get all attributes for the part's category
    attributes = []
    if part.category:
        attributes = part.category.attributes.prefetch_related('choices').all()
    
    context = {
        'part': part,
        'categories': categories,
        'attribute_values': attribute_values,
        'attributes': attributes,
    }
    
    return render(request, 'inventory/partials/_part_specs_edit.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_specs_save_all(request, part_id):
    """HTMX endpoint to save all part specifications."""
    part = get_object_or_404(Part, pk=part_id)
    
    if not part.category:
        return HttpResponse("No category selected", status=400)
    
    # Get all attributes for this category
    attributes = part.category.attributes.all()
    
    for attribute in attributes:
        field_name = f"attr_{attribute.id}"
        value = request.POST.get(field_name, '').strip()
        
        # Get or create the attribute value
        attr_value, created = PartAttributeValue.objects.get_or_create(
            part=part,
            attribute=attribute,
            defaults={
                'value_text': '',
                'value_int': None,
                'value_dec': None,
                'value_bool': None,
                'value_date': None,
                'choice': None,
            }
        )
        
        # Clear all value fields first
        attr_value.value_text = ''
        attr_value.value_int = None
        attr_value.value_dec = None
        attr_value.value_bool = None
        attr_value.value_date = None
        attr_value.choice = None
        
        # Set the appropriate value field based on data type
        if attribute.data_type == PartAttribute.DataType.TEXT:
            attr_value.value_text = value
        elif attribute.data_type == PartAttribute.DataType.INTEGER:
            if value:
                try:
                    attr_value.value_int = int(value)
                except ValueError:
                    return HttpResponse(f"Invalid integer value for {attribute.name}", status=400)
        elif attribute.data_type == PartAttribute.DataType.DECIMAL:
            if value:
                try:
                    attr_value.value_dec = float(value)
                except ValueError:
                    return HttpResponse(f"Invalid decimal value for {attribute.name}", status=400)
        elif attribute.data_type == PartAttribute.DataType.BOOLEAN:
            attr_value.value_bool = value.lower() in ('true', '1', 'yes', 'on')
        elif attribute.data_type == PartAttribute.DataType.DATE:
            if value:
                try:
                    attr_value.value_date = datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    return HttpResponse(f"Invalid date value for {attribute.name}", status=400)
        elif attribute.data_type == PartAttribute.DataType.CHOICE:
            if value:
                try:
                    choice = PartAttributeChoice.objects.get(attribute=attribute, value=value)
                    attr_value.choice = choice
                except PartAttributeChoice.DoesNotExist:
                    return HttpResponse(f"Invalid choice value for {attribute.name}", status=400)
        
        # Check required validation
        if attribute.is_required:
            has_value = False
            if attribute.data_type == PartAttribute.DataType.TEXT and attr_value.value_text:
                has_value = True
            elif attribute.data_type == PartAttribute.DataType.INTEGER and attr_value.value_int is not None:
                has_value = True
            elif attribute.data_type == PartAttribute.DataType.DECIMAL and attr_value.value_dec is not None:
                has_value = True
            elif attribute.data_type == PartAttribute.DataType.BOOLEAN and attr_value.value_bool is not None:
                has_value = True
            elif attribute.data_type == PartAttribute.DataType.DATE and attr_value.value_date:
                has_value = True
            elif attribute.data_type == PartAttribute.DataType.CHOICE and attr_value.choice:
                has_value = True
            
            if not has_value:
                return HttpResponse(f"{attribute.name} is required", status=400)
        
        attr_value.save()
    
    # Return the updated read partial
    return part_specs_read(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_category_confirm_change(request, part_id):
    """HTMX endpoint to show category change confirmation modal."""
    part = get_object_or_404(Part, pk=part_id)
    
    category_id = request.POST.get('category_id')
    reconciliation_option = request.POST.get('reconciliation_option', 'clear')
    
    if not category_id:
        return HttpResponse("Category is required", status=400)
    
    try:
        new_category = PartCategory.objects.get(id=category_id)
    except PartCategory.DoesNotExist:
        return HttpResponse("Invalid category", status=400)
    
    # Get current attribute values
    current_values = {}
    for attr_value in part.attribute_values.select_related('attribute').all():
        current_values[attr_value.attribute.code] = attr_value
    
    # Update the part's category
    part.category = new_category
    part.save()
    
    # Handle reconciliation based on option
    if reconciliation_option == 'keep_matching':
        # Keep values for attributes whose code exists in the new category
        new_attributes = {attr.code: attr for attr in new_category.attributes.all()}
        
        for code, attr_value in current_values.items():
            if code in new_attributes:
                # Update the attribute reference to the new category's attribute
                new_attr = new_attributes[code]
                attr_value.attribute = new_attr
                attr_value.save()
            else:
                # Remove values for attributes that don't exist in new category
                attr_value.delete()
    else:
        # Clear all specifications
        part.attribute_values.all().delete()
    
    # Return the updated edit form
    return part_specs_edit_form(request, part_id)


# Settings Views
@login_required
def part_categories_list(request):
    """List all part categories."""
    categories = PartCategory.objects.annotate(
        field_count=Count('attributes')
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'inventory/settings/part_categories_list.html', context)


@login_required
def part_category_create(request):
    """Create a new part category."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        
        if not name:
            return HttpResponse("Name is required", status=400)
        
        if not slug:
            from django.utils.text import slugify
            slug = slugify(name)
        
        # Ensure slug is unique
        base_slug = slug
        counter = 1
        while PartCategory.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        category = PartCategory.objects.create(name=name, slug=slug)
        
        return redirect('inventory:part_category_detail', category_id=category.id)
    
    return render(request, 'inventory/settings/part_category_form.html', {'category': None})


@login_required
def part_category_detail(request, category_id):
    """Detail view for a part category with field management."""
    category = get_object_or_404(PartCategory, pk=category_id)
    
    # Get attributes with choice counts
    attributes = category.attributes.prefetch_related('choices').all().order_by('sort_order', 'name')
    
    context = {
        'category': category,
        'attributes': attributes,
    }
    
    return render(request, 'inventory/settings/part_category_detail.html', context)


@login_required
def part_category_edit(request, category_id):
    """Edit a part category."""
    category = get_object_or_404(PartCategory, pk=category_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        
        if not name:
            return HttpResponse("Name is required", status=400)
        
        if not slug:
            from django.utils.text import slugify
            slug = slugify(name)
        
        # Ensure slug is unique (excluding current category)
        base_slug = slug
        counter = 1
        while PartCategory.objects.filter(slug=slug).exclude(id=category.id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        category.name = name
        category.slug = slug
        category.save()
        
        return redirect('inventory:part_category_detail', category_id=category.id)
    
    context = {
        'category': category,
    }
    
    return render(request, 'inventory/settings/part_category_form.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_category_delete(request, category_id):
    """Delete a part category."""
    category = get_object_or_404(PartCategory, pk=category_id)
    
    # Check if any parts are using this category
    if Part.objects.filter(category=category).exists():
        return HttpResponse("Cannot delete category that is in use by parts", status=400)
    
    category.delete()
    return redirect('inventory:part_categories_list')


# Settings HTMX endpoints
@login_required
@require_http_methods(["POST"])
@login_required
def part_attribute_add(request, category_id):
    """HTMX endpoint to add a new attribute to a category."""
    category = get_object_or_404(PartCategory, pk=category_id)
    
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    data_type = request.POST.get('data_type', '')
    unit = request.POST.get('unit', '').strip()
    is_required = request.POST.get('is_required') == 'on'
    sort_order = request.POST.get('sort_order', '0')
    help_text = request.POST.get('help_text', '').strip()
    
    if not name or not data_type:
        return HttpResponse("Name and data type are required", status=400)
    
    if not code:
        from django.utils.text import slugify
        code = slugify(name)
    
    # Ensure code is unique within category
    base_code = code
    counter = 1
    while PartAttribute.objects.filter(category=category, code=code).exists():
        code = f"{base_code}-{counter}"
        counter += 1
    
    try:
        sort_order = int(sort_order)
    except ValueError:
        sort_order = 0
    
    attribute = PartAttribute.objects.create(
        category=category,
        name=name,
        code=code,
        data_type=data_type,
        unit=unit,
        is_required=is_required,
        sort_order=sort_order,
        help_text=help_text
    )
    
    # Re-render the category detail
    return part_category_detail(request, category_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_attribute_edit(request, category_id, attribute_id):
    """HTMX endpoint to edit an attribute."""
    category = get_object_or_404(PartCategory, pk=category_id)
    attribute = get_object_or_404(PartAttribute, pk=attribute_id, category=category)
    
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    data_type = request.POST.get('data_type', '')
    unit = request.POST.get('unit', '').strip()
    is_required = request.POST.get('is_required') == 'on'
    sort_order = request.POST.get('sort_order', '0')
    help_text = request.POST.get('help_text', '').strip()
    
    if not name or not data_type:
        return HttpResponse("Name and data type are required", status=400)
    
    if not code:
        from django.utils.text import slugify
        code = slugify(name)
    
    # Ensure code is unique within category (excluding current attribute)
    base_code = code
    counter = 1
    while PartAttribute.objects.filter(category=category, code=code).exclude(id=attribute.id).exists():
        code = f"{base_code}-{counter}"
        counter += 1
    
    try:
        sort_order = int(sort_order)
    except ValueError:
        sort_order = 0
    
    attribute.name = name
    attribute.code = code
    attribute.data_type = data_type
    attribute.unit = unit
    attribute.is_required = is_required
    attribute.sort_order = sort_order
    attribute.help_text = help_text
    attribute.save()
    
    # Re-render the category detail
    return part_category_detail(request, category_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_attribute_delete(request, category_id, attribute_id):
    """HTMX endpoint to delete an attribute."""
    category = get_object_or_404(PartCategory, pk=category_id)
    attribute = get_object_or_404(PartAttribute, pk=attribute_id, category=category)
    
    # Check if any parts have values for this attribute
    if PartAttributeValue.objects.filter(attribute=attribute).exists():
        return HttpResponse("Cannot delete attribute that has values", status=400)
    
    attribute.delete()
    
    # Re-render the category detail
    return part_category_detail(request, category_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_attribute_choice_add(request, category_id, attribute_id):
    """HTMX endpoint to add a choice to a CHOICE attribute."""
    category = get_object_or_404(PartCategory, pk=category_id)
    attribute = get_object_or_404(PartAttribute, pk=attribute_id, category=category)
    
    if attribute.data_type != 'choice':
        return HttpResponse("Can only add choices to CHOICE attributes", status=400)
    
    value = request.POST.get('value', '').strip()
    label = request.POST.get('label', '').strip()
    sort_order = request.POST.get('sort_order', '0')
    
    if not value or not label:
        return HttpResponse("Value and label are required", status=400)
    
    # Ensure value is unique within attribute
    base_value = value
    counter = 1
    while PartAttributeChoice.objects.filter(attribute=attribute, value=value).exists():
        value = f"{base_value}-{counter}"
        counter += 1
    
    try:
        sort_order = int(sort_order)
    except ValueError:
        sort_order = 0
    
    choice = PartAttributeChoice.objects.create(
        attribute=attribute,
        value=value,
        label=label,
        sort_order=sort_order
    )
    
    # Re-render the category detail
    return part_category_detail(request, category_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_attribute_choice_edit(request, category_id, attribute_id, choice_id):
    """HTMX endpoint to edit a choice."""
    category = get_object_or_404(PartCategory, pk=category_id)
    attribute = get_object_or_404(PartAttribute, pk=attribute_id, category=category)
    choice = get_object_or_404(PartAttributeChoice, pk=choice_id, attribute=attribute)
    
    value = request.POST.get('value', '').strip()
    label = request.POST.get('label', '').strip()
    sort_order = request.POST.get('sort_order', '0')
    
    if not value or not label:
        return HttpResponse("Value and label are required", status=400)
    
    # Ensure value is unique within attribute (excluding current choice)
    base_value = value
    counter = 1
    while PartAttributeChoice.objects.filter(attribute=attribute, value=value).exclude(id=choice.id).exists():
        value = f"{base_value}-{counter}"
        counter += 1
    
    try:
        sort_order = int(sort_order)
    except ValueError:
        sort_order = 0
    
    choice.value = value
    choice.label = label
    choice.sort_order = sort_order
    choice.save()
    
    # Re-render the category detail
    return part_category_detail(request, category_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_attribute_choice_delete(request, category_id, attribute_id, choice_id):
    """HTMX endpoint to delete a choice."""
    category = get_object_or_404(PartCategory, pk=category_id)
    attribute = get_object_or_404(PartAttribute, pk=attribute_id, category=category)
    choice = get_object_or_404(PartAttributeChoice, pk=choice_id, attribute=attribute)
    
    # Check if any parts have this choice selected
    if PartAttributeValue.objects.filter(choice=choice).exists():
        return HttpResponse("Cannot delete choice that is in use", status=400)
    
    choice.delete()
    
    # Re-render the category detail
    return part_category_detail(request, category_id)


# Vendor Management Views
@login_required
def part_vendor_add_form(request, part_id):
    """HTMX endpoint to render the add vendor form."""
    part = get_object_or_404(Part, pk=part_id)
    
    # Get vendors that are NOT already associated with this part
    existing_vendor_ids = part.vendor_links.values_list('vendor_id', flat=True)
    vendors = Vendor.objects.exclude(id__in=existing_vendor_ids).order_by('name')
    
    context = {
        'part': part,
        'vendors': vendors,
    }
    
    return render(request, 'inventory/partials/part_vendor_add_form.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def part_vendor_add(request, part_id):
    """HTMX endpoint to add a vendor to a part."""
    part = get_object_or_404(Part, pk=part_id)
    
    vendor_id = request.POST.get('vendor_id')
    vendor_sku = request.POST.get('vendor_sku', '').strip()
    cost = request.POST.get('cost', '').strip()
    stock_qty = request.POST.get('stock_qty', '0').strip()
    lead_time_days = request.POST.get('lead_time_days', '').strip()
    notes = request.POST.get('notes', '').strip()
    
    if not vendor_id:
        return HttpResponse("Vendor is required", status=400)
    
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return HttpResponse("Invalid vendor", status=400)
    
    # Check if this vendor is already associated with this part
    if PartVendor.objects.filter(part=part, vendor=vendor).exists():
        return HttpResponse("This vendor is already associated with this part", status=400)
    
    # Parse numeric fields
    try:
        stock_qty = int(stock_qty) if stock_qty else 0
        lead_time_days = int(lead_time_days) if lead_time_days else None
        cost = float(cost) if cost else None
    except ValueError:
        return HttpResponse("Invalid numeric values", status=400)
    
    part_vendor = PartVendor.objects.create(
        part=part,
        vendor=vendor,
        vendor_sku=vendor_sku,
        cost=cost,
        stock_qty=stock_qty,
        lead_time_days=lead_time_days,
        notes=notes
    )
    
    # Auto-set primary vendor if only one vendor exists
    part.auto_set_primary_vendor()
    
    # Re-render the vendors section
    return part_vendors_section(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_vendor_edit(request, part_id, part_vendor_id):
    """HTMX endpoint to edit a part vendor."""
    part = get_object_or_404(Part, pk=part_id)
    part_vendor = get_object_or_404(PartVendor, pk=part_vendor_id, part=part)
    
    vendor_sku = request.POST.get('vendor_sku', '').strip()
    cost = request.POST.get('cost', '').strip()
    stock_qty = request.POST.get('stock_qty', '0').strip()
    lead_time_days = request.POST.get('lead_time_days', '').strip()
    notes = request.POST.get('notes', '').strip()
    
    # Parse numeric fields
    try:
        stock_qty = int(stock_qty) if stock_qty else 0
        lead_time_days = int(lead_time_days) if lead_time_days else None
        cost = float(cost) if cost else None
    except ValueError:
        return HttpResponse("Invalid numeric values", status=400)
    
    part_vendor.vendor_sku = vendor_sku
    part_vendor.cost = cost
    part_vendor.stock_qty = stock_qty
    part_vendor.lead_time_days = lead_time_days
    part_vendor.notes = notes
    part_vendor.save()
    
    # Re-render the vendors section
    return part_vendors_section(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_vendor_delete(request, part_id, part_vendor_id):
    """HTMX endpoint to delete a part vendor."""
    part = get_object_or_404(Part, pk=part_id)
    part_vendor = get_object_or_404(PartVendor, pk=part_vendor_id, part=part)
    
    part_vendor.delete()
    
    # Auto-set primary vendor if only one vendor exists
    part.auto_set_primary_vendor()
    
    # Re-render the vendors section
    return part_vendors_section(request, part_id)


@login_required
@require_http_methods(["POST"])
@login_required
def part_vendor_set_primary(request, part_id, part_vendor_id):
    """HTMX endpoint to set a vendor as the primary vendor for a part."""
    part = get_object_or_404(Part, pk=part_id)
    part_vendor = get_object_or_404(PartVendor, pk=part_vendor_id, part=part)
    
    part.primary_vendor = part_vendor.vendor
    part.save()
    
    # Re-render the vendors section
    return part_vendors_section(request, part_id)


@login_required
def part_vendors_section(request, part_id):
    """HTMX endpoint to render the vendors section for a part."""
    part = get_object_or_404(Part, pk=part_id)
    
    # Get part vendors for the vendors section
    part_vendors = part.vendor_links.select_related('vendor').all()
    total_stock = sum(pv.stock_qty or 0 for pv in part_vendors)
    
    # Get all vendors for the add form
    vendors = Vendor.objects.all().order_by('name')
    
    context = {
        'part': part,
        'part_vendors': part_vendors,
        'total_stock': total_stock,
        'vendors': vendors,
    }
    
    return render(request, 'inventory/partials/_part_vendors_section.html', context)


@login_required
def vendor_search_modal_for_part(request, part_id):
    """Renders the vendor search modal for adding vendors to a part."""
    part = get_object_or_404(Part, pk=part_id)
    # Get already linked vendors to exclude them from search
    linked_vendor_ids = PartVendor.objects.filter(part=part).values_list('vendor_id', flat=True)
    vendors = Vendor.objects.exclude(id__in=linked_vendor_ids).order_by('name')[:20]
    
    context = {
        'part': part,
        'vendors': vendors,
    }
    return render(request, 'inventory/partials/vendor_search_modal_for_part.html', context)


@login_required
def vendor_search_results_for_part(request, part_id):
    """Handles the search query for vendors to add to a part."""
    part = get_object_or_404(Part, pk=part_id)
    query = request.GET.get('q', '').strip()
    
    # Get already linked vendors to exclude them
    linked_vendor_ids = PartVendor.objects.filter(part=part).values_list('vendor_id', flat=True)
    
    vendors = Vendor.objects.exclude(id__in=linked_vendor_ids)
    
    if query:
        from django.db.models import Q
        vendors = vendors.filter(
            Q(name__icontains=query) |
            Q(contact_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    
    vendors = vendors.order_by('name')[:50]  # Limit results
    
    context = {
        'part': part,
        'vendors': vendors,
    }
    return render(request, 'inventory/partials/vendor_search_results_for_part.html', context)


@login_required
def vendor_details_form_for_part(request, part_id):
    """Renders the vendor details form modal after selecting a vendor."""
    part = get_object_or_404(Part, pk=part_id)
    vendor_id = request.GET.get('vendor_id')
    
    if not vendor_id:
        return HttpResponse("Vendor ID required", status=400)
    
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    
    context = {
        'part': part,
        'vendor': vendor,
    }
    return render(request, 'inventory/partials/vendor_details_form_modal.html', context)


# Build List Views
@login_required
def engine_build_lists_section(request, engine_id):
    """HTMX endpoint to render the build lists section for an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Get build lists for the engine
    build_lists = engine.build_lists.all().order_by('-updated_at')
    
    context = {
        'engine': engine,
        'build_lists': build_lists,
    }
    
    return render(request, 'inventory/partials/_engine_build_lists.html', context)


@login_required
def build_list_add_form(request, engine_id):
    """HTMX endpoint to render the add build list form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    context = {
        'engine': engine,
    }
    
    return render(request, 'inventory/partials/build_list_add_form.html', context)


# New engine-based kit management views
# NOTE: Kits are now independent and not connected to build lists
# These views need refactoring for the new system
@login_required
def engine_kits_section(request, engine_id):
    """HTMX endpoint to render the kits section for an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    # TODO: Implement kit management for independent kits
    kits = Kit.objects.all().order_by('-updated_at')  # Temporary: show all kits
    
    context = {
        'engine': engine,
        'kits': kits,
    }
    
    return render(request, 'inventory/partials/_engine_kits.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def engine_kit_create(request, engine_id):
    """HTMX endpoint to create a new kit for an engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    name = request.POST.get('name', '').strip()
    notes = request.POST.get('notes', '').strip()
    margin_pct = request.POST.get('margin_pct', '0').strip()
    
    if not name:
        return HttpResponse("Kit name is required", status=400)
    
    # Check for duplicate kit names
    if Kit.objects.filter(name__iexact=name).exists():
        return HttpResponse("A kit with this name already exists", status=400)
    
    try:
        margin_pct = Decimal(margin_pct)
    except (ValueError, InvalidOperation):
        margin_pct = Decimal('0.00')
    
    kit = Kit.objects.create(
        name=name,
        notes=notes,
        margin_pct=margin_pct
    )
    
    # Re-render the kits section
    return engine_kits_section(request, engine_id)


@login_required
def engine_kit_add_form(request, engine_id):
    """HTMX endpoint to render the add kit form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    context = {
        'engine': engine,
    }
    
    return render(request, 'inventory/partials/engine_kit_add_form.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def build_list_create(request, engine_id):
    """HTMX endpoint to create a new build list."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    name = request.POST.get('name', '').strip()
    notes = request.POST.get('notes', '').strip()
    
    if not name:
        return HttpResponse("Build list name is required", status=400)
    
    # Check for duplicate names within this engine
    if BuildList.objects.filter(engine=engine, name__iexact=name).exists():
        return HttpResponse("A build list with this name already exists for this engine", status=400)
    
    build_list = BuildList.objects.create(
        engine=engine,
        name=name,
        notes=notes
    )
    
    # Re-render the build lists section
    return engine_build_lists_section(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def build_list_rename(request, build_list_id):
    """HTMX endpoint to rename a build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    name = request.POST.get('name', '').strip()
    
    if not name:
        return HttpResponse("Build list name is required", status=400)
    
    # Check for duplicate names within this engine
    if BuildList.objects.filter(engine=build_list.engine, name__iexact=name).exclude(id=build_list.id).exists():
        return HttpResponse("A build list with this name already exists for this engine", status=400)
    
    build_list.name = name
    build_list.save()
    
    # Re-render the build lists section
    return engine_build_lists_section(request, build_list.engine.id)


@login_required
@require_http_methods(["POST"])
@login_required
def build_list_delete(request, build_list_id):
    """HTMX endpoint to delete a build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    engine_id = build_list.engine.id
    
    build_list.delete()
    
    # Re-render the build lists section
    return engine_build_lists_section(request, engine_id)


@login_required
def build_list_detail(request, engine_id, build_list_id):
    """Display build list detail with kits."""
    engine = get_object_or_404(Engine, pk=engine_id)
    build_list = get_object_or_404(BuildList, pk=build_list_id, engine=engine)
    
    # Get kits for the build list
    kits = build_list.kits.all().order_by('-updated_at')
    
    context = {
        'engine': engine,
        'build_list': build_list,
        'kits': kits,
    }
    
    return render(request, 'inventory/build_list_detail.html', context)


@login_required
def build_list_detail_redirect(request, engine_id, build_list_id):
    """Redirect old build list detail URLs to engine detail."""
    return redirect('inventory:engine_detail', engine_id=engine_id)


@login_required
def build_list_redirect(request, build_list_id):
    """Redirect old build list URLs to engine detail."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    return redirect('inventory:engine_detail', engine_id=build_list.engine.id)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_create(request, build_list_id):
    """HTMX endpoint to create a new kit."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    name = request.POST.get('name', '').strip()
    notes = request.POST.get('notes', '').strip()
    margin_pct = request.POST.get('margin_pct', '0').strip()
    
    if not name:
        return HttpResponse("Kit name is required", status=400)
    
    # Check for duplicate names within this build list
    if Kit.objects.filter(build_list=build_list, name__iexact=name).exists():
        return HttpResponse("A kit with this name already exists in this build list", status=400)
    
    try:
        margin_pct = Decimal(margin_pct)
    except (ValueError, InvalidOperation):
        margin_pct = Decimal('0.00')
    
    kit = Kit.objects.create(
        build_list=build_list,
        name=name,
        notes=notes,
        margin_pct=margin_pct
    )
    
    # Re-render the kits section
    return build_list_kits_section(request, build_list_id)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_rename(request, kit_id):
    """HTMX endpoint to rename/edit a kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    name = request.POST.get('name', '').strip()
    notes = request.POST.get('notes', '').strip()
    margin_pct = request.POST.get('margin_pct', '0').strip()
    
    if not name:
        return HttpResponse("Kit name is required", status=400)
    
    # Check for duplicate names within this build list
    if Kit.objects.filter(build_list=kit.build_list, name__iexact=name).exclude(id=kit.id).exists():
        return HttpResponse("A kit with this name already exists in this build list", status=400)
    
    try:
        margin_pct = Decimal(margin_pct)
    except (ValueError, InvalidOperation):
        margin_pct = Decimal('0.00')
    
    kit.name = name
    kit.notes = notes
    kit.margin_pct = margin_pct
    kit.save()
    
    # Recalculate totals since margin changed
    kit.recalc_totals()
    
    # Re-render the kits section
    return engine_kits_section(request, kit.build_list.engine.id)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_delete(request, kit_id):
    """HTMX endpoint to delete a kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    engine_id = kit.build_list.engine.id
    
    kit.delete()
    
    # Re-render the kits section
    return engine_kits_section(request, engine_id)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_duplicate(request, kit_id):
    """HTMX endpoint to duplicate a kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Create a copy of the kit
    new_kit = Kit.objects.create(
        build_list=kit.build_list,
        name=f"{kit.name} (Copy)",
        notes=kit.notes,
        margin_pct=kit.margin_pct
    )
    
    # Copy all items
    for item in kit.items.all():
        KitItem.objects.create(
            kit=new_kit,
            part=item.part,
            vendor=item.vendor,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            notes=item.notes
        )
    
    # Recalculate totals for the new kit
    new_kit.recalc_totals()
    
    # Re-render the kits section
    return engine_kits_section(request, kit.build_list.engine.id)


@login_required
def build_list_kits_section(request, build_list_id):
    """HTMX endpoint to render the kits section for a build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    # Get kits for the build list
    kits = build_list.kits.all().order_by('-updated_at')
    
    context = {
        'build_list': build_list,
        'kits': kits,
    }
    
    return render(request, 'inventory/partials/_build_list_kits.html', context)


@login_required
def kit_detail(request, kit_id):
    """Display kit detail with items."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Get items for the kit
    items = kit.items.select_related('part', 'vendor').all().order_by('part__part_number')
    
    # Get all parts for the add form
    parts = Part.objects.all().order_by('part_number')
    
    # Get all vendors for the add form
    vendors = Vendor.objects.all().order_by('name')
    
    context = {
        'kit': kit,
        'items': items,
        'parts': parts,
        'vendors': vendors,
    }
    
    return render(request, 'inventory/kit_detail.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_set_margin(request, kit_id):
    """HTMX endpoint to set kit margin and recalculate totals."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    margin_pct = request.POST.get('margin_pct', '0').strip()
    
    try:
        margin_pct = Decimal(margin_pct)
    except (ValueError, InvalidOperation):
        margin_pct = Decimal('0.00')
    
    kit.margin_pct = margin_pct
    kit.save()
    
    # Recalculate totals
    kit.recalc_totals()
    
    # Re-render the kit items section
    return kit_items_section(request, kit_id)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_item_add(request, kit_id):
    """HTMX endpoint to add an item to a kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Create form data from POST
    form_data = {
        'part': request.POST.get('part_id'),
        'vendor': request.POST.get('vendor_id'),
        'quantity': request.POST.get('quantity', '1').strip(),
        'unit_cost': request.POST.get('unit_cost', '').strip(),
        'notes': request.POST.get('notes', '').strip(),
    }
    
    form = KitItemForm(data=form_data)
    
    if form.is_valid():
        # Check if this combination already exists
        if KitItem.objects.filter(kit=kit, part=form.cleaned_data['part'], vendor=form.cleaned_data['vendor']).exists():
            return HttpResponse("This part-vendor combination already exists in this kit", status=400)
        
        # Create the kit item
        kit_item = form.save(commit=False)
        kit_item.kit = kit
        kit_item.save()
        
        # Recalculate kit totals
        kit.recalc_totals()
        
        # Re-render the kit items section
        return kit_items_section(request, kit_id)
    else:
        # Return form errors
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field}: {error}")
        return HttpResponse("; ".join(error_messages), status=400)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_item_edit(request, kit_id, item_id):
    """HTMX endpoint to edit a kit item."""
    kit = get_object_or_404(Kit, pk=kit_id)
    item = get_object_or_404(KitItem, pk=item_id, kit=kit)
    
    # Create form data from POST
    form_data = {
        'part': item.part.id,  # Keep existing part
        'vendor': item.vendor.id,  # Keep existing vendor
        'quantity': request.POST.get('quantity', '1').strip(),
        'unit_cost': request.POST.get('unit_cost', '').strip(),
        'notes': request.POST.get('notes', '').strip(),
    }
    
    form = KitItemForm(data=form_data, instance=item)
    
    if form.is_valid():
        form.save()
        
        # Recalculate kit totals
        kit.recalc_totals()
        
        # Re-render the kit items section
        return kit_items_section(request, kit_id)
    else:
        # Return form errors
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field}: {error}")
        return HttpResponse("; ".join(error_messages), status=400)


@login_required
@require_http_methods(["POST"])
@login_required
def kit_item_remove(request, kit_id, item_id):
    """HTMX endpoint to remove an item from a kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    item = get_object_or_404(KitItem, pk=item_id, kit=kit)
    
    item.delete()
    
    # Recalculate kit totals
    kit.recalc_totals()
    
    # Re-render the kit items section
    return kit_items_section(request, kit_id)


@login_required
def kit_items_section(request, kit_id):
    """HTMX endpoint to render the items section for a kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Get items for the kit
    items = kit.items.select_related('part', 'vendor').all().order_by('part__part_number')
    
    # Get all parts for the add form
    parts = Part.objects.all().order_by('part_number')
    
    # Get all vendors for the add form
    vendors = Vendor.objects.all().order_by('name')
    
    context = {
        'kit': kit,
        'items': items,
        'parts': parts,
        'vendors': vendors,
    }
    
    return render(request, 'inventory/partials/_kit_items_section.html', context)


@login_required
def get_vendors_for_part(request, part_id):
    """HTMX endpoint to get vendors for a specific part."""
    try:
        part = get_object_or_404(Part, pk=part_id)
        
        # Get vendors that have this part
        part_vendors = list(part.vendor_links.select_related('vendor').all())
        
        # Reorder part_vendors to put primary vendor first
        if part.primary_vendor:
            # Find the primary vendor in part_vendors and move it to the front
            primary_vendor_pv = None
            other_vendors_pv = []
            
            for pv in part_vendors:
                if pv.vendor == part.primary_vendor:
                    primary_vendor_pv = pv
                else:
                    other_vendors_pv.append(pv)
            
            # Reconstruct the list with primary vendor first
            if primary_vendor_pv:
                part_vendors = [primary_vendor_pv] + other_vendors_pv
        
        # Get all vendors and create a set of vendor IDs that have this part
        all_vendors = Vendor.objects.all().order_by('name')
        part_vendor_ids = {pv.vendor.id for pv in part_vendors}
        
        # Create a list of vendors that don't have this part
        other_vendors = [v for v in all_vendors if v.id not in part_vendor_ids]
        
        context = {
            'part_vendors': part_vendors,
            'all_vendors': all_vendors,
            'part_vendor_ids': part_vendor_ids,
            'other_vendors': other_vendors,
            'primary_vendor': part.primary_vendor,
        }
        
        return render(request, 'inventory/partials/_vendor_select_options.html', context)
    except Exception as e:
        # Log the error and return a simple error response
        print(f"Error in get_vendors_for_part: {e}")
        return HttpResponse(f"<option value=''>Error loading vendors</option>", status=500)


# New stable container Engine-Interchange relationship views
@login_required
def engine_interchanges_partial(request, engine_id):
    """HTMX endpoint to render the engine interchanges partial (table + form)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    interchanges = engine.interchanges.select_related('sg_engine').all()
    show_form = request.GET.get('show_form') == '1'
    form = EngineInterchangeForm(engine=engine)
    
    context = {
        'engine': engine,
        'interchanges': interchanges,
        'form': form,
        'show_form': show_form,
    }
    
    return render(request, 'inventory/partials/_engine_interchanges_partial.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def engine_interchange_add(request, engine_id):
    """HTMX endpoint to add an interchange to an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest()
    
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Handle direct engine_id submission from modal
    engine_id_from_modal = request.POST.get('engine_id')
    if engine_id_from_modal:
        try:
            interchange_engine = Engine.objects.get(id=engine_id_from_modal)
            
            if interchange_engine != engine:
                engine.interchanges.add(interchange_engine)
            
            # Return updated partial
            interchanges = engine.interchanges.select_related('sg_engine').all()
            ctx = {
                "engine": engine,
                "interchanges": interchanges,
                "form": EngineInterchangeForm(engine=engine),
                "show_form": False,
            }
            return render(request, "inventory/partials/_engine_interchanges_partial.html", ctx)
            
        except Engine.DoesNotExist:
            return HttpResponseBadRequest("Engine not found")
    
    # Handle form submission (legacy)
    form = EngineInterchangeForm(request.POST, engine=engine)
    
    if form.is_valid():
        interchange_sg_engine_id = form.cleaned_data['interchange_engine']
        
        try:
            sg_engine = SGEngine.objects.get(id=interchange_sg_engine_id)
            
            # First, try to find an existing Engine record for this SG Engine
            interchange_engine = Engine.objects.filter(sg_engine=sg_engine).first()
            
            if not interchange_engine:
                # Create a new Engine record for this SG Engine
                interchange_engine = Engine.objects.create(
                    sg_engine=sg_engine,
                    engine_make=sg_engine.sg_make,
                    engine_model=sg_engine.sg_model,
                    sg_engine_identifier=sg_engine.identifier,
                )
            
            # Create the interchange relationship
            engine.interchanges.add(interchange_engine)
            
            interchanges = engine.interchanges.select_related('sg_engine').all()
            return render(request, 'inventory/partials/_engine_interchanges_partial.html', {
                'engine': engine,
                'interchanges': interchanges,
                'form': EngineInterchangeForm(engine=engine),
                'show_form': False,
            })
        except SGEngine.DoesNotExist:
            form.add_error('interchange_engine', 'Selected SG Engine does not exist.')
    
    # Error case
    interchanges = engine.interchanges.select_related('sg_engine').all()
    response = render(request, 'inventory/partials/_engine_interchanges_partial.html', {
        'engine': engine,
        'interchanges': interchanges,
        'form': form,
        'show_form': True,
    })
    response.status_code = 400
    return response


@login_required
@require_http_methods(["POST"])
@login_required
def engine_interchange_remove(request, engine_id, interchange_id):
    """HTMX endpoint to remove an interchange from an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    engine = get_object_or_404(Engine, pk=engine_id)
    interchange_engine = get_object_or_404(Engine, pk=interchange_id)
    engine.interchanges.remove(interchange_engine)
    
    interchanges = engine.interchanges.select_related('sg_engine').all()
    ctx = {
        "engine": engine,
        "interchanges": interchanges,
        "form": EngineInterchangeForm(engine=engine),
        "show_form": False,
    }
    return render(request, "inventory/partials/_engine_interchanges_partial.html", ctx)


# New stable container Engine-Compatible relationship views
@login_required
def engine_compatibles_partial(request, engine_id):
    """HTMX endpoint to render the engine compatibles partial (table + form)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    compatibles = engine.compatibles.select_related('sg_engine').all()
    show_form = request.GET.get('show_form') == '1'
    form = EngineCompatibleForm(engine=engine)
    
    context = {
        'engine': engine,
        'compatibles': compatibles,
        'form': form,
        'show_form': show_form,
    }
    
    return render(request, 'inventory/partials/_engine_compatibles_partial.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def engine_compatible_add(request, engine_id):
    """HTMX endpoint to add a compatible to an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest()
    
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Handle direct engine_id submission from modal
    engine_id_from_modal = request.POST.get('engine_id')
    if engine_id_from_modal:
        try:
            compatible_engine = Engine.objects.get(id=engine_id_from_modal)
            
            if compatible_engine != engine:
                engine.compatibles.add(compatible_engine)
            
            # Return updated partial
            compatibles = engine.compatibles.select_related('sg_engine').all()
            ctx = {
                "engine": engine,
                "compatibles": compatibles,
                "form": EngineCompatibleForm(engine=engine),
                "show_form": False,
            }
            return render(request, "inventory/partials/_engine_compatibles_partial.html", ctx)
            
        except Engine.DoesNotExist:
            return HttpResponseBadRequest("Engine not found")
    
    # Handle form submission (legacy)
    form = EngineCompatibleForm(request.POST, engine=engine)
    
    if form.is_valid():
        compatible_sg_engine_id = form.cleaned_data['compatible_engine']
        
        try:
            sg_engine = SGEngine.objects.get(id=compatible_sg_engine_id)
            
            # First, try to find an existing Engine record for this SG Engine
            compatible_engine = Engine.objects.filter(sg_engine=sg_engine).first()
            
            if not compatible_engine:
                # Create a new Engine record for this SG Engine
                compatible_engine = Engine.objects.create(
                    sg_engine=sg_engine,
                    engine_make=sg_engine.sg_make,
                    engine_model=sg_engine.sg_model,
                    sg_engine_identifier=sg_engine.identifier,
                )
            
            # Add the compatible (symmetrical relationship)
            engine.compatibles.add(compatible_engine)
            
            compatibles = engine.compatibles.select_related('sg_engine').all()
            return render(request, 'inventory/partials/_engine_compatibles_partial.html', {
                'engine': engine,
                'compatibles': compatibles,
                'form': EngineCompatibleForm(engine=engine),
                'show_form': False,
            })
        except SGEngine.DoesNotExist:
            form.add_error('compatible_engine', 'Selected SG Engine does not exist.')
    
    # Error case
    compatibles = engine.compatibles.select_related('sg_engine').all()
    response = render(request, 'inventory/partials/_engine_compatibles_partial.html', {
        'engine': engine,
        'compatibles': compatibles,
        'form': form,
        'show_form': True,
    })
    response.status_code = 400
    return response


@login_required
@require_http_methods(["POST"])
@login_required
def engine_compatible_remove(request, engine_id, compatible_id):
    """HTMX endpoint to remove a compatible from an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    engine = get_object_or_404(Engine, pk=engine_id)
    compatible_engine = get_object_or_404(Engine, pk=compatible_id)
    engine.compatibles.remove(compatible_engine)
    
    compatibles = engine.compatibles.select_related('sg_engine').all()
    ctx = {
        "engine": engine,
        "compatibles": compatibles,
        "form": EngineCompatibleForm(engine=engine),
        "show_form": False,
    }
    return render(request, "inventory/partials/_engine_compatibles_partial.html", ctx)


# New stable container Engine-Supercession relationship views
@login_required
def engine_supercession_form(request, engine_id, direction):
    """HTMX endpoint to render the engine supercession form."""
    engine = get_object_or_404(Engine, pk=engine_id)
    sg_engines = SGEngine.objects.all().order_by("sg_make", "sg_model", "identifier")
    return render(request, "inventory/partials/_engine_supercession_form.html", {
        "engine": engine,
        "sg_engines": sg_engines,
        "direction": direction,  # "older" or "newer"
    })


@login_required
def engine_supercessions_partial(request, engine_id):
    """HTMX endpoint to render the engine supercessions partial (table only)."""
    engine = get_object_or_404(Engine, pk=engine_id)
    supersedes = engine.supersedes.select_related('sg_engine').all()
    superseded_by = engine.superseded_by.select_related('sg_engine').all()
    
    context = {
        'engine': engine,
        'supersedes': supersedes,
        'superseded_by': superseded_by,
    }
    
    return render(request, 'inventory/partials/_engine_supercessions_partial.html', context)


@login_required
@require_http_methods(["POST"])
@login_required
def engine_supercession_add(request, engine_id, direction):
    """HTMX endpoint to add a supercession to an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest()
    
    try:
        engine = get_object_or_404(Engine, pk=engine_id)
        other_engine_id = request.POST.get("engine_id")
        sg_engine_id = request.POST.get("sg_engine_id")
        
        other = None
        if other_engine_id:
            other = get_object_or_404(Engine, pk=other_engine_id)
        elif sg_engine_id:
            other = Engine.objects.filter(sg_engine_id=sg_engine_id).first()
            if not other:
                sg_engine = SGEngine.objects.get(id=sg_engine_id)
                other = Engine.objects.create(
                    sg_engine=sg_engine,
                    engine_make=sg_engine.sg_make,
                    engine_model=sg_engine.sg_model,
                    sg_engine_identifier=sg_engine.identifier,
                )
        else:
            return HttpResponseBadRequest("engine_id is required")

        if direction == "older":
            # Current engine is newer → supersedes older engine
            # from_engine=current, to_engine=older (current supersedes older)
            EngineSupercession.objects.get_or_create(from_engine=engine, to_engine=other)
        else:
            # Current engine is older → superseded by newer engine
            # from_engine=newer, to_engine=current (newer supersedes current)
            EngineSupercession.objects.get_or_create(from_engine=other, to_engine=engine)

        return render(request, "inventory/partials/_engine_supercessions_partial.html", {
            "engine": engine,
            "supersedes": engine.supersedes.select_related('sg_engine').all(),
            "superseded_by": engine.superseded_by.select_related('sg_engine').all(),
        })
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in engine_supercession_add: {str(e)}")
        return HttpResponseBadRequest(f"Error: {str(e)}")


@login_required
@require_http_methods(["POST"])
@login_required
def engine_supercession_remove(request, engine_id, superseded_id):
    """HTMX endpoint to remove a supercession from an engine."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    engine = get_object_or_404(Engine, pk=engine_id)
    superseded_engine = get_object_or_404(Engine, pk=superseded_id)
    # Remove the supercession relationship using the through model
    EngineSupercession.objects.filter(
        from_engine=engine,
        to_engine=superseded_engine
    ).delete()
    
    supersedes = engine.supersedes.select_related('sg_engine').all()
    superseded_by = engine.superseded_by.select_related('sg_engine').all()
    ctx = {
        "engine": engine,
        "supersedes": supersedes,
        "superseded_by": superseded_by,
    }
    return render(request, "inventory/partials/_engine_supercessions_partial.html", ctx)


# ---------- Build List Views ----------

@login_required
def build_lists_list(request):
    """Display list of build lists with search and sorting."""
    from django.db.models import Count, Sum
    from core.view_utils import get_list_context
    
    # Base queryset with annotations
    build_lists = BuildList.objects.annotate(
        engines_count=Count('engines'),
        total_hours=Sum('items__hour_qty')
    ).all()
    
    # Get list context with search, sort, and pagination
    context = get_list_context(
        queryset=build_lists,
        request=request,
        search_fields=['name', 'notes'],
        sort_fields={
            'name', '-name', 'engines_count', '-engines_count',
            'total_hours', '-total_hours', 'created_at', '-created_at'
        },
        default_sort=['name'],
        per_page=200
    )
    
    # Add build_lists to context for template compatibility
    context['build_lists'] = context['object_list']
    
    return render(request, 'inventory/build_lists_list.html', context)


@login_required
def build_list_detail(request, build_list_id):
    """Redirect to edit page - there is no separate view page."""
    return redirect('inventory:build_list_edit', build_list_id=build_list_id)


@login_required
@require_http_methods(["GET", "POST"])
def build_list_create(request):
    """Create new build list - uses edit.html with is_new=True like vendor pattern."""
    form = BuildListForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            build_list = form.save(commit=False)
            if request.user.is_authenticated:
                build_list.created_by = request.user
            build_list.save()
            return redirect("inventory:build_list_edit", build_list_id=build_list.id)
    
    return render(request, 'inventory/build_lists/edit.html', {
        'form': form,
        'build_list': None,
        'is_new': True,
        'items': [],
        'engines': [],
        'total_hours': 0,
        'item_count': 0,
        'engine_count': 0,
    })


@login_required
def build_list_create_modal(request):
    """HTMX endpoint to show/handle build list creation modal."""
    if request.method == "POST":
        form = BuildListForm(request.POST)
        if form.is_valid():
            build_list = form.save(commit=False)
            if request.user.is_authenticated:
                build_list.created_by = request.user
            build_list.save()
            
            # Return a script that closes the modal and redirects to the edit page
            return HttpResponse(
                f'<script>document.body.dispatchEvent(new Event("buildListCreated")); window.location.href = "/inventory/build-lists/{build_list.id}/edit/";</script>',
                content_type='text/html'
            )
        else:
            # Re-render the modal with errors
            return render(request, 'inventory/modals/build_list_create_modal.html', {
                'form': form,
            })
    else:
        # GET request - show empty form
        form = BuildListForm()
        return render(request, 'inventory/modals/build_list_create_modal.html', {
            'form': form,
        })


@login_required
@require_http_methods(["GET", "POST"])
def build_list_edit(request, build_list_id):
    """Edit build list - main edit page with all related items and engines."""
    from django.db.models import Sum
    
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    if request.method == "POST":
        form = BuildListForm(request.POST, instance=build_list)
        if form.is_valid():
            form.save()
            messages.success(request, "Build list updated.")
            return redirect("inventory:build_list_edit", build_list_id=build_list.id)
    else:
        form = BuildListForm(instance=build_list)
    
    # Get items and engines for display
    items = build_list.items.all()
    engines = build_list.engines.all()
    
    # Calculate total hours
    total_hours = build_list.items.aggregate(total=Sum('hour_qty'))['total'] or 0
    
    context = {
        'form': form,
        'build_list': build_list,
        'items': items,
        'engines': engines,
        'total_hours': total_hours,
        'item_count': items.count(),
        'engine_count': engines.count(),
    }
    
    return render(request, 'inventory/build_lists/edit.html', context)


@login_required
@require_http_methods(["POST"])
def build_list_update(request, build_list_id):
    """POST-only endpoint for updating build list via form."""
    from django.db.models import Sum
    
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    form = BuildListForm(request.POST, instance=build_list)
    
    if form.is_valid():
        form.save()
        return redirect("inventory:build_lists_list")
    
    # If form is invalid, re-render the edit page with errors
    items = build_list.items.all()
    engines = build_list.engines.all()
    total_hours = build_list.items.aggregate(total=Sum('hour_qty'))['total'] or 0
    
    context = {
        'form': form,
        'build_list': build_list,
        'items': items,
        'engines': engines,
        'total_hours': total_hours,
        'item_count': items.count(),
        'engine_count': engines.count(),
    }
    
    return render(request, 'inventory/build_lists/edit.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def build_list_delete(request, build_list_id):
    """Delete build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    build_list.delete()
    messages.success(request, "Build list deleted.")
    return redirect("inventory:build_lists_list")


# Build List Items (HTMX)

@login_required
def build_list_items_partial(request, build_list_id):
    """HTMX partial for build list items table."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    items = build_list.items.all()
    
    context = {
        'build_list': build_list,
        'items': items,
    }
    
    return render(request, 'inventory/partials/_build_list_items.html', context)


@login_required
def build_list_total_hours_partial(request, build_list_id):
    """HTMX partial for total hours display."""
    from django.db.models import Sum
    
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    total_hours = build_list.items.aggregate(total=Sum('hour_qty'))['total'] or 0
    
    context = {
        'total_hours': total_hours,
    }
    
    return render(request, 'inventory/partials/_build_list_total_hours.html', context)


@login_required
def build_list_item_add_modal(request, build_list_id):
    """HTMX modal to add item."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    context = {
        'build_list': build_list,
    }
    
    return render(request, 'inventory/partials/build_list_item_add_modal.html', context)


@login_required
@require_http_methods(["POST"])
def build_list_item_add(request, build_list_id):
    """POST: Create item."""
    from django.db.models import Sum
    from django.template.loader import render_to_string
    
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    # Get data from POST
    name = request.POST.get('name')
    hour_qty = request.POST.get('hour_qty', 0)
    description = request.POST.get('description', '')
    
    if name:
        BuildListItem.objects.create(
            build_list=build_list,
            name=name,
            hour_qty=hour_qty,
            description=description
        )
        messages.success(request, "Item added.")
    
    # Render the items table
    items = build_list.items.all()
    items_html = render_to_string('inventory/partials/_build_list_items.html', {
        'build_list': build_list,
        'items': items,
    }, request=request)
    
    # Render the total hours for out-of-band swap (header badge)
    total_hours = build_list.items.aggregate(total=Sum('hour_qty'))['total'] or 0
    
    # Out-of-band swap for the hours badge in the header
    oob_hours_badge = f'<span class="build-list-hours-badge" id="total-hours-display" hx-swap-oob="true">{total_hours} hrs</span>'
    
    # Combine both
    combined_html = items_html + oob_hours_badge
    
    return HttpResponse(combined_html)


@login_required
def build_list_item_edit_form(request, build_list_id, item_id):
    """HTMX form to edit item (legacy inline form)."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    item = get_object_or_404(BuildListItem, pk=item_id, build_list=build_list)
    form = BuildListItemForm(instance=item)
    
    context = {
        'build_list': build_list,
        'item': item,
        'form': form,
    }
    
    return render(request, 'inventory/partials/_build_list_item_edit_form.html', context)


@login_required
def build_list_item_edit_modal(request, build_list_id, item_id):
    """HTMX modal to edit item."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    item = get_object_or_404(BuildListItem, pk=item_id, build_list=build_list)
    form = BuildListItemForm(instance=item)
    
    context = {
        'build_list': build_list,
        'item': item,
        'form': form,
    }
    
    return render(request, 'inventory/partials/build_list_item_edit_modal.html', context)


@login_required
@require_http_methods(["POST"])
def build_list_item_edit(request, build_list_id, item_id):
    """POST: Update item."""
    from django.db.models import Sum
    from django.template.loader import render_to_string
    
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    item = get_object_or_404(BuildListItem, pk=item_id, build_list=build_list)
    form = BuildListItemForm(request.POST, instance=item)
    
    if form.is_valid():
        form.save()
        messages.success(request, "Item updated.")
        
        # Render the items table
        items = build_list.items.all()
        items_html = render_to_string('inventory/partials/_build_list_items.html', {
            'build_list': build_list,
            'items': items,
        }, request=request)
        
        # Render the total hours for both out-of-band swaps (header badge and legacy display)
        total_hours = build_list.items.aggregate(total=Sum('hour_qty'))['total'] or 0
        
        # Out-of-band swap for the hours badge in the header
        oob_hours_badge = f'<span class="build-list-hours-badge" id="total-hours-display" hx-swap-oob="true">{total_hours} hrs</span>'
        
        # Combine both
        combined_html = items_html + oob_hours_badge
        
        response = HttpResponse(combined_html)
        response['HX-Trigger'] = 'clearItemForm'
        return response
    
    # Return form with errors - render the modal again with errors
    context = {
        'build_list': build_list,
        'item': item,
        'form': form,
    }
    return render(request, 'inventory/partials/build_list_item_edit_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def build_list_item_delete(request, build_list_id, item_id):
    """POST: Delete item."""
    from django.db.models import Sum
    from django.template.loader import render_to_string
    
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    item = get_object_or_404(BuildListItem, pk=item_id, build_list=build_list)
    item.delete()
    messages.success(request, "Item deleted.")
    
    # Render the items table
    items = build_list.items.all()
    items_html = render_to_string('inventory/partials/_build_list_items.html', {
        'build_list': build_list,
        'items': items,
    }, request=request)
    
    # Render the total hours for out-of-band swap (header badge)
    total_hours = build_list.items.aggregate(total=Sum('hour_qty'))['total'] or 0
    
    # Out-of-band swap for the hours badge in the header
    oob_hours_badge = f'<span class="build-list-hours-badge" id="total-hours-display" hx-swap-oob="true">{total_hours} hrs</span>'
    
    # Combine both
    combined_html = items_html + oob_hours_badge
    
    return HttpResponse(combined_html)


# Engine Assignments from Build List side (HTMX)

@login_required
def build_list_engines_partial(request, build_list_id):
    """HTMX partial for engines using this build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    engines = build_list.engines.all()
    
    context = {
        'build_list': build_list,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/_build_list_engines.html', context)


@login_required
def engine_search_modal_for_build_list(request, build_list_id):
    """HTMX modal to search and add engines."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    
    # Get engines not already assigned
    assigned_engine_ids = build_list.engines.values_list('id', flat=True)
    engines = Engine.objects.exclude(id__in=assigned_engine_ids).select_related('sg_engine').order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'build_list': build_list,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_search_modal_for_build_list.html', context)


@login_required
def engine_search_results_for_build_list(request, build_list_id):
    """HTMX search results for engines."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    query = request.GET.get('q', '').strip()
    
    # Get engines not already assigned
    assigned_engine_ids = build_list.engines.values_list('id', flat=True)
    engines = Engine.objects.exclude(id__in=assigned_engine_ids).select_related('sg_engine')
    
    if query:
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(status__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query)
        )
    
    engines = engines.order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'build_list': build_list,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_search_results_for_build_list.html', context)


@login_required
@require_http_methods(["POST"])
def build_list_engine_add(request, build_list_id):
    """POST: Assign engine to build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    engine_id = request.POST.get('engine_id')
    
    if engine_id:
        engine = get_object_or_404(Engine, pk=engine_id)
        build_list.engines.add(engine)
        messages.success(request, f"Added {engine} to build list.")
    
    # Re-render engines partial
    return build_list_engines_partial(request, build_list_id)


@login_required
@require_http_methods(["POST"])
def build_list_engine_remove(request, build_list_id, engine_id):
    """POST: Remove engine from build list."""
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    engine = get_object_or_404(Engine, pk=engine_id)
    build_list.engines.remove(engine)
    messages.success(request, f"Removed {engine} from build list.")
    
    # Re-render engines partial
    return build_list_engines_partial(request, build_list_id)


# Build Lists on Engine side (HTMX)

@login_required
def engine_build_lists_partial(request, engine_id):
    """HTMX partial showing build lists assigned to this engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    build_lists = engine.build_lists.all()
    
    context = {
        'engine': engine,
        'build_lists': build_lists,
    }
    
    return render(request, 'inventory/partials/_engine_build_lists.html', context)


@login_required
def engine_build_list_add_form(request, engine_id):
    """HTMX form to add build list to engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Get all build lists not already assigned
    assigned_bl_ids = engine.build_lists.values_list('id', flat=True)
    available_build_lists = BuildList.objects.exclude(id__in=assigned_bl_ids).order_by('name')
    
    context = {
        'engine': engine,
        'available_build_lists': available_build_lists,
    }
    
    return render(request, 'inventory/partials/_engine_build_list_add_form.html', context)


@login_required
@require_http_methods(["POST"])
def engine_build_list_add(request, engine_id):
    """POST: Assign build list to engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    build_list_id = request.POST.get('build_list_id')
    
    if build_list_id:
        build_list = get_object_or_404(BuildList, pk=build_list_id)
        engine.build_lists.add(build_list)
        messages.success(request, f"Added {build_list.name} to engine.")
    
    # Re-render build lists partial and clear form
    response = engine_build_lists_partial(request, engine_id)
    response['HX-Trigger'] = 'clearEngineBuildListForm'
    return response


@login_required
@require_http_methods(["POST"])
def engine_build_list_remove(request, engine_id, build_list_id):
    """POST: Remove build list from engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    build_list = get_object_or_404(BuildList, pk=build_list_id)
    engine.build_lists.remove(build_list)
    messages.success(request, f"Removed {build_list.name} from engine.")
    
    # Re-render build lists partial
    return engine_build_lists_partial(request, engine_id)


# ---------- Kit Views ----------

@login_required
def kits_list(request):
    """Display list of kits with search and sorting."""
    from django.db.models import Count
    from decimal import Decimal
    from core.view_utils import get_list_context
    
    # Base queryset with annotations
    kits = Kit.objects.annotate(
        engines_count=Count('engines'),
        parts_count=Count('items')
    ).prefetch_related('items__part__primary_vendor', 'items__part__vendor_links').all()
    
    # Get list context with search, sort, and pagination
    context = get_list_context(
        queryset=kits,
        request=request,
        search_fields=['name', 'notes'],
        sort_fields={
            'name', '-name', 'engines_count', '-engines_count',
            'parts_count', '-parts_count', 'created_at', '-created_at'
        },
        default_sort=['name'],
        per_page=200
    )
    
    # Calculate total cost for each kit (kit-specific logic)
    for kit in context['object_list']:
        total_cost = Decimal('0.00')
        for item in kit.items.all():
            if item.part.primary_vendor:
                try:
                    part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                    if part_vendor.cost:
                        total_cost += part_vendor.cost * item.quantity
                except:
                    pass
        kit.total_cost = total_cost
    
    # Add kits to context for template compatibility
    context['kits'] = context['object_list']
    
    return render(request, 'inventory/kits_list.html', context)


@login_required
def kit_detail(request, kit_id):
    """Display kit edit page (unified view/edit page)."""
    from decimal import Decimal
    
    kit = get_object_or_404(Kit, pk=kit_id)
    form = KitForm(instance=kit)
    
    # Calculate total cost from primary vendor prices
    total_cost = Decimal('0.00')
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    
    for item in items:
        if item.part.primary_vendor:
            # Get the cost from PartVendor relationship
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                if part_vendor.cost:
                    total_cost += part_vendor.cost * item.quantity
            except:
                pass
    
    context = {
        'kit': kit,
        'form': form,
        'total_cost': total_cost,
        'item_count': kit.items.count(),
        'engine_count': kit.engines.count(),
        'is_new': False,
    }
    
    return render(request, 'inventory/kit_edit.html', context)


@login_required
@require_http_methods(["POST"])
def kit_update(request, kit_id):
    """Handle kit form submission."""
    kit = get_object_or_404(Kit, pk=kit_id)
    form = KitForm(request.POST, instance=kit)
    
    if form.is_valid():
        form.save()
        return redirect("inventory:kits_list")
    
    # If form is invalid, re-render the edit page with errors
    from decimal import Decimal
    
    total_cost = Decimal('0.00')
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    
    for item in items:
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                if part_vendor.cost:
                    total_cost += part_vendor.cost * item.quantity
            except:
                pass
    
    context = {
        'kit': kit,
        'form': form,
        'total_cost': total_cost,
        'item_count': kit.items.count(),
        'engine_count': kit.engines.count(),
        'is_new': False,
    }
    
    return render(request, 'inventory/kit_edit.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def kit_create(request):
    """Create new kit (uses same template as edit)."""
    form = KitForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            kit = form.save(commit=False)
            if request.user.is_authenticated:
                kit.created_by = request.user
            kit.save()
            return redirect("inventory:kit_detail", kit_id=kit.id)
    
    return render(request, 'inventory/kit_edit.html', {
        'form': form,
        'kit': None,
        'is_new': True,
        'total_cost': 0,
        'item_count': 0,
        'engine_count': 0,
    })


@login_required
def kit_create_modal(request):
    """HTMX endpoint to show/handle kit creation modal."""
    if request.method == "POST":
        form = KitForm(request.POST)
        if form.is_valid():
            kit = form.save(commit=False)
            if request.user.is_authenticated:
                kit.created_by = request.user
            kit.save()
            
            # Return a script that closes the modal and reloads the page
            return HttpResponse(
                '<script>document.body.dispatchEvent(new Event("kitCreated")); window.location.href = "/inventory/kits/";</script>',
                content_type='text/html'
            )
        else:
            # Re-render the modal with errors
            return render(request, 'inventory/modals/kit_create_modal.html', {
                'form': form,
            })
    else:
        # GET request - show empty form
        form = KitForm()
        return render(request, 'inventory/modals/kit_create_modal.html', {
            'form': form,
        })


@login_required
def kit_edit(request, kit_id):
    """Redirect to kit detail page (which is now the unified edit page)."""
    return redirect("inventory:kit_detail", kit_id=kit_id)


@login_required
@require_http_methods(["POST"])
def kit_delete(request, kit_id):
    """Delete kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    kit.delete()
    messages.success(request, "Kit deleted.")
    return redirect("inventory:kits_list")


# Kit Items (HTMX)

@login_required
def kit_items_partial(request, kit_id):
    """HTMX partial for kit items table."""
    kit = get_object_or_404(Kit, pk=kit_id)
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    
    # Attach primary vendor price to each item
    for item in items:
        # Auto-set primary vendor if needed (opportunistic fix)
        if not item.part.primary_vendor:
            item.part.auto_set_primary_vendor()
            # Refresh the part to get the updated primary_vendor
            item.part.refresh_from_db()
        
        item.primary_vendor_price = None
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                item.primary_vendor_price = part_vendor.cost
            except:
                pass
    
    context = {
        'kit': kit,
        'items': items,
    }
    
    return render(request, 'inventory/partials/_kit_items.html', context)


@login_required
def kit_total_cost_partial(request, kit_id):
    """HTMX partial for total cost display."""
    from decimal import Decimal
    
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Calculate total cost from primary vendor prices
    total_cost = Decimal('0.00')
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    
    for item in items:
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                if part_vendor.cost:
                    total_cost += part_vendor.cost * item.quantity
            except:
                pass
    
    context = {
        'total_cost': total_cost,
    }
    
    return render(request, 'inventory/partials/_kit_total_cost.html', context)


@login_required
def kit_items_popover(request, kit_id):
    """HTMX partial for kit items popover preview."""
    kit = get_object_or_404(Kit, pk=kit_id)
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    
    # Attach primary vendor cost to each item
    for item in items:
        # Auto-set primary vendor if needed (opportunistic fix)
        if not item.part.primary_vendor:
            item.part.auto_set_primary_vendor()
            # Refresh the part to get the updated primary_vendor
            item.part.refresh_from_db()
        
        item.primary_vendor_cost = None
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                item.primary_vendor_cost = part_vendor.cost
            except:
                pass
    
    context = {
        'kit': kit,
        'items': items,
    }
    
    return render(request, 'inventory/partials/_kit_items_popover.html', context)


@login_required
def part_search_modal_for_kit(request, kit_id):
    """HTMX modal to search and add parts."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Get parts not already in kit
    existing_part_ids = kit.items.values_list('part_id', flat=True)
    parts = Part.objects.exclude(id__in=existing_part_ids).select_related('category', 'primary_vendor').order_by('part_number')[:50]
    
    context = {
        'kit': kit,
        'parts': parts,
    }
    
    return render(request, 'inventory/partials/part_search_modal_for_kit.html', context)


@login_required
def part_search_results_for_kit(request, kit_id):
    """HTMX search results for parts."""
    kit = get_object_or_404(Kit, pk=kit_id)
    query = request.GET.get('q', '').strip()
    
    # Get parts not already in kit
    existing_part_ids = kit.items.values_list('part_id', flat=True)
    parts = Part.objects.exclude(id__in=existing_part_ids).select_related('category', 'primary_vendor')
    
    if query:
        parts = parts.filter(
            Q(part_number__icontains=query) |
            Q(name__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    parts = parts.order_by('part_number')[:50]
    
    context = {
        'kit': kit,
        'parts': parts,
    }
    
    return render(request, 'inventory/partials/part_search_results_for_kit.html', context)


@login_required
def part_details_form_for_kit(request, kit_id):
    """HTMX modal for entering part details."""
    kit = get_object_or_404(Kit, pk=kit_id)
    part_id = request.GET.get('part_id')
    part = get_object_or_404(Part, pk=part_id)
    
    context = {
        'kit': kit,
        'part': part,
    }
    
    return render(request, 'inventory/partials/part_details_form_for_kit.html', context)


@login_required
@require_http_methods(["POST"])
def kit_item_add(request, kit_id):
    """POST: Create item."""
    from decimal import Decimal
    from django.template.loader import render_to_string
    
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Get data from POST
    part_id = request.POST.get('part_id')
    quantity = request.POST.get('quantity', 1)
    notes = request.POST.get('notes', '')
    
    if part_id:
        part = get_object_or_404(Part, pk=part_id)
        KitItem.objects.create(
            kit=kit,
            part=part,
            quantity=quantity,
            notes=notes
        )
        messages.success(request, "Part added to kit.")
    
    # Render the items table
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    item_count = items.count()
    
    # Attach primary vendor price to each item
    for item in items:
        if not item.part.primary_vendor:
            item.part.auto_set_primary_vendor()
            item.part.refresh_from_db()
        
        item.primary_vendor_price = None
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                item.primary_vendor_price = part_vendor.cost
            except:
                pass
    
    items_html = render_to_string('inventory/partials/_kit_items.html', {
        'kit': kit,
        'items': items,
    }, request=request)
    
    # Calculate total cost
    total_cost = Decimal('0.00')
    for item in items:
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                if part_vendor.cost:
                    total_cost += part_vendor.cost * item.quantity
            except:
                pass
    
    total_cost_html = render_to_string('inventory/partials/_kit_total_cost.html', {
        'total_cost': total_cost,
    }, request=request)
    
    # Combine with out-of-band swaps for total cost, header badge, and item count
    combined_html = items_html
    combined_html += f'<span id="total-cost-display" hx-swap-oob="true">{total_cost_html}</span>'
    combined_html += f'<span id="header-total-cost" class="kit-cost-badge" hx-swap-oob="true">{total_cost_html}</span>'
    combined_html += f'<span id="header-item-count" class="kit-items-badge" hx-swap-oob="true">{item_count} Part{"s" if item_count != 1 else ""}</span>'
    
    return HttpResponse(combined_html)


@login_required
def kit_item_edit_modal(request, kit_id, item_id):
    """HTMX modal to edit item."""
    kit = get_object_or_404(Kit, pk=kit_id)
    item = get_object_or_404(KitItem, pk=item_id, kit=kit)
    
    context = {
        'kit': kit,
        'item': item,
    }
    
    return render(request, 'inventory/partials/kit_item_edit_modal.html', context)


@login_required
@require_http_methods(["POST"])
def kit_item_edit(request, kit_id, item_id):
    """POST: Update item."""
    from decimal import Decimal
    from django.template.loader import render_to_string
    
    kit = get_object_or_404(Kit, pk=kit_id)
    item = get_object_or_404(KitItem, pk=item_id, kit=kit)
    
    # Get data from POST
    quantity = request.POST.get('quantity', item.quantity)
    notes = request.POST.get('notes', '')
    
    item.quantity = quantity
    item.notes = notes
    item.save()
    messages.success(request, "Kit item updated.")
    
    # Render the items table
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    item_count = items.count()
    
    # Attach primary vendor price to each item
    for item in items:
        if not item.part.primary_vendor:
            item.part.auto_set_primary_vendor()
            item.part.refresh_from_db()
        
        item.primary_vendor_price = None
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                item.primary_vendor_price = part_vendor.cost
            except:
                pass
    
    items_html = render_to_string('inventory/partials/_kit_items.html', {
        'kit': kit,
        'items': items,
    }, request=request)
    
    # Calculate total cost
    total_cost = Decimal('0.00')
    for item in items:
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                if part_vendor.cost:
                    total_cost += part_vendor.cost * item.quantity
            except:
                pass
    
    total_cost_html = render_to_string('inventory/partials/_kit_total_cost.html', {
        'total_cost': total_cost,
    }, request=request)
    
    # Combine with out-of-band swaps for total cost and header badge
    combined_html = items_html
    combined_html += f'<span id="total-cost-display" hx-swap-oob="true">{total_cost_html}</span>'
    combined_html += f'<span id="header-total-cost" class="kit-cost-badge" hx-swap-oob="true">{total_cost_html}</span>'
    
    return HttpResponse(combined_html)


@login_required
@require_http_methods(["POST"])
def kit_item_delete(request, kit_id, item_id):
    """POST: Delete item."""
    from decimal import Decimal
    from django.template.loader import render_to_string
    
    kit = get_object_or_404(Kit, pk=kit_id)
    item = get_object_or_404(KitItem, pk=item_id, kit=kit)
    item.delete()
    messages.success(request, "Part removed from kit.")
    
    # Render the items table
    items = kit.items.select_related('part__primary_vendor').prefetch_related('part__vendor_links').all()
    item_count = items.count()
    
    # Attach primary vendor price to each item
    for item in items:
        if not item.part.primary_vendor:
            item.part.auto_set_primary_vendor()
            item.part.refresh_from_db()
        
        item.primary_vendor_price = None
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                item.primary_vendor_price = part_vendor.cost
            except:
                pass
    
    items_html = render_to_string('inventory/partials/_kit_items.html', {
        'kit': kit,
        'items': items,
    }, request=request)
    
    # Calculate total cost
    total_cost = Decimal('0.00')
    for item in items:
        if item.part.primary_vendor:
            try:
                part_vendor = item.part.vendor_links.get(vendor=item.part.primary_vendor)
                if part_vendor.cost:
                    total_cost += part_vendor.cost * item.quantity
            except:
                pass
    
    total_cost_html = render_to_string('inventory/partials/_kit_total_cost.html', {
        'total_cost': total_cost,
    }, request=request)
    
    # Combine with out-of-band swaps for total cost, header badge, and item count
    combined_html = items_html
    combined_html += f'<span id="total-cost-display" hx-swap-oob="true">{total_cost_html}</span>'
    combined_html += f'<span id="header-total-cost" class="kit-cost-badge" hx-swap-oob="true">{total_cost_html}</span>'
    combined_html += f'<span id="header-item-count" class="kit-items-badge" hx-swap-oob="true">{item_count} Part{"s" if item_count != 1 else ""}</span>'
    
    return HttpResponse(combined_html)


# Engine Assignments from Kit side (HTMX)

@login_required
def kit_engines_partial(request, kit_id):
    """HTMX partial for engines using this kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    engines = kit.engines.all()
    
    context = {
        'kit': kit,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/_kit_engines.html', context)


@login_required
def engine_search_modal_for_kit(request, kit_id):
    """HTMX modal to search and add engines."""
    kit = get_object_or_404(Kit, pk=kit_id)
    
    # Get engines not already assigned
    assigned_engine_ids = kit.engines.values_list('id', flat=True)
    engines = Engine.objects.exclude(id__in=assigned_engine_ids).select_related('sg_engine').order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'kit': kit,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_search_modal_for_kit.html', context)


@login_required
def engine_search_results_for_kit(request, kit_id):
    """HTMX search results for engines."""
    kit = get_object_or_404(Kit, pk=kit_id)
    query = request.GET.get('q', '').strip()
    
    # Get engines not already assigned
    assigned_engine_ids = kit.engines.values_list('id', flat=True)
    engines = Engine.objects.exclude(id__in=assigned_engine_ids).select_related('sg_engine')
    
    if query:
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(status__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query)
        )
    
    engines = engines.order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'kit': kit,
        'engines': engines,
    }
    
    return render(request, 'inventory/partials/engine_search_results_for_kit.html', context)


@login_required
@require_http_methods(["POST"])
def kit_engine_add(request, kit_id):
    """POST: Assign engine to kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    engine_id = request.POST.get('engine_id')
    
    if engine_id:
        engine = get_object_or_404(Engine, pk=engine_id)
        kit.engines.add(engine)
        messages.success(request, f"Added {engine} to kit.")
    
    # Re-render engines partial
    return kit_engines_partial(request, kit_id)


@login_required
@require_http_methods(["POST"])
def kit_engine_remove(request, kit_id, engine_id):
    """POST: Remove engine from kit."""
    kit = get_object_or_404(Kit, pk=kit_id)
    engine = get_object_or_404(Engine, pk=engine_id)
    kit.engines.remove(engine)
    messages.success(request, f"Removed {engine} from kit.")
    
    # Re-render engines partial
    return kit_engines_partial(request, kit_id)


# Kits on Engine side (HTMX)

@login_required
def engine_kits_partial(request, engine_id):
    """HTMX partial showing kits assigned to this engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    kits = engine.kits.all()
    
    context = {
        'engine': engine,
        'kits': kits,
    }
    
    return render(request, 'inventory/partials/_engine_kits.html', context)


@login_required
def engine_kit_add_form(request, engine_id):
    """HTMX form to add kit to engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    # Get all kits not already assigned
    assigned_kit_ids = engine.kits.values_list('id', flat=True)
    available_kits = Kit.objects.exclude(id__in=assigned_kit_ids).order_by('name')
    
    context = {
        'engine': engine,
        'available_kits': available_kits,
    }
    
    return render(request, 'inventory/partials/_engine_kit_add_form.html', context)


@login_required
@require_http_methods(["POST"])
def engine_kit_add(request, engine_id):
    """POST: Assign kit to engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    kit_id = request.POST.get('kit_id')
    
    if kit_id:
        kit = get_object_or_404(Kit, pk=kit_id)
        engine.kits.add(kit)
        messages.success(request, f"Added {kit.name} to engine.")
    
    # Re-render kits partial and clear form
    response = engine_kits_partial(request, engine_id)
    response['HX-Trigger'] = 'clearEngineKitForm'
    return response


@login_required
@require_http_methods(["POST"])
def engine_kit_remove(request, engine_id, kit_id):
    """POST: Remove kit from engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    kit = get_object_or_404(Kit, pk=kit_id)
    engine.kits.remove(kit)
    messages.success(request, f"Removed {kit.name} from engine.")
    
    # Re-render kits partial
    return engine_kits_partial(request, engine_id)


# ---------- Search Modal Views (Engine) ----------

@login_required
def engine_search_modal_interchange(request, engine_id):
    """Search modal for adding interchange engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    # Get already linked engines to exclude
    linked_engine_ids = list(engine.interchanges.values_list('id', flat=True))
    linked_engine_ids.append(engine.id)  # Exclude self
    
    engines = Engine.objects.exclude(id__in=linked_engine_ids).select_related('sg_engine').order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'parent_engine': engine,
        'engines': engines,
        'query': '',
    }
    return render(request, 'inventory/partials/engine_search_modal_interchange.html', context)


@login_required
def engine_search_results_interchange(request, engine_id):
    """Search results for interchange engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    # Get already linked engines to exclude
    linked_engine_ids = list(engine.interchanges.values_list('id', flat=True))
    linked_engine_ids.append(engine.id)  # Exclude self
    
    engines = Engine.objects.exclude(id__in=linked_engine_ids).select_related('sg_engine')
    
    if query:
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(identifier__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query) |
            Q(sg_engine__identifier__icontains=query)
        )
    
    engines = engines.order_by('engine_make', 'engine_model')[:100]
    
    context = {
        'parent_engine': engine,
        'engines': engines,
        'query': query,
    }
    return render(request, 'inventory/partials/engine_search_results_interchange.html', context)


@login_required
def engine_search_modal_compatible(request, engine_id):
    """Search modal for adding compatible engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    # Get already linked engines to exclude
    linked_engine_ids = list(engine.compatibles.values_list('id', flat=True))
    linked_engine_ids.append(engine.id)  # Exclude self
    
    engines = Engine.objects.exclude(id__in=linked_engine_ids).select_related('sg_engine').order_by('engine_make', 'engine_model')[:50]
    
    context = {
        'parent_engine': engine,
        'engines': engines,
        'query': '',
    }
    return render(request, 'inventory/partials/engine_search_modal_compatible.html', context)


@login_required
def engine_search_results_compatible(request, engine_id):
    """Search results for compatible engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    # Get already linked engines to exclude
    linked_engine_ids = list(engine.compatibles.values_list('id', flat=True))
    linked_engine_ids.append(engine.id)  # Exclude self
    
    engines = Engine.objects.exclude(id__in=linked_engine_ids).select_related('sg_engine')
    
    if query:
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(identifier__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query) |
            Q(sg_engine__identifier__icontains=query)
        )
    
    engines = engines.order_by('engine_make', 'engine_model')[:100]
    
    context = {
        'parent_engine': engine,
        'engines': engines,
        'query': query,
    }
    return render(request, 'inventory/partials/engine_search_results_compatible.html', context)


@login_required
def engine_search_modal_supercession(request, engine_id, direction):
    """Search modal for adding supercession engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    
    if direction == 'older':
        linked_engine_ids = list(engine.supersedes.values_list('id', flat=True))
        template = 'inventory/partials/engine_search_modal_supercession_older.html'
    else:
        linked_engine_ids = list(engine.superseded_by.values_list('id', flat=True))
        template = 'inventory/partials/engine_search_modal_supercession_newer.html'
    
    linked_engine_ids.append(engine.id)
    
    engines = (Engine.objects
               .exclude(id__in=linked_engine_ids)
               .select_related('sg_engine')
               .order_by('engine_make', 'engine_model')[:50])
    
    context = {
        'parent_engine': engine,
        'engines': engines,
        'query': '',
    }
    return render(request, template, context)


@login_required
def engine_search_results_supercession(request, engine_id, direction):
    """Search results for supercession engines."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    if direction == 'older':
        linked_engine_ids = list(engine.supersedes.values_list('id', flat=True))
        template = 'inventory/partials/engine_search_results_supercession_older.html'
    else:
        linked_engine_ids = list(engine.superseded_by.values_list('id', flat=True))
        template = 'inventory/partials/engine_search_results_supercession_newer.html'
    
    linked_engine_ids.append(engine.id)
    
    engines = Engine.objects.exclude(id__in=linked_engine_ids).select_related('sg_engine')
    
    if query:
        engines = engines.filter(
            Q(engine_make__icontains=query) |
            Q(engine_model__icontains=query) |
            Q(identifier__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(sg_engine__sg_make__icontains=query) |
            Q(sg_engine__sg_model__icontains=query) |
            Q(sg_engine__identifier__icontains=query)
        )
    
    engines = engines.order_by('engine_make', 'engine_model')[:100]
    
    context = {
        'parent_engine': engine,
        'engines': engines,
        'query': query,
    }
    return render(request, template, context)


@login_required
def build_list_search_modal(request, engine_id):
    """Search modal for adding build lists to engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    # Get build lists not already assigned
    assigned_bl_ids = engine.build_lists.values_list('id', flat=True)
    build_lists = BuildList.objects.exclude(id__in=assigned_bl_ids).order_by('name')[:50]
    
    context = {
        'engine': engine,
        'build_lists': build_lists,
        'query': '',
    }
    return render(request, 'inventory/partials/build_list_search_modal.html', context)


@login_required
def build_list_search_results(request, engine_id):
    """Search results for build lists."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    # Get build lists not already assigned
    assigned_bl_ids = engine.build_lists.values_list('id', flat=True)
    build_lists = BuildList.objects.exclude(id__in=assigned_bl_ids)
    
    if query:
        build_lists = build_lists.filter(
            Q(name__icontains=query) |
            Q(notes__icontains=query)
        )
    
    build_lists = build_lists.order_by('name')[:50]
    
    context = {
        'engine': engine,
        'build_lists': build_lists,
        'query': query,
    }
    return render(request, 'inventory/partials/build_list_search_results.html', context)


@login_required
def kit_search_modal(request, engine_id):
    """Search modal for adding kits to engine."""
    engine = get_object_or_404(Engine, pk=engine_id)
    # Get kits not already assigned
    assigned_kit_ids = engine.kits.values_list('id', flat=True)
    kits = Kit.objects.exclude(id__in=assigned_kit_ids).order_by('name')[:50]
    
    context = {
        'engine': engine,
        'kits': kits,
        'query': '',
    }
    return render(request, 'inventory/partials/kit_search_modal.html', context)


@login_required
def kit_search_results(request, engine_id):
    """Search results for kits."""
    engine = get_object_or_404(Engine, pk=engine_id)
    query = request.GET.get('q', '').strip()
    
    # Get kits not already assigned
    assigned_kit_ids = engine.kits.values_list('id', flat=True)
    kits = Kit.objects.exclude(id__in=assigned_kit_ids)
    
    if query:
        kits = kits.filter(
            Q(name__icontains=query) |
            Q(notes__icontains=query)
        )
    
    kits = kits.order_by('name')[:50]
    
    context = {
        'engine': engine,
        'kits': kits,
        'query': query,
    }
    return render(request, 'inventory/partials/kit_search_results.html', context)


# ---------- Casting Views (Engine-side) ----------

@login_required
def engine_castings_partial(request, engine_id):
    """HTMX partial for engine castings table."""
    engine = get_object_or_404(Engine, pk=engine_id)
    castings = engine.castings.all()
    
    context = {
        'engine': engine,
        'castings': castings,
    }
    
    return render(request, 'inventory/partials/_engine_castings.html', context)


@login_required
def engine_casting_add_form(request, engine_id):
    """HTMX form to add casting."""
    engine = get_object_or_404(Engine, pk=engine_id)
    form = CastingForm()
    
    context = {
        'engine': engine,
        'form': form,
    }
    
    return render(request, 'inventory/partials/_engine_casting_add_form.html', context)


@login_required
@require_http_methods(["POST"])
def engine_casting_add(request, engine_id):
    """POST: Create casting."""
    engine = get_object_or_404(Engine, pk=engine_id)
    form = CastingForm(request.POST)
    
    if form.is_valid():
        casting = form.save(commit=False)
        casting.engine = engine
        casting.save()
        
        # Refresh the castings table
        return engine_castings_partial(request, engine_id)
    
    # Return form with errors
    context = {
        'engine': engine,
        'form': form,
    }
    return render(request, 'inventory/partials/_engine_casting_add_form.html', context, status=400)


@login_required
def engine_casting_edit_form(request, engine_id, casting_id):
    """HTMX form to edit casting."""
    engine = get_object_or_404(Engine, pk=engine_id)
    casting = get_object_or_404(Casting, pk=casting_id, engine=engine)
    form = CastingForm(instance=casting)
    
    context = {
        'engine': engine,
        'casting': casting,
        'form': form,
    }
    
    return render(request, 'inventory/partials/_engine_casting_edit_form.html', context)


@login_required
@require_http_methods(["POST"])
def engine_casting_edit(request, engine_id, casting_id):
    """POST: Update casting."""
    engine = get_object_or_404(Engine, pk=engine_id)
    casting = get_object_or_404(Casting, pk=casting_id, engine=engine)
    form = CastingForm(request.POST, instance=casting)
    
    if form.is_valid():
        form.save()
        
        # Refresh the castings table
        return engine_castings_partial(request, engine_id)
    
    # Return form with errors
    context = {
        'engine': engine,
        'casting': casting,
        'form': form,
    }
    return render(request, 'inventory/partials/_engine_casting_edit_form.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def engine_casting_delete(request, engine_id, casting_id):
    """POST: Delete casting."""
    engine = get_object_or_404(Engine, pk=engine_id)
    casting = get_object_or_404(Casting, pk=casting_id, engine=engine)
    casting.delete()
    
    # Re-render castings partial
    return engine_castings_partial(request, engine_id)


# ---------- Vendor Views ----------

@login_required
def vendor_index(request):
    """Display a list of vendors with filtering, sorting, and pagination."""
    vendors = Vendor.objects.prefetch_related('contacts').all()
    
    # Apply filters
    search_filter = request.GET.get('search', '').strip()
    
    if search_filter:
        vendors = vendors.filter(
            Q(name__icontains=search_filter) |
            Q(contact_name__icontains=search_filter) |
            Q(email__icontains=search_filter) |
            Q(phone__icontains=search_filter) |
            Q(contacts__full_name__icontains=search_filter) |
            Q(contacts__email__icontains=search_filter) |
            Q(contacts__phone__icontains=search_filter)
        ).distinct()
    
    # Apply multi-column sorting (comma-separated fields like "name,-created_at")
    sort = request.GET.get('sort', 'name')
    valid_sort_fields = ['name', '-name', 'contact_name', '-contact_name', 
                         'email', '-email', 'phone', '-phone', 
                         'created_at', '-created_at']
    
    if sort:
        sort_fields = [s.strip() for s in sort.split(',') if s.strip()]
        # Filter to only valid sort fields
        sort_fields = [f for f in sort_fields if f in valid_sort_fields]
        if sort_fields:
            vendors = vendors.order_by(*sort_fields)
        else:
            vendors = vendors.order_by('name')
    else:
        vendors = vendors.order_by('name')
    
    # Pagination
    paginator = Paginator(vendors, 50)  # Reduced from 200 for better UX
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'vendors': page_obj.object_list,
        'total_count': paginator.count,
        'sort': sort,
        'current_filters': {
            'search': search_filter,
        },
    }
    
    return render(request, "inventory/vendors/index.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def vendor_create(request):
    """Create a new vendor."""
    form = VendorForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            vendor = form.save()
            return redirect("inventory:vendor_detail", vendor_id=vendor.id)
    
    return render(request, "inventory/vendors/edit.html", {
        "form": form,
        "vendor": None,
        "is_new": True,
        "parts_count": 0,
    })


@login_required
@require_http_methods(["GET", "POST"])
def vendor_edit(request, vendor_id):
    """Edit an existing vendor (combined view/edit page)."""
    vendor = get_object_or_404(Vendor.objects.prefetch_related('contacts'), pk=vendor_id)
    form = VendorForm(request.POST or None, instance=vendor)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("inventory:vendor_detail", vendor_id=vendor.id)
    
    # Get parts count
    parts_count = PartVendor.objects.filter(vendor=vendor).count()
    
    return render(request, "inventory/vendors/edit.html", {
        "form": form,
        "vendor": vendor, 
        "is_new": False,
        "parts_count": parts_count,
    })


@login_required
@require_http_methods(["POST"])
@login_required
def vendor_delete(request, vendor_id):
    """Delete a vendor."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    vendor.delete()
    messages.success(request, "Vendor deleted.")
    return redirect("inventory:vendor_index")


@login_required
@require_http_methods(["GET", "POST"])
def vendor_contact_create(request, vendor_id):
    """Create a new contact for a vendor."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    form = VendorContactForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            contact = form.save(commit=False)
            contact.vendor = vendor
            contact.save()
            messages.success(request, "Contact created.")
            return redirect("inventory:vendor_edit", vendor_id=vendor.id)
    
    return render(request, "inventory/vendors/contact_form.html", {
        "form": form,
        "vendor": vendor,
        "is_create": True
    })


@login_required
@require_http_methods(["GET", "POST"])
def vendor_contact_edit(request, vendor_id, contact_id):
    """Edit an existing contact for a vendor."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    contact = get_object_or_404(VendorContact, pk=contact_id, vendor=vendor)
    form = VendorContactForm(request.POST or None, instance=contact)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Contact updated.")
            return redirect("inventory:vendor_edit", vendor_id=vendor.id)
    
    return render(request, "inventory/vendors/contact_form.html", {
        "form": form,
        "vendor": vendor,
        "contact": contact,
        "is_create": False
    })


@login_required
@require_http_methods(["GET"])
def vendor_contact_delete_confirm(request, vendor_id, contact_id):
    """Display confirmation page for deleting a contact."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    contact = get_object_or_404(VendorContact, pk=contact_id, vendor=vendor)
    
    return render(request, "inventory/vendors/contact_confirm_delete.html", {
        "vendor": vendor,
        "contact": contact
    })


@login_required
@require_http_methods(["POST"])
def vendor_contact_delete(request, vendor_id, contact_id):
    """Delete a contact from a vendor."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    contact = get_object_or_404(VendorContact, pk=contact_id, vendor=vendor)
    contact.delete()
    messages.success(request, "Contact deleted.")
    return redirect("inventory:vendor_edit", vendor_id=vendor.id)


@login_required
@require_http_methods(["POST"])
def vendor_contact_set_primary(request, vendor_id, contact_id):
    """Set a contact as the primary contact for a vendor."""
    vendor = get_object_or_404(Vendor.objects.prefetch_related('contacts'), pk=vendor_id)
    contact = get_object_or_404(VendorContact, pk=contact_id, vendor=vendor)
    
    # Update vendor's primary contact fields
    vendor.contact_name = contact.full_name
    vendor.email = contact.email
    vendor.phone = contact.phone
    vendor.save()
    
    # If HTMX request, return the contacts section partial
    if request.headers.get('HX-Request'):
        return render(request, "inventory/vendors/_contacts_section.html", {
            "vendor": vendor
        })
    
    messages.success(request, f"{contact.full_name} set as primary contact.")
    return redirect("inventory:vendor_edit", vendor_id=vendor.id)


@login_required
def vendor_detail(request, vendor_id):
    """Display vendor details (redirects to combined edit page)."""
    return redirect("inventory:vendor_edit", vendor_id=vendor_id)


@login_required
def vendor_contact_create_modal(request, vendor_id):
    """Render the contact creation modal."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    return render(request, "inventory/vendors/contact_create_modal.html", {
        "vendor": vendor
    })


@login_required
@require_http_methods(["POST"])
def vendor_contact_create_ajax(request, vendor_id):
    """Create a new contact for a vendor via AJAX."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    
    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    title = request.POST.get('title', '').strip()
    notes = request.POST.get('notes', '').strip()
    set_primary = request.POST.get('set_primary') == 'on'
    
    if full_name:
        contact = VendorContact.objects.create(
            vendor=vendor,
            full_name=full_name,
            email=email,
            phone=phone,
            title=title,
            notes=notes
        )
        
        # Set as primary if requested
        if set_primary:
            vendor.contact_name = contact.full_name
            vendor.email = contact.email
            vendor.phone = contact.phone
            vendor.save()
    
    return render(request, "inventory/vendors/_contacts_section.html", {
        "vendor": vendor
    })


@login_required
def vendor_contacts_partial(request, vendor_id):
    """Render the contacts section partial."""
    vendor = get_object_or_404(Vendor.objects.prefetch_related('contacts'), pk=vendor_id)
    return render(request, "inventory/vendors/_contacts_section.html", {
        "vendor": vendor
    })


@login_required
def vendor_part_add_modal(request, vendor_id):
    """Render the part add modal for a vendor."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    
    # Get search query if provided
    q = request.GET.get('q', '').strip()
    
    # Get parts that aren't already linked to this vendor
    linked_ids = list(PartVendor.objects.filter(vendor=vendor).values_list('part_id', flat=True))
    
    parts = Part.objects.exclude(id__in=linked_ids)
    if q:
        parts = parts.filter(
            Q(name__icontains=q) |
            Q(part_number__icontains=q) |
            Q(description__icontains=q)
        )
    parts = parts.order_by('name')[:50]
    
    return render(request, "inventory/vendors/part_add_modal.html", {
        "vendor": vendor,
        "parts": parts,
        "q": q,
        "linked_ids": linked_ids
    })


# ---------- Vendor detail: Parts supplied (HTMX partials) ----------

@login_required
def vendor_parts_partial(request, vendor_id):
    """HTMX endpoint to render vendor parts table."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    links = (PartVendor.objects
             .select_related("part", "vendor")
             .filter(vendor=vendor)
             .order_by("part__name", "part__part_number"))
    paginator = Paginator(links, 50)
    page = paginator.get_page(request.GET.get("page"))
    
    # Check if we should show the add form
    show_form = request.GET.get('show_form') == '1'
    form = None
    parts = []
    
    if show_form:
        # initial options (first page, no query)
        q = ""
        parts = Part.objects.order_by("name", "part_number")[:50]
        # mark which are already linked
        linked_ids = set(PartVendor.objects.filter(vendor=vendor).values_list("part_id", flat=True))
        form = None  # We don't need the form object for the new structure
    
    return render(request, "inventory/vendors/_parts_table.html", {
        "vendor": vendor, 
        "page": page, 
        "links": page.object_list, 
        "paginator": paginator,
        "show_form": show_form,
        "form": form,
        "parts": parts,
        "linked_ids": linked_ids if show_form else set(),
        "q": q if show_form else ""
    })


@login_required
@require_http_methods(["GET"])
@login_required
def vendor_part_add_form(request, vendor_id):
    """HTMX endpoint to render add part form."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    # initial options (first page, no query)
    q = ""
    parts = Part.objects.order_by("name", "part_number")[:50]
    # mark which are already linked
    linked_ids = set(PartVendor.objects.filter(vendor=vendor).values_list("part_id", flat=True))
    return render(request, "inventory/vendors/_part_add_form.html", {
        "vendor": vendor, "parts": parts, "q": q, "linked_ids": linked_ids,
    })


@login_required
@require_http_methods(["GET"])
@login_required
def vendor_part_options(request, vendor_id):
    """Return <option> list for the select based on q; include already-linked state."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    q = (request.GET.get("q") or "").strip()
    qs = Part.objects.all()
    if q:
        qs = qs.filter(Q(part_number__icontains=q) | Q(name__icontains=q))
    qs = qs.order_by("name", "part_number")[:100]
    linked_ids = set(PartVendor.objects.filter(vendor=vendor).values_list("part_id", flat=True))
    html = render_to_string("inventory/vendors/_part_options.html", {
        "parts": qs, "linked_ids": linked_ids,
    })
    return HttpResponse(html)


@login_required
@require_POST
@transaction.atomic
@login_required
def vendor_part_add(request, vendor_id):
    """Create or update Vendor↔Part link; never fails if already exists."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    part_id = request.POST.get("part_id")
    if not part_id:
        return vendor_parts_partial(request, vendor_id)

    link, created = PartVendor.objects.get_or_create(vendor=vendor, part_id=part_id)
    form = PartVendorForm(request.POST, instance=link)
    if form.is_valid():
        form.save()
        msg = "Part added to vendor." if created else "Existing vendor-part link updated."
        messages.success(request, msg)
        
        # Set as primary vendor if requested
        if request.POST.get('set_primary') == 'on':
            link.part.primary_vendor = vendor
            link.part.save()
        else:
            # Auto-set primary vendor if only one vendor exists
            link.part.auto_set_primary_vendor()
    else:
        messages.error(request, "Please fix the errors in the form.")

    return vendor_parts_partial(request, vendor_id)


@login_required
@require_http_methods(["GET"])
@login_required
def vendor_part_edit_form(request, vendor_id, link_id):
    """HTMX endpoint to render edit part form."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    link = get_object_or_404(PartVendor, pk=link_id, vendor=vendor)
    form = PartVendorForm(instance=link)
    return render(request, "inventory/vendors/_part_edit_form.html", {"vendor": vendor, "link": link, "form": form})


@login_required
def vendor_part_edit_modal(request, vendor_id, link_id):
    """Render the part edit modal."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    link = get_object_or_404(PartVendor.objects.select_related('part'), pk=link_id, vendor=vendor)
    return render(request, "inventory/vendors/part_edit_modal.html", {"vendor": vendor, "link": link})


@login_required
@require_POST
@login_required
def vendor_part_edit(request, vendor_id, link_id):
    """HTMX endpoint to edit a part vendor link."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    link = get_object_or_404(PartVendor, pk=link_id, vendor=vendor)
    
    # Update text fields (use empty string for NOT NULL fields)
    link.vendor_part_number = request.POST.get('vendor_part_number', '').strip()
    link.vendor_sku = request.POST.get('vendor_sku', '').strip()
    link.notes = request.POST.get('notes', '').strip()
    
    # Handle numeric fields (these can be NULL)
    price = request.POST.get('price', '').strip()
    link.price = float(price) if price else None
    
    cost = request.POST.get('cost', '').strip()
    link.cost = float(cost) if cost else None
    
    stock_qty = request.POST.get('stock_qty', '').strip()
    link.stock_qty = int(stock_qty) if stock_qty else None
    
    lead_time = request.POST.get('lead_time_days', '').strip()
    link.lead_time_days = int(lead_time) if lead_time else None
    
    link.save()
    messages.success(request, "Vendor part updated.")
    
    return vendor_parts_partial(request, vendor_id)


@login_required
@require_POST
@login_required
def vendor_part_remove(request, vendor_id, link_id):
    """HTMX endpoint to remove a part from a vendor."""
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    link = get_object_or_404(PartVendor, pk=link_id, vendor=vendor)
    part = link.part  # Save part reference before deleting
    link.delete()
    
    # Auto-set primary vendor if only one vendor exists
    part.auto_set_primary_vendor()
    
    messages.success(request, "Removed part from vendor.")
    return vendor_parts_partial(request, vendor_id)


# ---------- Set Primary Vendor for a Part ----------

@login_required
@require_POST
@transaction.atomic
@login_required
def part_set_primary_vendor(request, part_id, vendor_id):
    """Set a vendor as the primary vendor for a part."""
    part = get_object_or_404(Part, pk=part_id)
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    part.primary_vendor = vendor
    part.save(update_fields=["primary_vendor"])
    messages.success(request, f"Primary Vendor for {part.name} set to {vendor.name}.")
    # if request came from vendor detail: reload vendor parts partial if 'from_vendor' is present
    if request.headers.get("HX-Request"):
        from_vendor = request.POST.get("from_vendor") == "1"
        if from_vendor:
            return vendor_parts_partial(request, vendor_id)
    return redirect("inventory:part_edit", pk=part.id)


# Inline Editing API Endpoints

@login_required
@require_http_methods(["PATCH"])
def engine_field_update(request, engine_id):
    """Update a single field of an engine via AJAX."""
    import json
    
    try:
        engine = Engine.objects.get(pk=engine_id)
        data = json.loads(request.body)
        field_name = data.get('field')
        new_value = data.get('value', '').strip()
        
        # Define editable fields
        editable_fields = [
            'engine_make', 'engine_model', 'serial_number', 'identifier',
            'injection_type', 'valve_config', 'fuel_system_type',
            'cpl_number', 'status', 'price'
        ]
        
        if field_name not in editable_fields:
            return JsonResponse({'error': 'Field not editable'}, status=400)
        
        # Handle empty values
        if new_value == '':
            new_value = None
        
        # Special handling for price field
        if field_name == 'price':
            if new_value is not None:
                try:
                    new_value = Decimal(new_value)
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Invalid price format'}, status=400)
        
        # Set the field value
        setattr(engine, field_name, new_value)
        engine.save(update_fields=[field_name])
        
        # Format response value for display
        display_value = getattr(engine, field_name)
        if display_value is None or display_value == '':
            display_value = '—'
        elif field_name == 'price' and display_value != '—':
            display_value = f'${display_value}'
        
        return JsonResponse({
            'success': True,
            'value': str(display_value)
        })
        
    except Engine.DoesNotExist:
        return JsonResponse({'error': 'Engine not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PATCH"])
def machine_field_update(request, machine_id):
    """Update a single field of a machine via AJAX."""
    import json
    
    try:
        machine = Machine.objects.get(pk=machine_id)
        data = json.loads(request.body)
        field_name = data.get('field')
        new_value = data.get('value', '').strip()
        
        # Define editable fields
        editable_fields = [
            'make', 'model', 'year', 'machine_type', 'market_type'
        ]
        
        if field_name not in editable_fields:
            return JsonResponse({'error': 'Field not editable'}, status=400)
        
        # Handle empty values
        if new_value == '':
            new_value = None
        
        # Special handling for year field (integer)
        if field_name == 'year':
            if new_value is not None:
                try:
                    new_value = int(new_value)
                except ValueError:
                    return JsonResponse({'error': 'Invalid year format'}, status=400)
        
        # Set the field value
        setattr(machine, field_name, new_value)
        machine.save(update_fields=[field_name])
        
        # Format response value for display
        display_value = getattr(machine, field_name)
        if display_value is None or display_value == '':
            display_value = '—'
        
        return JsonResponse({
            'success': True,
            'value': str(display_value)
        })
        
    except Machine.DoesNotExist:
        return JsonResponse({'error': 'Machine not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PATCH"])
def part_field_update(request, part_id):
    """Update a single field of a part via AJAX."""
    import json
    
    try:
        part = Part.objects.get(pk=part_id)
        data = json.loads(request.body)
        field_name = data.get('field')
        new_value = data.get('value', '').strip()
        
        # Define editable fields
        editable_fields = [
            'part_number', 'name', 'manufacturer', 'unit', 'type'
        ]
        
        if field_name not in editable_fields:
            return JsonResponse({'error': 'Field not editable'}, status=400)
        
        # Handle empty values
        if new_value == '':
            new_value = None
        
        # Set the field value
        setattr(part, field_name, new_value)
        part.save(update_fields=[field_name])
        
        # Format response value for display
        display_value = getattr(part, field_name)
        if display_value is None or display_value == '':
            display_value = '—'
        
        return JsonResponse({
            'success': True,
            'value': str(display_value)
        })
        
    except Part.DoesNotExist:
        return JsonResponse({'error': 'Part not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
