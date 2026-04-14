from django.db import migrations, models
import django.db.models.deletion


def migrate_course_payment_installments(apps, schema_editor):
    CoursePayment = apps.get_model("internship", "CoursePayment")
    InstallmentItem = apps.get_model("internship", "InstallmentItem")
    Student = apps.get_model("internship", "Student")
    StudentCourseEnrollment = apps.get_model("internship", "StudentCourseEnrollment")

    for payment in CoursePayment.objects.select_related("installment").all():
        legacy_installment = payment.installment
        if legacy_installment is None:
            continue

        candidates = InstallmentItem.objects.filter(
            plan__course_id=legacy_installment.course_id,
            amount=legacy_installment.amount,
            due_days=legacy_installment.due_days_after_enrollment,
        ).order_by("plan_id", "installment_number", "id")

        student = Student.objects.filter(profile_id=payment.staff_id).first()
        preferred_plan_ids = []

        if student:
            enrollment = (
                StudentCourseEnrollment.objects
                .filter(
                    student_id=student.id,
                    course_id=legacy_installment.course_id,
                )
                .exclude(installment_plan_id__isnull=True)
                .order_by("id")
                .first()
            )
            if enrollment:
                preferred_plan_ids.append(enrollment.installment_plan_id)

            if student.payment_type_id and student.payment_type_id not in preferred_plan_ids:
                preferred_plan_ids.append(student.payment_type_id)

        if preferred_plan_ids:
            scoped_candidates = candidates.filter(plan_id__in=preferred_plan_ids)
            if scoped_candidates.exists():
                candidates = scoped_candidates

        candidate = candidates.first()
        if candidate is None:
            raise RuntimeError(
                f"Unable to map CoursePayment {payment.id} to an InstallmentItem."
            )

        payment.installment_item_id = candidate.id
        payment.save(update_fields=["installment_item"])


def reverse_course_payment_installments(apps, schema_editor):
    CoursePayment = apps.get_model("internship", "CoursePayment")
    CourseInstallment = apps.get_model("internship", "CourseInstallment")

    for payment in CoursePayment.objects.select_related("installment_item").all():
        installment_item = payment.installment_item
        if installment_item is None:
            continue

        candidate = (
            CourseInstallment.objects.filter(
                course_id=installment_item.plan.course_id,
                amount=installment_item.amount,
                due_days_after_enrollment=installment_item.due_days,
            )
            .order_by("id")
            .first()
        )
        if candidate is None:
            raise RuntimeError(
                f"Unable to reverse-map CoursePayment {payment.id} to a CourseInstallment."
            )

        payment.installment_id = candidate.id
        payment.save(update_fields=["installment"])


class Migration(migrations.Migration):

    dependencies = [
        ("internship", "0014_student_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursepayment",
            name="installment_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payment_installment_migrations",
                to="internship.installmentitem",
            ),
        ),
        migrations.RunPython(
            migrate_course_payment_installments,
            reverse_course_payment_installments,
        ),
        migrations.RemoveField(
            model_name="coursepayment",
            name="installment",
        ),
        migrations.RenameField(
            model_name="coursepayment",
            old_name="installment_item",
            new_name="installment",
        ),
        migrations.AlterField(
            model_name="coursepayment",
            name="installment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="internship.installmentitem",
            ),
        ),
    ]
