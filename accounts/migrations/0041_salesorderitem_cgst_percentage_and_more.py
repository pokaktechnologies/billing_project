# Generated by Django 4.2.16 on 2025-04-11 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0040_salesorderitem_unit_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesorderitem',
            name='cgst_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='salesorderitem',
            name='sgst_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
