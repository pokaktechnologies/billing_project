# Generated by Django 4.2.16 on 2025-03-26 08:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_alter_product_unit'),
    ]

    operations = [
        migrations.RenameField(
            model_name='quotationordermodel',
            old_name='terms',
            new_name='remark',
        ),
        migrations.RemoveField(
            model_name='quotationordermodel',
            name='attachments',
        ),
        migrations.RemoveField(
            model_name='quotationordermodel',
            name='due_date',
        ),
    ]
