# Generated by Django 4.2.16 on 2025-04-15 07:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0043_salesordermodel_quotation_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quotationitem',
            name='unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
    ]
