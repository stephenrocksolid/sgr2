import csv
import io
import json
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple, Any
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Q
from openpyxl import load_workbook
from .models import ImportBatch, ImportLog, SavedImportMapping, ImportRow
from inventory.models import Machine, Engine, Part, SGEngine, Vendor, PartVendor, MachineEngine, EnginePart, MachinePart, PartAttribute, PartAttributeValue, PartAttributeChoice

def get_valid_model_fields(model_class):
    """Get a set of valid field names for a Django model."""
    return {field.name for field in model_class._meta.get_fields()}

def filter_valid_fields(data, model_class):
    """Filter data to only include fields that exist on the model."""
    valid_fields = get_valid_model_fields(model_class)
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
    
    # Log filtered out fields for debugging
    filtered_out = {k: v for k, v in data.items() if k not in valid_fields}
    if filtered_out:
        print(f"Warning: Filtered out invalid fields for {model_class.__name__}: {list(filtered_out.keys())}")
    
    return filtered_data

def validate_and_truncate_fields(data, model_class, batch=None, row_number=None):
    """Validate and truncate field values to match model constraints."""
    if not data:
        return data
    
    validated_data = {}
    
    # Get model field information
    model_fields = {field.name: field for field in model_class._meta.get_fields()}
    
    for field_name, value in data.items():
        if field_name not in model_fields:
            validated_data[field_name] = value
            continue
            
        field = model_fields[field_name]
        
        # Skip if value is None or empty
        if value is None or value == '':
            validated_data[field_name] = value
            continue
            
        # Convert to string for validation
        str_value = str(value)
        
        # Check for CharField with max_length
        if hasattr(field, 'max_length') and field.max_length:
            if len(str_value) > field.max_length:
                truncated_value = str_value[:field.max_length]
                validated_data[field_name] = truncated_value
                
                # Log truncation warning
                warning_msg = f"Truncated {field_name} from {len(str_value)} to {field.max_length} characters: '{str_value}' -> '{truncated_value}'"
                print(f"Warning: {warning_msg}")
                
                # Log to database if batch info is available
                if batch and row_number is not None:
                    ImportLog.objects.create(
                        batch=batch,
                        level='warning',
                        message=warning_msg,
                        row_number=row_number
                    )
            else:
                validated_data[field_name] = value
        else:
            validated_data[field_name] = value
    
    return validated_data

# Import Celery task decorator with fallback
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    # Fallback decorator when Celery is not available
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    CELERY_AVAILABLE = False

@shared_task
def test_task():
    return "Celery is working!"

@shared_task(bind=True, time_limit=1800, soft_time_limit=1500)
def process_import_batch(self, batch_id):
    """Process an import batch in chunks with transaction.atomic() per chunk."""
    start_time = time.time()
    
    try:
        batch = ImportBatch.objects.get(id=batch_id)
        batch.status = 'processing'
        batch.progress_percentage = 0
        batch.save()
        
        # Update Celery task state
        if CELERY_AVAILABLE and hasattr(self, 'update_state'):
            self.update_state(
                state='PROGRESS',
                meta={'rows': 0, 'created': 0, 'errors': 0, 'status': 'Starting import...'}
            )
        
        # Log start
        ImportLog.objects.create(
            batch=batch,
            level='info',
            message=f"Starting import processing for {batch.original_filename}"
        )
        
        # Get mapping configuration
        if not batch.mapping:
            raise Exception("No mapping configuration found for this batch.")
        
        mapping = batch.mapping
        
        # Process file based on type
        if batch.is_csv():
            success_count, error_count = process_csv_import(batch, mapping, self)
        elif batch.is_xlsx():
            success_count, error_count = process_xlsx_import(batch, mapping, self)
        else:
            raise Exception(f"Unsupported file type: {batch.file_type}")
        
        # Update batch status
        batch.status = 'completed'
        batch.progress_percentage = 100
        batch.processed_rows = success_count + error_count
        batch.save()
        
        # Final Celery task state update
        if CELERY_AVAILABLE and hasattr(self, 'update_state'):
            self.update_state(
                state='SUCCESS',
                meta={
                    'rows': success_count + error_count,
                    'created': success_count,
                    'errors': error_count,
                    'status': 'Import completed successfully'
                }
            )
        
        # Log completion
        ImportLog.objects.create(
            batch=batch,
            level='info',
            message=f"Import completed in {time.time() - start_time:.2f}s. {success_count} records processed successfully, {error_count} errors."
        )
        
        return {
            'success': True,
            'processed_rows': success_count + error_count,
            'success_count': success_count,
            'error_count': error_count,
            'processing_time': time.time() - start_time
        }
        
    except Exception as e:
        # Update batch status to failed
        try:
            batch = ImportBatch.objects.get(id=batch_id)
            batch.status = 'failed'
            batch.error_message = str(e)
            batch.save()
            
            # Update Celery task state
            if CELERY_AVAILABLE and hasattr(self, 'update_state'):
                self.update_state(
                    state='FAILURE',
                    meta={'status': f'Import failed: {str(e)}'}
                )
            
            ImportLog.objects.create(
                batch=batch,
                level='error',
                message=f"Import failed: {str(e)}"
            )
        except:
            pass
        
        return {
            'success': False,
            'error': str(e)
        }

