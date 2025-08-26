# Generated manually to convert part category to foreign key

import django.db.models.deletion
from django.db import migrations, models

def convert_category_to_foreign_key(apps, schema_editor):
    """Convert existing category string values to foreign key references."""
    PartCategory = apps.get_model('inventory', 'PartCategory')
    
    # Update each part to reference the correct PartCategory using raw SQL
    from django.db import connection
    with connection.cursor() as cursor:
        # Get all parts with their category names
        cursor.execute("SELECT id, category FROM inventory_part WHERE category IS NOT NULL AND category != ''")
        parts = cursor.fetchall()
        
        for part_id, category_name in parts:
            if category_name and category_name.strip():
                try:
                    # Get the category ID
                    cursor.execute("SELECT id FROM inventory_partcategory WHERE name = %s", [category_name])
                    category_result = cursor.fetchone()
                    if category_result:
                        category_id = category_result[0]
                        # Update the new foreign key field
                        cursor.execute(
                            "UPDATE inventory_part SET category_fk_id = %s WHERE id = %s",
                            [category_id, part_id]
                        )
                except Exception:
                    # If category doesn't exist, skip it
                    pass

def reverse_convert_category(apps, schema_editor):
    """Reverse the conversion (not really needed but required for migration)."""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_migrate_part_categories'),
    ]

    operations = [
        # First, remove the index on the old category field
        migrations.RemoveIndex(
            model_name='part',
            name='part_category_lower_idx',
        ),
        # Add the new foreign key field
        migrations.AddField(
            model_name='part',
            name='category_fk',
            field=models.ForeignKey(
                blank=True, 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='parts', 
                to='inventory.partcategory'
            ),
        ),
        # Convert the data
        migrations.RunPython(
            convert_category_to_foreign_key,
            reverse_convert_category,
        ),
        # Remove the old field
        migrations.RemoveField(
            model_name='part',
            name='category',
        ),
        # Rename the new field to the original name
        migrations.RenameField(
            model_name='part',
            old_name='category_fk',
            new_name='category',
        ),
    ]
