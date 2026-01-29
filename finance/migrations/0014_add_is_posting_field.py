# Run: python manage.py migrate finance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_alter_journalentry_type'),
    ]

    operations = [
        # Add is_posting field with default=True (existing accounts become posting)
        migrations.AddField(
            model_name='account',
            name='is_posting',
            field=models.BooleanField(
                default=True,
                help_text='Only posting accounts can receive journal entries. Parent accounts must be non-posting.'
            ),
        ),
        # Make account_number required (remove blank=True, null=True)
        migrations.AlterField(
            model_name='account',
            name='account_number',
            field=models.CharField(max_length=100, unique=True),
        ),
        # Add ordering to Account model
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ['account_number']},
        ),
    ]