def process_csv_import(batch, mapping, task_instance=None):
    """Process CSV import in chunks with streaming."""
    success_count = 0
    error_count = 0
    
    # Use streaming approach to avoid loading entire file into memory
    chunk_size = mapping.chunk_size or 1000  # Default to 1000 if not set
    
    # Read file in streaming fashion
    with batch.file.open('rb') as f:
        # Detect encoding and delimiter if needed
        file_content_sample = f.read(8192)  # Read first 8KB for detection
        f.seek(0)  # Reset to beginning
        
        # Process CSV with streaming
        import csv
        import io
        
        # Decode the file content
        text_content = file_content_sample.decode(batch.encoding or 'utf-8', errors='ignore')
        
        # Get headers from first line
        first_line = text_content.split('\n')[0]
        headers = [h.strip() for h in first_line.split(batch.delimiter or ',')]
        
        # Stream process the file
        f.seek(0)
        text_stream = io.TextIOWrapper(f, encoding=batch.encoding or 'utf-8')
        csv_reader = csv.reader(text_stream, delimiter=batch.delimiter or ',')
        
        # Skip header row
        next(csv_reader, None)
        
        # Process in chunks
        chunk_data = []
        row_number = 1
        
        for row in csv_reader:
            chunk_data.append(row)
            
            # Process chunk when it reaches the chunk size
            if len(chunk_data) >= chunk_size:
                chunk_success, chunk_errors = process_data_chunk(
                    batch, mapping, headers, chunk_data, row_number - len(chunk_data) + 1, task_instance
                )
                
                success_count += chunk_success
                error_count += chunk_errors
                
                # Update progress
                progress = min(100, int(row_number / batch.total_rows * 100)) if batch.total_rows > 0 else 0
                batch.progress_percentage = progress
                batch.processed_rows = row_number
                batch.save()
                
                # Update Celery task state
                if task_instance and CELERY_AVAILABLE and hasattr(task_instance, 'update_state'):
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'rows': row_number,
                            'created': success_count,
                            'errors': error_count,
                            'status': f'Processing row {row_number}...'
                        }
                    )
                
                # Clear chunk
                chunk_data = []
            
            row_number += 1
        
        # Process remaining data in chunk
        if chunk_data:
            chunk_success, chunk_errors = process_data_chunk(
                batch, mapping, headers, chunk_data, row_number - len(chunk_data), task_instance
            )
            success_count += chunk_success
            error_count += chunk_errors
    
    return success_count, error_count

