# Manual migration to add unique constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0010_merge_buildlists'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='buildlist',
            constraint=models.UniqueConstraint(fields=['engine'], name='unique_buildlist_per_engine'),
        ),
    ]
