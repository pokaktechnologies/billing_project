# Generated by Django 4.2.16 on 2025-04-17 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0044_alter_quotationitem_unit_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='cgst',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AddField(
            model_name='product',
            name='sgst',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
    ]
