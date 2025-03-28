# Generated by Django 4.2.16 on 2025-02-21 06:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_remove_product_stock_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quotationitem',
            name='total_price',
        ),
        migrations.AddField(
            model_name='quotationitem',
            name='cgst',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AddField(
            model_name='quotationitem',
            name='sgst',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AddField(
            model_name='quotationitem',
            name='sub_total',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AddField(
            model_name='quotationitem',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AddField(
            model_name='quotationordermodel',
            name='grand_total',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
    ]
