# Generated manually to fix main_bearing field type mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0014_jobcomponent_main_bearing_and_more'),
    ]

    operations = [
        # Remove the main_bearing_done field that shouldn't exist
        migrations.RemoveField(
            model_name='jobcomponent',
            name='main_bearing_done',
        ),
        # Alter main_bearing from BooleanField to CharField with null=True
        migrations.AlterField(
            model_name='jobcomponent',
            name='main_bearing',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