def process_xlsx_import(batch, mapping, task_instance=None):
    """Process XLSX import in chunks with streaming."""
    success_count = 0
    error_count = 0
    
    # Use streaming approach for XLSX
    chunk_size = mapping.chunk_size or 1000  # Default to 1000 if not set
    
    # Stream process XLSX file
    with batch.file.open('rb') as f:
        from openpyxl import load_workbook
        
        # Load workbook with read_only=True for memory efficiency
        workbook = load_workbook(f, read_only=True, data_only=True)
        
        # Get the specified worksheet
        worksheet_name = batch.worksheet_name or workbook.sheetnames[0]
        worksheet = workbook[worksheet_name]
        
        # Get headers from first row
        headers = []
        first_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if first_row:
            headers = [str(cell).strip() if cell is not None else '' for cell in first_row]
        
        # Process rows in chunks
        chunk_data = []
        row_number = 1
        
        # Iterate through rows starting from row 2 (skip header)
        for row in worksheet.iter_rows(min_row=2, values_only=True):
            # Convert row to list and handle None values
            row_data = [str(cell).strip() if cell is not None else '' for cell in row]
            
            # Skip completely empty rows
            if not any(cell for cell in row_data):
                continue
            
            chunk_data.append(row_data)
            
            # Process chunk when it reaches the chunk size
            if len(chunk_data) >= chunk_size:
                chunk_success, chunk_errors = process_data_chunk(
                    batch, mapping, headers, chunk_data, row_number - len(chunk_data) + 1, task_instance
                )
                
                success_count += chunk_success
                error_count += chunk_errors
                
                # Update progress
                progress = min(100, int(row_number / batch.total_rows * 100)) if batch.total_rows > 0 else 0
                batch.progress_percentage = progress
                batch.processed_rows = row_number
                batch.save()
                
                # Update Celery task state
                if task_instance and CELERY_AVAILABLE and hasattr(task_instance, 'update_state'):
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'rows': row_number,
                            'created': success_count,
                            'errors': error_count,
                            'status': f'Processing row {row_number}...'
                        }
                    )
                
                # Clear chunk
                chunk_data = []
            
            row_number += 1
        
        # Process remaining data in chunk
        if chunk_data:
            chunk_success, chunk_errors = process_data_chunk(
                batch, mapping, headers, chunk_data, row_number - len(chunk_data), task_instance
            )
            success_count += chunk_success
            error_count += chunk_errors
        
        workbook.close()
    
    return success_count, error_count

def process_data_chunk(batch, mapping, headers, chunk_data, start_row, task_instance=None):
    """Process a chunk of data rows with transaction.atomic() per chunk and bulk operations."""
    success_count = 0
    error_count = 0
    
    # Pre-create ImportRow records in bulk to reduce DB queries
    import_rows_to_create = []
    for row_index, row in enumerate(chunk_data):
        row_number = start_row + row_index
        row_data = dict(zip(headers, row))
        import_rows_to_create.append(ImportRow(
            batch=batch,
            row_number=row_number,
            original_data=row_data
        ))
    
    # Bulk create ImportRow records
    created_import_rows = ImportRow.objects.bulk_create(import_rows_to_create)
    
    # Process each row with chunked transactions
    for row_index, (row, import_row) in enumerate(zip(chunk_data, created_import_rows)):
        row_number = start_row + row_index
        row_start_time = time.time()
        row_data = dict(zip(headers, row))
        
        try:
            # Process row within transaction
            with transaction.atomic():
                # Normalize data
                normalized_data = normalize_row_data(row_data, mapping)
                
                # Update ImportRow with normalized data
                import_row.normalized_machine_data = normalized_data.get('machine', {})
                import_row.normalized_engine_data = normalized_data.get('engine', {})
                import_row.normalized_part_data = normalized_data.get('part', {})
                
                # Process each section based on mapping
                if mapping.machine_mapping and mapping.machine_mapping != {}:
                    process_machine_row(batch, mapping, normalized_data, import_row)
                
                if mapping.engine_mapping and mapping.engine_mapping != {}:
                    process_engine_row(batch, mapping, normalized_data, import_row)
                
                if mapping.part_mapping and mapping.part_mapping != {}:
                    process_part_row(batch, mapping, normalized_data, import_row)
                
                # Create relationships
                create_relationships(batch, mapping, normalized_data, import_row)
                
                # Update processing time
                import_row.processing_time_ms = int((time.time() - row_start_time) * 1000)
                import_row.save()
                
                success_count += 1
                
        except Exception as e:
            error_count += 1
            # Handle error outside of transaction
            import_row.add_error(str(e))
            import_row.processing_time_ms = int((time.time() - row_start_time) * 1000)
            import_row.save()
            
            # Log error outside of transaction
            ImportLog.objects.create(
                batch=batch,
                level='error',
                message=f"Row {row_number}: {str(e)}",
                row_number=row_number
            )
    
    return success_count, error_count

