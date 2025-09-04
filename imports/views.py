import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.urls import reverse
from django.db.models import Count, Q
from .models import ImportBatch, SavedImportMapping, ImportLog, ImportRow
from .forms import (
    ImportFileUploadForm, CSVOptionsForm, XLSXOptionsForm, 
    ImportMappingForm, AdditionalEngineMappingForm, SavedMappingForm, ProcessingOptionsForm
)
from .utils import (
    process_csv_file, process_xlsx_file, get_xlsx_worksheet_data,
    validate_file_limits, create_mapping_dict, get_expected_fields
)
from .tasks import process_import_batch
from inventory.models import PartAttribute, PartCategory

@login_required
def index(request):
    """Import management index page."""
    batches = ImportBatch.objects.all()
    
    # Pagination
    paginator = Paginator(batches, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_batches': batches.count(),
        'completed_batches': batches.filter(status='completed').count(),
        'failed_batches': batches.filter(status='failed').count(),
    }
    return render(request, 'imports/index.html', context)

@login_required
def upload_step(request):
    """Step 1: File upload and preview."""
    if request.method == 'POST':
        form = ImportFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create import batch
                batch = form.save(commit=False)
                batch.original_filename = request.FILES['file'].name
                batch.file_size = request.FILES['file'].size
                batch.file_type = 'csv' if batch.original_filename.lower().endswith('.csv') else 'xlsx'
                batch.created_by = request.user if request.user.is_authenticated else None
                
                # Process file for preview
                file_content = request.FILES['file'].read()
                
                if batch.is_csv():
                    # Detect encoding
                    from .utils import detect_encoding
                    detected_encoding = detect_encoding(file_content)
                    batch.encoding = detected_encoding
                    batch.delimiter = ','
                    
                    # Process CSV
                    csv_data = process_csv_file(file_content, detected_encoding, ',')
                    batch.discovered_headers = csv_data['headers']
                    batch.preview_data = csv_data['preview_data']
                    batch.total_rows = csv_data['total_rows']
                    
                elif batch.is_xlsx():
                    # Process XLSX
                    xlsx_data = process_xlsx_file(file_content)
                    batch.discovered_headers = xlsx_data['headers']
                    batch.preview_data = xlsx_data['preview_data']
                    batch.total_rows = xlsx_data['total_rows']
                    batch.available_worksheets = xlsx_data['worksheet_names']
                    batch.worksheet_name = xlsx_data['worksheet_names'][0] if xlsx_data['worksheet_names'] else ''
                
                # Validate limits
                validate_file_limits(batch.total_rows, batch.file_size)
                
                # Save batch
                batch.save()
                
                # Redirect to options step
                return redirect('imports:options_step', batch_id=batch.id)
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = ImportFileUploadForm()
    
    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
    }
    return render(request, 'imports/upload_step.html', context)

@login_required
def options_step(request, batch_id):
    """Step 1.5: File options (encoding, delimiter, worksheet)."""
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    if request.method == 'POST':
        if batch.is_csv():
            form = CSVOptionsForm(request.POST)
        else:
            form = XLSXOptionsForm(request.POST, worksheet_choices=[
                (ws, ws) for ws in batch.available_worksheets
            ])
        
        if form.is_valid():
            # Update batch with options
            if batch.is_csv():
                batch.encoding = form.cleaned_data['encoding']
                batch.delimiter = form.cleaned_data['delimiter']
                
                # Reprocess with new options
                with batch.file.open('rb') as f:
                    file_content = f.read()
                
                csv_data = process_csv_file(file_content, batch.encoding, batch.delimiter)
                batch.discovered_headers = csv_data['headers']
                batch.preview_data = csv_data['preview_data']
                batch.total_rows = csv_data['total_rows']
                
            else:
                batch.worksheet_name = form.cleaned_data['worksheet_name']
                
                # Reprocess with selected worksheet
                with batch.file.open('rb') as f:
                    file_content = f.read()
                
                worksheet_data = get_xlsx_worksheet_data(file_content, batch.worksheet_name)
                batch.discovered_headers = worksheet_data['headers']
                batch.preview_data = worksheet_data['data'][:200]  # First 200 rows
                batch.total_rows = worksheet_data['total_rows']
            
            batch.save()
            return redirect('imports:mapping_step', batch_id=batch.id)
    else:
        if batch.is_csv():
            form = CSVOptionsForm(initial={
                'encoding': batch.encoding,
                'delimiter': batch.delimiter
            })
        else:
            form = XLSXOptionsForm(worksheet_choices=[
                (ws, ws) for ws in batch.available_worksheets
            ], initial={'worksheet_name': batch.worksheet_name})
    
    context = {
        'batch': batch,
        'form': form,
        'step': 1.5,
        'total_steps': 3,
    }
    return render(request, 'imports/options_step.html', context)

