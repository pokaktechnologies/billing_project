from django.db import migrations, models
import django.db.models.deletion


def copy_coursepayment_student(apps, schema_editor):
    CoursePayment = apps.get_model("internship", "CoursePayment")
    Student = apps.get_model("internship", "Student")

    missing_payments = []

    for payment in CoursePayment.objects.all():
        student = Student.objects.filter(profile_id=payment.staff_id).only("id").first()
        if not student:
            missing_payments.append(str(payment.id))
            continue

        payment.student_id = student.id
        payment.save(update_fields=["student"])

    if missing_payments:
        raise RuntimeError(
            "Could not map CoursePayment staff to Student for payment ids: "
            + ", ".join(missing_payments)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("internship", "0015_alter_coursepayment_installment"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursepayment",
            name="student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="course_payments",
                to="internship.student",
            ),
        ),
        migrations.RunPython(copy_coursepayment_student, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="coursepayment",
            name="staff",
        ),
        migrations.AlterField(
            model_name="coursepayment",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="course_payments",
                to="internship.student",
            ),
        ),
    ]
