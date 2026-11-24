from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0185_alter_modulepermission_module_name"),
    ]

    operations = [
        migrations.RenameField(
            model_name="staffprofile",
            old_name="qulification",
            new_name="qualification",
        ),
    ]
