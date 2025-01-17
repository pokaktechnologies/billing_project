# Generated by Django 4.2.16 on 2025-01-06 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_quotationorder'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(max_length=255)),
                ('invoice_number', models.CharField(max_length=50, unique=True)),
                ('invoice_date', models.DateField()),
                ('terms', models.CharField(blank=True, max_length=255)),
                ('due_date', models.DateField()),
                ('salesperson', models.CharField(max_length=255)),
                ('subject', models.TextField(blank=True)),
                ('attachments', models.URLField(blank=True)),
                ('invoice_amount', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
    ]