@login_required
def mapping_step(request, batch_id):
    """Step 2: Field mapping configuration."""
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    if request.method == 'POST':
        # Handle mapping form submission
        machine_mapping = create_mapping_dict(request.POST, 'machines')
        engine_mapping = create_mapping_dict(request.POST, 'engines')
        part_mapping = create_mapping_dict(request.POST, 'parts')
        
        # Handle part attribute mappings
        part_attribute_mappings = {}
        all_attrs = PartAttribute.objects.select_related('category').order_by('category__name', 'sort_order', 'name')
        for attr in all_attrs:
            key = f"attr_map_{attr.id}"
            header = request.POST.get(key, '').strip()
            if header:
                part_attribute_mappings[str(attr.id)] = header
        
        # Create or update mapping
        mapping_name = request.POST.get('mapping_name', '')
        mapping_description = request.POST.get('mapping_description', '')
        
        if mapping_name:
            mapping, created = SavedImportMapping.objects.get_or_create(
                name=mapping_name,
                defaults={
                    'description': mapping_description,
                    'created_by': request.user if request.user.is_authenticated else None
                }
            )
            
            # Update mapping
            mapping.machine_mapping = machine_mapping
            mapping.engine_mapping = engine_mapping
            mapping.part_mapping = part_mapping
            mapping.part_attribute_mappings = part_attribute_mappings
            mapping.save()
            
            # Assign to batch
            batch.mapping = mapping
            batch.status = 'mapped'
            batch.save()
            
            messages.success(request, f"Mapping '{mapping_name}' saved successfully.")
            return redirect('imports:processing_step', batch_id=batch.id)
        else:
            messages.error(request, "Please provide a name for the mapping.")
    
    # Create mapping forms for each section
    machine_form = ImportMappingForm(
        discovered_headers=batch.discovered_headers,
        section='machines'
    )
    engine_form = ImportMappingForm(
        discovered_headers=batch.discovered_headers,
        section='engines'
    )
    additional_engine_form = AdditionalEngineMappingForm(
        discovered_headers=batch.discovered_headers
    )
    part_form = ImportMappingForm(
        discovered_headers=batch.discovered_headers,
        section='parts'
    )
    
    # Get auto-suggestions for engine fields
    from .utils import suggest_engine_field_mappings
    engine_suggestions = suggest_engine_field_mappings(batch.discovered_headers)
    
    # Get all part attributes for mapping
    all_attrs = PartAttribute.objects.select_related('category').order_by('category__name', 'sort_order', 'name')
    
    # Get saved mappings for dropdown
    saved_mappings = SavedImportMapping.objects.all()
    
    context = {
        'batch': batch,
        'machine_form': machine_form,
        'engine_form': engine_form,
        'additional_engine_form': additional_engine_form,
        'part_form': part_form,
        'all_attrs': all_attrs,
        'saved_mappings': saved_mappings,
        'engine_suggestions': engine_suggestions,
        'step': 2,
        'total_steps': 3,
    }
    return render(request, 'imports/mapping_step.html', context)

