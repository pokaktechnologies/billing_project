# Generated by Django 4.2.16 on 2025-03-19 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_salesperson_address_salesperson_country_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salesperson',
            name='display_name',
            field=models.CharField(max_length=200),
        ),
    ]