def normalize_row_data(row_data: Dict[str, Any], mapping: SavedImportMapping) -> Dict[str, Dict[str, Any]]:
    """Normalize row data according to the specification."""
    normalized = {
        'machine': {},
        'engine': {},
        'part': {},
        'vendor': {},
        'raw_data': row_data  # Include raw data for attribute processing
    }
    
    # Helper function to normalize a value
    def normalize_value(value, field_type='string'):
        if value is None or value == '':
            return None
        
        # Convert to string first
        value = str(value).strip()
        
        if value == '':
            return None
        
        # Collapse multiple spaces
        value = re.sub(r'\s+', ' ', value)
        
        if field_type == 'string':
            return value
        elif field_type == 'uppercase':
            return value.upper()
        elif field_type == 'integer':
            try:
                return int(float(value))  # Handle Excel numbers stored as text
            except (ValueError, TypeError):
                return None
        elif field_type == 'decimal':
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None
        elif field_type == 'boolean':
            # Handle various boolean formats
            value_lower = value.lower().strip()
            
            # Truthy values
            if value_lower in ('true', '1', 'yes', 'y', '✓', 'di', 'idi', 'common rail', 'common-rail', 'cr', '2v', '2 valve', 'two valve', '4v', '4 valve', 'four valve', '5v', '5 valve', 'five valve'):
                return True
            # Falsy values
            elif value_lower in ('false', '0', 'no', 'n', 'x', ''):
                return False
            # For any other value, log warning and default to False
            else:
                # Log warning for invalid boolean values
                print(f"Warning: Invalid boolean value '{value}' - defaulting to False")
                return False
        
        return value
    
    # Normalize machine data
    for field_name, header_name in mapping.machine_mapping.items():
        if header_name in row_data:
            value = row_data[header_name]
            
            # Determine field type for normalization
            if field_name in ['make', 'model', 'machine_type', 'market_type']:
                normalized_value = normalize_value(value, 'string')
            elif field_name == 'year':
                normalized_value = normalize_value(value, 'integer')
            else:
                normalized_value = normalize_value(value, 'string')
            
            if normalized_value is not None:
                normalized['machine'][field_name] = normalized_value
    
    # Normalize engine data
    for field_name, header_name in mapping.engine_mapping.items():
        if header_name in row_data:
            value = row_data[header_name]
            
            # Determine field type for normalization
            if field_name in ['engine_make', 'engine_model', 'sg_engine_identifier', 'sg_engine_notes',
                             'cpl_number', 'ar_number', 'build_list', 'engine_code', 'serial_number',
                             'crankshaft_no', 'piston_no', 'piston_marked_no', 'piston_notes', 'oh_kit_no', 
                             'bore_stroke', 'firing_order', 'overview_comments', 'interference', 'camshaft', 
                             'valve_adjustment', 'status', 'casting_comments']:
                normalized_value = normalize_value(value, 'string')
            elif field_name in ['cylinder', 'valves_per_cyl']:
                normalized_value = normalize_value(value, 'integer')
            elif field_name in ['compression_ratio', 'rod_journal_diameter', 'main_journal_diameter_pos1',
                               'main_journal_diameter_1', 'big_end_housing_bore', 'price']:
                normalized_value = normalize_value(value, 'decimal')
            elif field_name in ['di', 'idi', 'common_rail', 'two_valve', 'four_valve', 'five_valve']:
                normalized_value = normalize_value(value, 'boolean')
            else:
                normalized_value = normalize_value(value, 'string')
            
            if normalized_value is not None:
                normalized['engine'][field_name] = normalized_value
    
    # Normalize part data
    for field_name, header_name in mapping.part_mapping.items():
        if header_name in row_data:
            value = row_data[header_name]
            
            # Determine field type for normalization
            if field_name == 'part_number':
                normalized_value = normalize_value(value, 'uppercase')
            elif field_name in ['name', 'category', 'manufacturer', 'unit', 'type', 'manufacturer_type']:
                normalized_value = normalize_value(value, 'string')
            else:
                normalized_value = normalize_value(value, 'string')
            
            if normalized_value is not None:
                normalized['part'][field_name] = normalized_value
    
    # Handle vendor data (optional columns)
    vendor_fields = ['vendor_name', 'vendor_sku', 'vendor_cost', 'vendor_stock_qty', 'vendor_lead_time_days', 'vendor_notes', 'primary_vendor_name']
    for field_name in vendor_fields:
        if field_name in row_data:
            value = row_data[field_name]
            
            if field_name == 'vendor_name':
                normalized_value = normalize_value(value, 'string')
            elif field_name == 'vendor_sku':
                normalized_value = normalize_value(value, 'string')
            elif field_name == 'vendor_cost':
                normalized_value = normalize_value(value, 'decimal')
            elif field_name == 'vendor_stock_qty':
                normalized_value = normalize_value(value, 'integer')
            elif field_name == 'vendor_lead_time_days':
                normalized_value = normalize_value(value, 'integer')
            elif field_name == 'vendor_notes':
                normalized_value = normalize_value(value, 'string')
            elif field_name == 'primary_vendor_name':
                normalized_value = normalize_value(value, 'string')
            else:
                normalized_value = normalize_value(value, 'string')
            
            if normalized_value is not None:
                normalized['vendor'][field_name] = normalized_value
    
    return normalized