@login_required
def processing_step(request, batch_id):
    """Step 3: Processing options and commit."""
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    if not batch.mapping:
        messages.error(request, "No mapping configuration found. Please complete the mapping step.")
        return redirect('imports:mapping_step', batch_id=batch.id)
    
    if request.method == 'POST':
        form = ProcessingOptionsForm(request.POST)
        if form.is_valid():
            # Update mapping with processing options
            mapping = batch.mapping
            mapping.chunk_size = form.cleaned_data['chunk_size']
            mapping.skip_duplicates = form.cleaned_data['skip_duplicates']
            mapping.update_existing = form.cleaned_data['update_existing']
            mapping.save()
            
            # Start processing task
            from django.conf import settings
            if getattr(settings, 'CELERY_ENABLED', False):
                # Use Celery for async processing
                result = process_import_batch.delay(batch.id)
                batch.celery_id = result.id
                batch.status = 'queued'
                batch.save(update_fields=['celery_id', 'status'])
            else:
                # For large files, run asynchronously even without Celery
                if batch.total_rows > 5000:
                    import threading
                    batch.status = 'processing'
                    batch.save(update_fields=['status'])
                    thread = threading.Thread(target=process_import_batch, args=(batch.id,))
                    thread.daemon = True
                    thread.start()
                else:
                    # Run synchronously for small files
                    batch.status = 'processing'
                    batch.save(update_fields=['status'])
                    process_import_batch(batch.id)
            
            messages.success(request, "Import processing started. You can monitor progress below.")
            return redirect('imports:processing_step', batch_id=batch.id)
    else:
        # Smart chunk size based on file size
        default_chunk_size = 2000
        if batch.total_rows > 20000:
            default_chunk_size = 500  # Very large files
        elif batch.total_rows > 10000:
            default_chunk_size = 1000  # Large files
        elif batch.total_rows > 5000:
            default_chunk_size = 1500  # Medium files
        
        form = ProcessingOptionsForm(initial={
            'chunk_size': batch.mapping.chunk_size if batch.mapping else default_chunk_size,
            'skip_duplicates': batch.mapping.skip_duplicates if batch.mapping else True,
            'update_existing': batch.mapping.update_existing if batch.mapping else False,
        })
    
    context = {
        'batch': batch,
        'form': form,
        'step': 3,
        'total_steps': 3,
    }
    return render(request, 'imports/processing_step.html', context)

@login_required
def batch_status(request, batch_id):
    """HTMX endpoint for polling import status."""
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    # Check Celery task status if available
    celery_meta = {}
    if batch.celery_id:
        try:
            from celery.result import AsyncResult
            from django.conf import settings
            
            if getattr(settings, 'CELERY_ENABLED', False):
                result = AsyncResult(batch.celery_id)
                celery_meta = {
                    'state': result.state,
                    'meta': result.info if hasattr(result, 'info') else {}
                }
                
                # Update batch status based on Celery task state
                if result.state == 'PENDING' and batch.status != 'queued':
                    batch.status = 'queued'
                    batch.save(update_fields=['status'])
                elif result.state == 'PROGRESS' and batch.status != 'processing':
                    batch.status = 'processing'
                    batch.save(update_fields=['status'])
                elif result.state == 'SUCCESS' and batch.status != 'completed':
                    batch.status = 'completed'
                    batch.save(update_fields=['status'])
                elif result.state == 'FAILURE' and batch.status != 'failed':
                    batch.status = 'failed'
                    batch.error_message = str(result.info) if result.info else 'Task failed'
                    batch.save(update_fields=['status', 'error_message'])
        except Exception as e:
            # If Celery check fails, continue with database status
            celery_meta = {'error': str(e)}
    
    # Get recent logs
    recent_logs = batch.logs.all()[:10]
    
    # Get ImportRow statistics
    rows_stats = batch.rows.aggregate(
        total_rows=Count('id'),
        error_rows=Count('id', filter=Q(has_errors=True)),
        machine_created=Count('id', filter=Q(machine_created=True)),
        engine_created=Count('id', filter=Q(engine_created=True)),
        part_created=Count('id', filter=Q(part_created=True)),
        machine_updated=Count('id', filter=Q(machine_updated=True)),
        engine_updated=Count('id', filter=Q(engine_updated=True)),
        part_updated=Count('id', filter=Q(part_updated=True)),
        relationships_created=Count('id', filter=Q(
            Q(machine_engine_created=True) | 
            Q(engine_part_created=True) | 
            Q(part_vendor_created=True)
        ))
    )
    
    context = {
        'batch': batch,
        'recent_logs': recent_logs,
        'rows_stats': rows_stats,
        'celery_meta': celery_meta,
    }
    
    html = render_to_string('imports/partials/batch_status.html', context)
    
    return JsonResponse({
        'status': batch.status,
        'progress': batch.progress_percentage,
        'processed_rows': batch.processed_rows,
        'total_rows': batch.total_rows,
        'html': html,
        'is_complete': batch.status in ['completed', 'failed'],
        'rows_stats': rows_stats,
        'celery_meta': celery_meta
    })

