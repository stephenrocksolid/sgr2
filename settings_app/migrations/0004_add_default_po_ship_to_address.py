# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0003_userprofile_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_po_ship_to_name',
            field=models.CharField(blank=True, help_text='Default recipient name for PO shipping', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_po_ship_to_address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_po_ship_to_city',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_po_ship_to_state',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_po_ship_to_zip',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_po_ship_to_phone',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]



