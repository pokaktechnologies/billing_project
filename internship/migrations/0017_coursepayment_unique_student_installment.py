from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internship", "0016_coursepayment_student"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="coursepayment",
            constraint=models.UniqueConstraint(
                fields=("student", "installment"),
                name="unique_student_installment_payment",
            ),
        ),
    ]
