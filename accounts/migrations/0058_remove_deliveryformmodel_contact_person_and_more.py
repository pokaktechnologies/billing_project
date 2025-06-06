# Generated by Django 4.2.16 on 2025-04-30 11:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0057_salesordermodel_termsandconditions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='contact_person',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='customer_name',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='date',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='delivery_status',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='due_date',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='mobile_number',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='salesperson',
        ),
        migrations.RemoveField(
            model_name='deliveryformmodel',
            name='terms',
        ),
        migrations.RemoveField(
            model_name='deliveryitem',
            name='quantity',
        ),
        migrations.RemoveField(
            model_name='deliveryitem',
            name='status',
        ),
        migrations.AddField(
            model_name='deliveryformmodel',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.customer'),
        ),
        migrations.AddField(
            model_name='deliveryformmodel',
            name='termsandconditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.termsandconditions'),
        ),
        migrations.AddField(
            model_name='deliveryformmodel',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='deliveryitem',
            name='cgst_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='deliveryitem',
            name='sgst_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='deliveryitem',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='salesorderitem',
            name='is_item_delivered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='salesorderitem',
            name='pending_quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='salesordermodel',
            name='is_delivered',
            field=models.BooleanField(default=False),
        ),
    ]