@login_required
def batch_detail(request, batch_id):
    """View import batch details and logs."""
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    # Paginate logs
    paginator = Paginator(batch.logs.all(), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get ImportRow statistics
    rows_stats = batch.rows.aggregate(
        total_rows=Count('id'),
        error_rows=Count('id', filter=Q(has_errors=True)),
        machine_created=Count('id', filter=Q(machine_created=True)),
        engine_created=Count('id', filter=Q(engine_created=True)),
        part_created=Count('id', filter=Q(part_created=True)),
        machine_updated=Count('id', filter=Q(machine_updated=True)),
        engine_updated=Count('id', filter=Q(engine_updated=True)),
        part_updated=Count('id', filter=Q(part_updated=True)),
        relationships_created=Count('id', filter=Q(
            Q(machine_engine_created=True) | 
            Q(engine_part_created=True) | 
            Q(part_vendor_created=True)
        ))
    )
    
    context = {
        'batch': batch,
        'page_obj': page_obj,
        'rows_stats': rows_stats,
    }
    return render(request, 'imports/batch_detail.html', context)

@login_required
def batch_rows(request, batch_id):
    """View import rows with filtering options."""
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    # Get filter parameters
    has_errors = request.GET.get('has_errors')
    machine_created = request.GET.get('machine_created')
    engine_created = request.GET.get('engine_created')
    part_created = request.GET.get('part_created')
    
    # Build query
    rows = batch.rows.all()
    
    if has_errors == 'true':
        rows = rows.filter(has_errors=True)
    elif has_errors == 'false':
        rows = rows.filter(has_errors=False)
    
    if machine_created == 'true':
        rows = rows.filter(machine_created=True)
    elif machine_created == 'false':
        rows = rows.filter(machine_created=False)
    
    if engine_created == 'true':
        rows = rows.filter(engine_created=True)
    elif engine_created == 'false':
        rows = rows.filter(engine_created=False)
    
    if part_created == 'true':
        rows = rows.filter(part_created=True)
    elif part_created == 'false':
        rows = rows.filter(part_created=False)
    
    # Pagination
    paginator = Paginator(rows, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics for current filter
    filtered_stats = rows.aggregate(
        total_rows=Count('id'),
        error_rows=Count('id', filter=Q(has_errors=True)),
        machine_created=Count('id', filter=Q(machine_created=True)),
        engine_created=Count('id', filter=Q(engine_created=True)),
        part_created=Count('id', filter=Q(part_created=True)),
    )
    
    context = {
        'batch': batch,
        'page_obj': page_obj,
        'filtered_stats': filtered_stats,
        'current_filters': {
            'has_errors': has_errors,
            'machine_created': machine_created,
            'engine_created': engine_created,
            'part_created': part_created,
        }
    }
    return render(request, 'imports/batch_rows.html', context)

@login_required
def load_saved_mapping(request, mapping_id):
    """HTMX endpoint to load a saved mapping."""
    mapping = get_object_or_404(SavedImportMapping, id=mapping_id)
    
    return JsonResponse({
        'machine_mapping': mapping.machine_mapping,
        'engine_mapping': mapping.engine_mapping,
        'part_mapping': mapping.part_mapping,
    })

@login_required
def saved_mappings_list(request):
    """List of saved import mappings."""
    mappings = SavedImportMapping.objects.all()
    
    context = {
        'mappings': mappings,
    }
    return render(request, 'imports/saved_mappings_list.html', context)

# Unmatched Items Views
@login_required
def unmatched_index(request):
    """Main unmatched items dashboard."""
    from inventory.models import Engine, Machine, Part
    
    # Get counts of unmatched items
    unmatched_engines = Engine.objects.filter(sg_engine__isnull=True).count()
    unmatched_machines = Machine.objects.filter(engines__isnull=True).count()
    unmatched_parts = Part.objects.filter(engines__isnull=True).count()
    
    # Get recent import rows with errors
    error_rows = ImportRow.objects.filter(has_errors=True).order_by('-created_at')[:10]
    
    context = {
        'unmatched_engines': unmatched_engines,
        'unmatched_machines': unmatched_machines,
        'unmatched_parts': unmatched_parts,
        'error_rows': error_rows,
    }
    return render(request, 'imports/unmatched_index.html', context)

@login_required
def unmatched_engines(request):
    """Show engines that need SG Engine matching."""
    from inventory.models import Engine
    
    engines = Engine.objects.filter(sg_engine__isnull=True).order_by('engine_make', 'engine_model')
    
    # Pagination
    paginator = Paginator(engines, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_unmatched': engines.count(),
    }
    return render(request, 'imports/unmatched_engines.html', context)

@login_required
def unmatched_machines(request):
    """Show machines that need engine relationships."""
    from inventory.models import Machine
    
    machines = Machine.objects.filter(engines__isnull=True).order_by('make', 'model')
    
    # Pagination
    paginator = Paginator(machines, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_unmatched': machines.count(),
    }
    return render(request, 'imports/unmatched_machines.html', context)

@login_required
def unmatched_parts(request):
    """Show parts that need engine relationships."""
    from inventory.models import Part
    
    parts = Part.objects.filter(engines__isnull=True).order_by('part_number', 'name')
    
    # Pagination
    paginator = Paginator(parts, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_unmatched': parts.count(),
    }
    return render(request, 'imports/unmatched_parts.html', context)

@login_required
def models_for_make(request):
    """AJAX endpoint to get models for a given make."""
    from inventory.models import SGEngine
    
    sg_make = request.GET.get('sg_make', '')
    if sg_make:
        models = SGEngine.objects.filter(sg_make__iexact=sg_make).values_list('sg_model', flat=True).distinct()
        return JsonResponse({'models': list(models)})
    return JsonResponse({'models': []})

@login_required
def match_single(request):
    """HTMX endpoint to match a single engine to SG Engine."""
    from inventory.models import Engine, SGEngine
    
    if request.method == 'POST':
        engine_id = request.POST.get('engine_id')
        sg_engine_id = request.POST.get('sg_engine_id')
        
        try:
            engine = Engine.objects.get(id=engine_id)
            
            if not sg_engine_id:
                return JsonResponse({
                    'success': False, 
                    'error': 'Select an SG Identifier.',
                    'html': render_to_string('imports/partials/engine_row.html', {
                        'engine': engine,
                        'error': 'Select an SG Identifier.'
                    }, request=request)
                })
            
            # Get the exact SG Engine by ID
            try:
                sg_engine = SGEngine.objects.get(id=sg_engine_id)
            except SGEngine.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'error': 'Selected SG Engine not found.',
                    'html': render_to_string('imports/partials/engine_row.html', {
                        'engine': engine,
                        'error': 'Selected SG Engine not found.'
                    }, request=request)
                })
            
            # Update engine
            engine.sg_engine = sg_engine
            engine.save()
            
            return JsonResponse({'success': True, 'message': 'Engine matched successfully'})
            
        except Engine.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Engine not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def engine_identifiers(request):
    """HTMX endpoint to get SG Engine identifiers for a selected model."""
    from inventory.models import SGEngine
    
    sg_model = request.GET.get('sg_model_id')
    sg_make = request.GET.get('sg_make')
    
    if not sg_model:
        return HttpResponse('<option value="">Select Identifier</option>')
    
    try:
        # Get the SGEngine for the selected make and model
        if sg_make:
            sg_engine = SGEngine.objects.filter(sg_make=sg_make, sg_model=sg_model).first()
        else:
            sg_engine = SGEngine.objects.filter(sg_model=sg_model).first()
        
        if sg_engine:
            # Return the single identifier for this make+model combination
            options_html = f'<option value="">Select Identifier</option>'
            options_html += f'<option value="{sg_engine.id}">{sg_engine.identifier}</option>'
        else:
            options_html = '<option value="">No identifiers found</option>'
        
        return HttpResponse(options_html)
        
    except Exception as e:
        return HttpResponse('<option value="">Error loading identifiers</option>')

