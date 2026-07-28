from decimal import Decimal

from rest_framework import serializers

from internship.models import Student, StudentCourseEnrollment
from certificates.models import CertificateRecord
from internship.serializers.report_serializers import InstallmentItemReportSerializer


class StudentRegistrationReportSerializer(serializers.ModelSerializer):
    registration_date = serializers.DateField(source="enrollment_date", format="%Y-%m-%d", read_only=True)
    enrollment_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    course_id = serializers.SerializerMethodField()
    student_code = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="student.profile.user.id",read_only=True)
    student_name = serializers.SerializerMethodField()
    place = serializers.SerializerMethodField()
    counsellor = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    center = serializers.CharField(source="student.center.name", read_only=True)
    duration = serializers.SerializerMethodField()
    course_fee = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    second_payment = serializers.SerializerMethodField()
    third_payment = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    student_status = serializers.CharField(source="student.status", read_only=True)
    batch_end_date = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source="student.profile.phone_number", read_only=True)
    start_date = serializers.DateField(source="batch.start_date", format="%Y-%m-%d", read_only=True)



    class Meta:
        model = StudentCourseEnrollment
        fields = [
            "id",
            "enrollment_id",
            "student_id",
            "course_id",
            "user_id",
            "student_code",
            "student_name",
            "registration_date",
            "phone_number",
            "place",
            "counsellor",
            "course",
            "start_date",
            "center",
            "duration",
            "course_fee",
            "paid_amount",
            "balance",
            "second_payment",
            "third_payment",
            "batch_end_date",
            "payment_status",
            "student_status",

        ]

    def get_enrollment_id(self, obj):
        return obj.id

    def get_student_id(self, obj):
        return obj.student.id

    def get_student_code(self, obj):
        return obj.student.student_id

    def get_course_id(self, obj):
        return obj.course.id if obj.course else None

    def get_student_name(self, obj):
        return obj.student.get_full_name()

    def get_place(self, obj):
        return (
            obj.student.center.address
            if obj.student.center
            else None
        )

    def get_counsellor(self, obj):
        counsellor = obj.student.councellor

        if counsellor:
            return {
                "id": counsellor.id,
                "name": counsellor.get_full_name(),
            }

        return None

    def get_course(self, obj):
        return obj.course.title if obj.course else None

    def get_duration(self, obj):
        if obj.batch:
            return (obj.batch.end_date - obj.batch.start_date).days
        return None

    def get_course_fee(self, obj):
        return obj.course.total_fee if obj.course else None

    def get_batch_end_date(self, obj):
        return obj.batch.end_date if obj.batch else None

    def get_balance(self, obj):
        fee = self.get_course_fee(obj)
        if fee is None:
            return None
        return f"{(fee - Decimal(self.get_paid_amount(obj))):.2f}"



    def get_paid_amount(self, obj):
        total = sum(
            payment.amount_paid
            for payment in obj.student.course_payments.all()
        )
        return f"{total:.2f}"

    def _payment(self, obj, number):
        item = obj.student_installment_items.filter(
            installment_number=number
        ).first()

        if not item:
            return None

        paid = sum(
            payment.amount_paid
            for payment in item.course_payments.filter(
                student=obj.student
            )
        )

        return {
            "amount": f"{item.amount:.2f}",
            "paid": f"{paid:.2f}",
            "status": "Paid" if paid >= item.amount else "Pending",
        }

    def get_second_payment(self, obj):
        return self._payment(obj, 2)

    def get_third_payment(self, obj):
        return self._payment(obj, 3)

    def get_payment_status(self, obj):
        fee = self.get_course_fee(obj)

        if fee is None:
            return None

        paid = Decimal(self.get_paid_amount(obj))

        if paid == 0:
            return "Unpaid"

        if paid >= fee:
            return "Paid"

        return "Partial"
