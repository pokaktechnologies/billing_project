# Generated by Django 4.2.16 on 2025-04-19 06:44

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0046_alter_product_cgst_alter_product_sgst'),
        ('project_management', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectmanagement',
            name='duration',
            field=models.IntegerField(blank=True, help_text='Duration in days', null=True),
        ),
        migrations.CreateModel(
            name='ClientContract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('contract_date', models.DateField(blank=True, default=datetime.date.today, null=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('duration', models.IntegerField(blank=True, help_text='Duration in days', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='projectmanagement',
            name='contract',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project_management.clientcontract'),
        ),
    ]
