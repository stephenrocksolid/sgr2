"""
Import revert logic for rolling back imports.
"""
from django.db import transaction
from django.utils import timezone
from inventory.models import Machine, Engine, Part, Vendor
from imports.models import ImportRow, ImportLog


@transaction.atomic
def execute_revert(batch, user):
    """
    Revert an import by deleting all created records.
    
    Args:
        batch: ImportBatch instance to revert
        user: User performing the revert
        
    Returns:
        dict: Statistics of deleted records
    """
    rows = batch.rows.all()
    
    # Collect IDs of created records
    machine_ids = set()
    engine_ids = set()
    part_ids = set()
    vendor_ids = set()
    
    for row in rows:
        if row.machine_created and row.machine_id:
            machine_ids.add(row.machine_id)
        if row.engine_created and row.engine_id:
            engine_ids.add(row.engine_id)
        if row.part_created and row.part_id:
            part_ids.add(row.part_id)
        if row.vendor_created and row.vendor_id:
            vendor_ids.add(row.vendor_id)
    
    # Check vendors for external usage
    safe_vendor_ids = []
    kept_vendor_ids = []
    
    for vendor_id in vendor_ids:
        # Only delete if not used in other imports or has no other relationships
        other_usage = ImportRow.objects.filter(
            vendor_id=vendor_id
        ).exclude(batch=batch).exists()
        
        if not other_usage:
            vendor = Vendor.objects.filter(id=vendor_id).first()
            if vendor:
                # Check if vendor has relationships beyond this import
                # Count engines and parts not from this import
                other_engines = vendor.engines.exclude(id__in=engine_ids).exists()
                other_parts = vendor.parts.exclude(id__in=part_ids).exists()
                
                if not other_engines and not other_parts:
                    safe_vendor_ids.append(vendor_id)
                else:
                    kept_vendor_ids.append(vendor_id)
        else:
            kept_vendor_ids.append(vendor_id)
    
    # Delete in order (CASCADE will handle relationships)
    # Django's delete() returns a tuple: (count, dict_of_counts)
    part_result = Part.objects.filter(id__in=part_ids).delete()
    part_count = part_result[0] if part_result else 0
    
    engine_result = Engine.objects.filter(id__in=engine_ids).delete()
    engine_count = engine_result[0] if engine_result else 0
    
    machine_result = Machine.objects.filter(id__in=machine_ids).delete()
    machine_count = machine_result[0] if machine_result else 0
    
    vendor_result = Vendor.objects.filter(id__in=safe_vendor_ids).delete()
    vendor_count = vendor_result[0] if vendor_result else 0
    
    # Update batch
    batch.status = 'reverted'
    batch.reverted_at = timezone.now()
    batch.reverted_by = user
    batch.save()
    
    # Log the revert
    ImportLog.objects.create(
        batch=batch,
        level='info',
        message=f'Import reverted: {machine_count} machines, {engine_count} engines, {part_count} parts, {vendor_count} vendors deleted'
    )
    
    return {
        'machines': machine_count,
        'engines': engine_count,
        'parts': part_count,
        'vendors': vendor_count,
        'vendors_kept': len(kept_vendor_ids)
    }


def get_revert_preview(batch):
    """
    Get preview of what will be deleted if import is reverted.
    
    Args:
        batch: ImportBatch instance
        
    Returns:
        dict: Preview statistics and warnings
    """
    rows = batch.rows.all()
    
    # Collect IDs
    machine_ids = set()
    engine_ids = set()
    part_ids = set()
    vendor_ids = set()
    
    # Track relationships
    relationships_count = 0
    
    for row in rows:
        if row.machine_created and row.machine_id:
            machine_ids.add(row.machine_id)
        if row.engine_created and row.engine_id:
            engine_ids.add(row.engine_id)
        if row.part_created and row.part_id:
            part_ids.add(row.part_id)
        if row.vendor_created and row.vendor_id:
            vendor_ids.add(row.vendor_id)
            
        # Count relationships
        if row.machine_engine_created:
            relationships_count += 1
        if row.engine_part_created:
            relationships_count += 1
        if row.machine_part_created:
            relationships_count += 1
        if row.part_vendor_created:
            relationships_count += 1
    
    # Check vendors
    safe_vendor_count = 0
    kept_vendor_count = 0
    
    for vendor_id in vendor_ids:
        other_usage = ImportRow.objects.filter(
            vendor_id=vendor_id
        ).exclude(batch=batch).exists()
        
        if not other_usage:
            vendor = Vendor.objects.filter(id=vendor_id).first()
            if vendor:
                other_engines = vendor.engines.exclude(id__in=engine_ids).exists()
                other_parts = vendor.parts.exclude(id__in=part_ids).exists()
                
                if not other_engines and not other_parts:
                    safe_vendor_count += 1
                else:
                    kept_vendor_count += 1
        else:
            kept_vendor_count += 1
    
    # Check if any records have been modified since import
    warnings = []
    
    if batch.updated_at and batch.created_at:
        # Check if any created records have been modified
        modified_machines = Machine.objects.filter(
            id__in=machine_ids,
            updated_at__gt=batch.updated_at
        ).count()
        
        modified_engines = Engine.objects.filter(
            id__in=engine_ids,
            updated_at__gt=batch.updated_at
        ).count()
        
        modified_parts = Part.objects.filter(
            id__in=part_ids,
            updated_at__gt=batch.updated_at
        ).count()
        
        total_modified = modified_machines + modified_engines + modified_parts
        
        if total_modified > 0:
            warnings.append(f"{total_modified} record(s) have been modified since import and will be deleted")
    
    return {
        'machines': len(machine_ids),
        'engines': len(engine_ids),
        'parts': len(part_ids),
        'vendors_to_delete': safe_vendor_count,
        'vendors_to_keep': kept_vendor_count,
        'relationships': relationships_count,
        'warnings': warnings
    }

