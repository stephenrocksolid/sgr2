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

# Import Celery task decorator with fallback
try:
    from celery import shared_task
except ImportError:
    # Fallback decorator when Celery is not available
    def shared_task(func):
        return func

@shared_task
def test_task():
    return "Celery is working!"

@shared_task
def process_import_batch(batch_id):
    """Process an import batch in chunks with transaction.atomic() per chunk."""
    start_time = time.time()
    
    try:
        batch = ImportBatch.objects.get(id=batch_id)
        batch.status = 'processing'
        batch.progress_percentage = 0
        batch.save()
        
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
            success_count, error_count = process_csv_import(batch, mapping)
        elif batch.is_xlsx():
            success_count, error_count = process_xlsx_import(batch, mapping)
        else:
            raise Exception(f"Unsupported file type: {batch.file_type}")
        
        # Update batch status
        batch.status = 'completed'
        batch.progress_percentage = 100
        batch.processed_rows = success_count + error_count
        batch.save()
        
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

def process_csv_import(batch, mapping):
    """Process CSV import in chunks."""
    success_count = 0
    error_count = 0
    
    # Read file content
    with batch.file.open('rb') as f:
        file_content = f.read()
    
    # Process CSV - read all data, not just preview
    from .utils import process_csv_file_all_data
    csv_data = process_csv_file_all_data(
        file_content, 
        encoding=batch.encoding, 
        delimiter=batch.delimiter
    )
    
    headers = csv_data['headers']
    data = csv_data['data']  # All data, not just preview
    
    # Process in chunks
    chunk_size = mapping.chunk_size
    total_rows = len(data)
    
    for i in range(0, total_rows, chunk_size):
        chunk = data[i:i + chunk_size]
        
        # Process chunk with transaction
        chunk_success, chunk_errors = process_data_chunk(
            batch, mapping, headers, chunk, i + 1
        )
        
        success_count += chunk_success
        error_count += chunk_errors
        
        # Update progress
        progress = min(100, int((i + len(chunk)) / total_rows * 100))
        batch.progress_percentage = progress
        batch.processed_rows = i + len(chunk)
        batch.save()
    
    return success_count, error_count

def process_xlsx_import(batch, mapping):
    """Process XLSX import in chunks."""
    success_count = 0
    error_count = 0
    
    # Read file content
    with batch.file.open('rb') as f:
        file_content = f.read()
    
    # Get worksheet data
    from .utils import get_xlsx_worksheet_data
    worksheet_data = get_xlsx_worksheet_data(file_content, batch.worksheet_name)
    
    headers = worksheet_data['headers']
    data = worksheet_data['data']  # All data, not just preview
    
    # Process in chunks
    chunk_size = mapping.chunk_size
    total_rows = len(data)
    
    for i in range(0, total_rows, chunk_size):
        chunk = data[i:i + chunk_size]
        
        # Process chunk with transaction
        chunk_success, chunk_errors = process_data_chunk(
            batch, mapping, headers, chunk, i + 1
        )
        
        success_count += chunk_success
        error_count += chunk_errors
        
        # Update progress
        progress = min(100, int((i + len(chunk)) / total_rows * 100))
        batch.progress_percentage = progress
        batch.processed_rows = i + len(chunk)
        batch.save()
    
    return success_count, error_count

def process_data_chunk(batch, mapping, headers, chunk_data, start_row):
    """Process a chunk of data rows with transaction.atomic() per chunk."""
    success_count = 0
    error_count = 0
    
    for row_index, row in enumerate(chunk_data):
        row_number = start_row + row_index
        row_start_time = time.time()
        
        # Create ImportRow record outside of transaction
        row_data = dict(zip(headers, row))
        import_row = ImportRow.objects.create(
            batch=batch,
            row_number=row_number,
            original_data=row_data
        )
        
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
    
    for field in dedupe_fields:
        if field in machine_data:
            dedupe_filters[f"{field}__iexact"] = machine_data[field]
    
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
            for field, value in filtered_machine_data.items():
                setattr(existing_machine, field, value)
            existing_machine.save()
            import_row.machine_updated = True
            import_row.machine_id = existing_machine.id
            import_row.save()
            return
    
    # Filter out fields that don't exist on the Machine model
    filtered_machine_data = filter_valid_fields(machine_data, Machine)
    
    # Create new machine
    machine = Machine.objects.create(**filtered_machine_data)
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
        sg_engine, created = SGEngine.objects.get_or_create(
            sg_make__iexact=engine_data['sg_make'],
            sg_model__iexact=engine_data['sg_model'],
            defaults={
                'sg_make': engine_data['sg_make'],
                'sg_model': engine_data['sg_model'],
                'identifier': f"{engine_data['sg_make']}_{engine_data['sg_model']}".replace(' ', '_').upper()
            }
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
            for field, value in filtered_engine_data.items():
                setattr(existing_engine, field, value)
            existing_engine.save()
            import_row.engine_updated = True
            import_row.engine_id = existing_engine.id
            import_row.save()
            return
    
    # Filter out fields that don't exist on the Engine model
    filtered_engine_data = filter_valid_fields(engine_data, Engine)
    
    # Create new engine
    engine = Engine.objects.create(**filtered_engine_data)
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
            for field, value in filtered_part_data.items():
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
    
    # Create new part
    part = Part.objects.create(**filtered_part_data)
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
            vendor, created = Vendor.objects.get_or_create(
                name__iexact=vendor_name,
                defaults={'name': vendor_name}
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
            
            part_vendor, created = PartVendor.objects.get_or_create(
                part=part,
                vendor=vendor,
                defaults=part_vendor_data
            )
            
            if created:
                import_row.part_vendor_created = True
            
            # Set as primary vendor if specified
            if vendor_data.get('primary_vendor_name') == vendor_name:
                part.primary_vendor = vendor
                part.save()
    
    import_row.save()