def process_machine_row(batch, mapping, normalized_data, import_row):
    """Process a machine row with deduplication rules."""
    machine_data = normalized_data.get('machine', {})
    
    if not machine_data:
        return
    
    # Check for required fields and provide defaults
    required_fields = ['make', 'model']  # Essential fields that must be provided
    missing_fields = [field for field in required_fields if not machine_data.get(field)]
    if missing_fields:
        error_msg = f"Machine requires: {', '.join(missing_fields)}"
        import_row.add_error(error_msg)
        raise Exception(error_msg)
    
    # Provide defaults for missing optional fields
    if not machine_data.get('year'):
        machine_data['year'] = 0  # Default year when not provided
    if not machine_data.get('machine_type'):
        machine_data['machine_type'] = 'Unknown'  # Default type when not provided
    if not machine_data.get('market_type'):
        machine_data['market_type'] = 'Unknown'  # Default market when not provided
    
    # Apply deduplication rules: (make, model, year, machine_type, market_type) CI
    dedupe_fields = ['make', 'model', 'year', 'machine_type', 'market_type']
    dedupe_filters = {}
    
    # String fields that should use case-insensitive matching
    string_fields = ['make', 'model', 'machine_type', 'market_type']
    
    for field in dedupe_fields:
        if field in machine_data:
            if field in string_fields:
                dedupe_filters[f"{field}__iexact"] = machine_data[field]
            else:
                # For non-string fields (like year), use exact matching
                dedupe_filters[field] = machine_data[field]
    
    # Check for existing machine
    existing_machine = Machine.objects.filter(**dedupe_filters).first()
    
    if existing_machine:
        if mapping.skip_duplicates:
            # Skip duplicate
            import_row.machine_id = existing_machine.id
            import_row.save()
            return
        elif mapping.update_existing:
            # Update existing
            filtered_machine_data = filter_valid_fields(machine_data, Machine)
            validated_machine_data = validate_and_truncate_fields(filtered_machine_data, Machine, batch, import_row.row_number)
            for field, value in validated_machine_data.items():
                setattr(existing_machine, field, value)
            existing_machine.save()
            import_row.machine_updated = True
            import_row.machine_id = existing_machine.id
            import_row.save()
            return
    
    # Filter out fields that don't exist on the Machine model
    filtered_machine_data = filter_valid_fields(machine_data, Machine)
    
    # Validate and truncate field lengths
    validated_machine_data = validate_and_truncate_fields(filtered_machine_data, Machine, batch, import_row.row_number)
    
    # Create new machine
    machine = Machine.objects.create(**validated_machine_data)
    import_row.machine_created = True
    import_row.machine_id = machine.id
    import_row.save()

