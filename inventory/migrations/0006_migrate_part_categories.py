# Generated manually to migrate part categories

from django.db import migrations

def migrate_part_categories(apps, schema_editor):
    """Migrate existing part category data to PartCategory model."""
    Part = apps.get_model('inventory', 'Part')
    PartCategory = apps.get_model('inventory', 'PartCategory')
    
    # Get all unique category values from existing parts
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT category FROM inventory_part WHERE category IS NOT NULL AND category != ''")
        categories = [row[0] for row in cursor.fetchall()]
    
    # Create PartCategory records
    category_map = {}
    for category_name in categories:
        if category_name and category_name.strip():
            # Create slug from name
            slug = category_name.lower().replace(' ', '-').replace('_', '-')
            # Ensure slug is unique
            base_slug = slug
            counter = 1
            while PartCategory.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            category, created = PartCategory.objects.get_or_create(
                name=category_name,
                defaults={'slug': slug}
            )
            category_map[category_name] = category

def reverse_migrate_part_categories(apps, schema_editor):
    """Reverse the data migration."""
    PartCategory = apps.get_model('inventory', 'PartCategory')
    PartCategory.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_create_part_custom_field_models'),
    ]

    operations = [
        migrations.RunPython(
            migrate_part_categories,
            reverse_migrate_part_categories,
        ),
    ]
