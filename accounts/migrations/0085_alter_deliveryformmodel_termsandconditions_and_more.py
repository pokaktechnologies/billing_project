# Generated by Django 4.2.16 on 2025-06-12 04:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0084_alter_modulepermission_module_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deliveryformmodel',
            name='termsandconditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
        migrations.AlterField(
            model_name='invoicemodel',
            name='termsandconditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
        migrations.AlterField(
            model_name='purchaseorder',
            name='terms_and_conditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
        migrations.AlterField(
            model_name='quotationordermodel',
            name='termsandconditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
        migrations.AlterField(
            model_name='receiptmodel',
            name='termsandconditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
        migrations.AlterField(
            model_name='salesordermodel',
            name='termsandconditions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='payment_terms',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.termsandconditions'),
        ),
    ]
