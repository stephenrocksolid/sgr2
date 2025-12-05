# Generated manually on 2025-12-04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0031_add_engine_identifier'),
        ('jobs', '0011_purchaseorder_purchaseorderattachment_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchaseorder',
            name='vendor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='purchase_orders',
                to='inventory.vendor'
            ),
        ),
    ]