@login_required
def sg_models_by_letter(request):
    """AJAX endpoint to get SG models that start with a specific letter."""
    from inventory.models import SGEngine
    
    letter = request.GET.get('letter', '').upper()
    if letter:
        models = SGEngine.objects.filter(sg_model__istartswith=letter).values('sg_make', 'sg_model').distinct()
        return JsonResponse({'models': list(models)})
    return JsonResponse({'models': []})

@login_required
def sg_make_for_model(request):
    """AJAX endpoint to get SG make for a given model."""
    from inventory.models import SGEngine
    
    sg_model = request.GET.get('sg_model', '')
    if sg_model:
        try:
            sg_engine = SGEngine.objects.filter(sg_model__iexact=sg_model).first()
            if sg_engine:
                return JsonResponse({'sg_make': sg_engine.sg_make})
        except Exception:
            pass
    return JsonResponse({'sg_make': None})

@login_required
def search_sg_engines(request):
    """AJAX endpoint to search SG engines by name."""
    from inventory.models import SGEngine
    
    query = request.GET.get('q', '').strip()
    if query and len(query) >= 2:
        engines = SGEngine.objects.filter(
            Q(sg_make__icontains=query) | 
            Q(sg_model__icontains=query) |
            Q(identifier__icontains=query)
        ).values('sg_make', 'sg_model', 'identifier')[:20]
        return JsonResponse({'engines': list(engines)})
    return JsonResponse({'engines': []})

@login_required
def create_sg_engine(request):
    """AJAX endpoint to create a new SG Engine."""
    from inventory.models import SGEngine
    
    if request.method == 'POST':
        sg_make = request.POST.get('sg_make', '').strip()
        sg_model = request.POST.get('sg_model', '').strip()
        identifier = request.POST.get('identifier', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        if not sg_make or not sg_model:
            return JsonResponse({'success': False, 'error': 'SG Make and SG Model are required'})
        
        try:
            # Generate identifier if not provided
            if not identifier:
                identifier = f"{sg_make}_{sg_model}".replace(' ', '_').upper()
            
            # Create SG Engine
            sg_engine = SGEngine.objects.create(
                sg_make=sg_make,
                sg_model=sg_model,
                identifier=identifier,
                notes=notes
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'SG Engine created successfully',
                'sg_engine': {
                    'id': sg_engine.id,
                    'sg_make': sg_engine.sg_make,
                    'sg_model': sg_engine.sg_model,
                    'identifier': sg_engine.identifier
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