def process_engine_row(batch, mapping, normalized_data, import_row):
    """Process an engine row with deduplication rules."""
    engine_data = normalized_data.get('engine', {})
    
    if not engine_data:
        return
    
    # Check for required fields
    required_fields = ['engine_make', 'engine_model']
    missing_fields = [field for field in required_fields if not engine_data.get(field)]
    if missing_fields:
        error_msg = f"Engine requires: {', '.join(missing_fields)}"
        import_row.add_error(error_msg)
        raise Exception(error_msg)
    
    # Handle SG Engine mapping
    sg_engine = None
    if engine_data.get('sg_make') and engine_data.get('sg_model'):
        # Validate and truncate SGEngine data
        sg_engine_defaults = {
            'sg_make': engine_data['sg_make'],
            'sg_model': engine_data['sg_model'],
            'identifier': f"{engine_data['sg_make']}_{engine_data['sg_model']}".replace(' ', '_').upper()
        }
        validated_sg_defaults = validate_and_truncate_fields(sg_engine_defaults, SGEngine, batch, import_row.row_number)
        
        sg_engine, created = SGEngine.objects.get_or_create(
            sg_make__iexact=engine_data['sg_make'],
            sg_model__iexact=engine_data['sg_model'],
            defaults=validated_sg_defaults
        )
        engine_data['sg_engine'] = sg_engine
    
    # Apply deduplication rules: (engine_make, engine_model[, cpl_number]) heuristic
    dedupe_filters = {
        'engine_make__iexact': engine_data['engine_make'],
        'engine_model__iexact': engine_data['engine_model']
    }
    
    # Add CPL number to dedupe if available
    if engine_data.get('cpl_number'):
        dedupe_filters['cpl_number__iexact'] = engine_data['cpl_number']
    
    # Check for existing engine
    existing_engine = Engine.objects.filter(**dedupe_filters).first()
    
    if existing_engine:
        if mapping.skip_duplicates:
            # Skip duplicate
            import_row.engine_id = existing_engine.id
            import_row.save()
            return
        elif mapping.update_existing:
            # Update existing
            filtered_engine_data = filter_valid_fields(engine_data, Engine)
            validated_engine_data = validate_and_truncate_fields(filtered_engine_data, Engine, batch, import_row.row_number)
            for field, value in validated_engine_data.items():
                setattr(existing_engine, field, value)
            existing_engine.save()
            import_row.engine_updated = True
            import_row.engine_id = existing_engine.id
            import_row.save()
            return
    
    # Filter out fields that don't exist on the Engine model
    filtered_engine_data = filter_valid_fields(engine_data, Engine)
    
    # Validate and truncate field lengths
    validated_engine_data = validate_and_truncate_fields(filtered_engine_data, Engine, batch, import_row.row_number)
    
    # Create new engine
    engine = Engine.objects.create(**validated_engine_data)
    import_row.engine_created = True
    import_row.engine_id = engine.id
    import_row.save()

def process_part_row(batch, mapping, normalized_data, import_row):
    """Process a part row with deduplication rules."""
    part_data = normalized_data.get('part', {})
    
    if not part_data:
        return
    
    # Check for required fields
    required_fields = ['part_number', 'name']
    missing_fields = [field for field in required_fields if not part_data.get(field)]
    if missing_fields:
        error_msg = f"Part requires: {', '.join(missing_fields)}"
        import_row.add_error(error_msg)
        raise Exception(error_msg)
    
    # Apply deduplication rules: (part_number, name) CI
    dedupe_filters = {
        'part_number__iexact': part_data['part_number'],
        'name__iexact': part_data['name']
    }
    
    # Check for existing part
    existing_part = Part.objects.filter(**dedupe_filters).first()
    
    if existing_part:
        if mapping.skip_duplicates:
            # Skip duplicate
            import_row.part_id = existing_part.id
            import_row.save()
            # Apply attributes to existing part
            apply_part_attributes_from_row(existing_part, normalized_data.get('raw_data', {}), mapping, batch, import_row)
            return
        elif mapping.update_existing:
            # Update existing
            filtered_part_data = filter_valid_fields(part_data, Part)
            validated_part_data = validate_and_truncate_fields(filtered_part_data, Part, batch, import_row.row_number)
            for field, value in validated_part_data.items():
                setattr(existing_part, field, value)
            existing_part.save()
            import_row.part_updated = True
            import_row.part_id = existing_part.id
            import_row.save()
            # Apply attributes to existing part
            apply_part_attributes_from_row(existing_part, normalized_data.get('raw_data', {}), mapping, batch, import_row)
            return
    
    # Filter out fields that don't exist on the Part model
    filtered_part_data = filter_valid_fields(part_data, Part)
    
    # Validate and truncate field lengths
    validated_part_data = validate_and_truncate_fields(filtered_part_data, Part, batch, import_row.row_number)
    
    # Create new part
    part = Part.objects.create(**validated_part_data)
    import_row.part_created = True
    import_row.part_id = part.id
    import_row.save()
    
    # Apply attributes to new part
    apply_part_attributes_from_row(part, normalized_data.get('raw_data', {}), mapping, batch, import_row)

def apply_part_attributes_from_row(part, row_dict, mapping, batch, import_row):
    """Apply mapped part attributes from CSV row data."""
    attr_map = mapping.part_attribute_mappings or {}
    if not attr_map:
        return
    
    # Build a set of allowed attribute IDs for the part's category
    allowed_ids = set(
        PartAttribute.objects
        .filter(category=part.category)
        .values_list("id", flat=True)
    )
    
    for attr_id_str, csv_header in attr_map.items():
        try:
            attr_id = int(attr_id_str)
        except ValueError:
            continue
        
        raw_val = row_dict.get(csv_header, "")
        if raw_val in (None, ""):
            continue
        
        if attr_id not in allowed_ids:
            # Log skip
            ImportLog.objects.create(
                batch=batch,
                level='warning',
                message=f"Skipped attribute {attr_id} — not in category {part.category}",
                row_number=import_row.row_number
            )
            continue
        
        try:
            attr = PartAttribute.objects.get(pk=attr_id)
            
            # Get or create PartAttributeValue
            pav, created = PartAttributeValue.objects.get_or_create(
                part=part, 
                attribute=attr,
                defaults={}
            )
            
            # Clear all typed fields
            pav.value_text = None
            pav.value_int = None
            pav.value_dec = None
            pav.value_bool = None
            pav.value_date = None
            pav.choice = None
            
            # Set the appropriate typed field based on attribute.data_type
            if attr.data_type == "text":
                pav.value_text = str(raw_val)
            elif attr.data_type == "int":
                try:
                    pav.value_int = int(str(raw_val).strip())
                except ValueError:
                    ImportLog.objects.create(
                        batch=batch,
                        level='warning',
                        message=f"Invalid integer value '{raw_val}' for attribute {attr.name}",
                        row_number=import_row.row_number
                    )
                    continue
            elif attr.data_type == "dec":
                try:
                    from decimal import Decimal
                    pav.value_dec = Decimal(str(raw_val))
                except (ValueError, InvalidOperation):
                    ImportLog.objects.create(
                        batch=batch,
                        level='warning',
                        message=f"Invalid decimal value '{raw_val}' for attribute {attr.name}",
                        row_number=import_row.row_number
                    )
                    continue
            elif attr.data_type == "bool":
                pav.value_bool = str(raw_val).strip().lower() in {"1", "true", "yes", "y"}
            elif attr.data_type == "date":
                try:
                    from datetime import datetime
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                        try:
                            pav.value_date = datetime.strptime(str(raw_val).strip(), fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        ImportLog.objects.create(
                            batch=batch,
                            level='warning',
                            message=f"Invalid date format '{raw_val}' for attribute {attr.name}",
                            row_number=import_row.row_number
                        )
                        continue
                except Exception:
                    ImportLog.objects.create(
                        batch=batch,
                        level='warning',
                        message=f"Invalid date value '{raw_val}' for attribute {attr.name}",
                        row_number=import_row.row_number
                    )
                    continue
            elif attr.data_type == "choice":
                choice = attr.choices.filter(value=str(raw_val)).first()
                if choice:
                    pav.choice = choice
                else:
                    ImportLog.objects.create(
                        batch=batch,
                        level='warning',
                        message=f"Invalid choice value '{raw_val}' for attribute {attr.name}",
                        row_number=import_row.row_number
                    )
                    continue
            
            pav.save()
            
        except PartAttribute.DoesNotExist:
            ImportLog.objects.create(
                batch=batch,
                level='warning',
                message=f"Attribute {attr_id} not found",
                row_number=import_row.row_number
            )
            continue
        except Exception as e:
            ImportLog.objects.create(
                batch=batch,
                level='error',
                message=f"Error setting attribute {attr_id}: {str(e)}",
                row_number=import_row.row_number
            )
            continue

def create_relationships(batch, mapping, normalized_data, import_row):
    """Create Machine↔Engine and Engine↔Part relationships."""
    
    # Create Machine↔Engine relationship
    if import_row.machine_id and import_row.engine_id:
        machine = Machine.objects.get(id=import_row.machine_id)
        engine = Engine.objects.get(id=import_row.engine_id)
        
        machine_engine, created = MachineEngine.objects.get_or_create(
            machine=machine,
            engine=engine,
            defaults={'notes': f"Created from import batch {batch.id}"}
        )
        
        if created:
            import_row.machine_engine_created = True
    
    # Create Engine↔Part relationship
    if import_row.engine_id and import_row.part_id:
        engine = Engine.objects.get(id=import_row.engine_id)
        part = Part.objects.get(id=import_row.part_id)
        
        engine_part, created = EnginePart.objects.get_or_create(
            engine=engine,
            part=part,
            defaults={'notes': f"Created from import batch {batch.id}"}
        )
        
        if created:
            import_row.engine_part_created = True
    
    # Create Machine↔Part relationship (stub for future implementation)
    machine_part_data = normalized_data.get('machine_part_links', {})
    if machine_part_data and import_row.machine_id and import_row.part_id:
        machine = Machine.objects.get(id=import_row.machine_id)
        part = Part.objects.get(id=import_row.part_id)
        
        # TODO: Implement machine-part link processing
        # This could handle cases where a row specifies a machine and multiple parts
        # or where a separate section/column specifies machine-part relationships
        pass
    
    # Handle vendor relationships
    vendor_data = normalized_data.get('vendor', {})
    if vendor_data and import_row.part_id:
        part = Part.objects.get(id=import_row.part_id)
        
        # Create or get vendor
        vendor_name = vendor_data.get('vendor_name')
        if vendor_name:
            # Validate vendor defaults
            vendor_defaults = {'name': vendor_name}
            validated_vendor_defaults = validate_and_truncate_fields(vendor_defaults, Vendor, batch, import_row.row_number)
            
            vendor, created = Vendor.objects.get_or_create(
                name__iexact=vendor_name,
                defaults=validated_vendor_defaults
            )
            
            # Create PartVendor relationship
            part_vendor_data = {}
            if vendor_data.get('vendor_sku'):
                part_vendor_data['vendor_sku'] = vendor_data['vendor_sku']
            if vendor_data.get('vendor_cost'):
                part_vendor_data['cost'] = vendor_data['vendor_cost']
            if vendor_data.get('vendor_stock_qty'):
                part_vendor_data['stock_qty'] = vendor_data['vendor_stock_qty']
            if vendor_data.get('vendor_lead_time_days'):
                part_vendor_data['lead_time_days'] = vendor_data['vendor_lead_time_days']
            if vendor_data.get('vendor_notes'):
                part_vendor_data['notes'] = vendor_data['vendor_notes']
            
            # Validate PartVendor data
            validated_part_vendor_data = validate_and_truncate_fields(part_vendor_data, PartVendor, batch, import_row.row_number)
            
            part_vendor, created = PartVendor.objects.get_or_create(
                part=part,
                vendor=vendor,
                defaults=validated_part_vendor_data
            )
            
            if created:
                import_row.part_vendor_created = True
            
            # Set as primary vendor if specified
            if vendor_data.get('primary_vendor_name') == vendor_name:
                part.primary_vendor = vendor
                part.save()
    
    import_row.save()
