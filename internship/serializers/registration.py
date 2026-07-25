from decimal import Decimal

from rest_framework import serializers

from internship.models import Student
from certificates.models import CertificateRecord
from internship.serializers.report_serializers import InstallmentItemReportSerializer


class StudentRegistrationReportSerializer(serializers.ModelSerializer):
    registration_date = serializers.DateTimeField(source="created_at",format="%Y-%m-%d",read_only=True)
    enrollment_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    course_id = serializers.SerializerMethodField()
    student_code = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="profile.user.id",read_only=True)
    student_name = serializers.SerializerMethodField()
    place = serializers.SerializerMethodField()
    counsellor = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    center = serializers.CharField(source="center.name", read_only=True, default=None)
    duration = serializers.SerializerMethodField()
    course_fee = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    second_payment = serializers.SerializerMethodField()
    third_payment = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    student_status = serializers.CharField(source="status", read_only=True)
    batch_end_date = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source="profile.phone_number", read_only=True, default=None)


    class Meta:
        model = Student
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

    def _get_enrollment(self, obj):
        if not hasattr(obj, "_cached_enrollment"):
            enrollments = list(obj.enrollments.all())
            obj._cached_enrollment = enrollments[0] if enrollments else None
        return obj._cached_enrollment

    def get_enrollment_id(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.id if enrollment else None

    def get_student_id(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.student.id if enrollment else None

    def get_student_code(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.student.student_id if enrollment else None

    def get_course_id(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.course.id if enrollment and enrollment.course else None
    def get_student_name(self, obj):
        return obj.get_full_name()

    def get_place(self, obj):
        return obj.center.address if obj.center else None

    def get_counsellor(self, obj):
        if obj.councellor:
            return {"id": obj.councellor.id, "name": obj.councellor.get_full_name()}
        return None

    def get_course(self, obj):
        e = self._get_enrollment(obj)
        return e.course.title if e and e.course else None

    def get_duration(self, obj):
        e = self._get_enrollment(obj)
        if e and e.batch:
            return (e.batch.end_date - e.batch.start_date).days
        return None

    def get_course_fee(self, obj):
        e = self._get_enrollment(obj)
        return e.course.total_fee if e and e.course else None

    def get_paid_amount(self, obj):
        total = sum(p.amount_paid for p in obj.course_payments.all())
        return f"{total:.2f}"

    def get_balance(self, obj):
        fee = self.get_course_fee(obj)
        if fee is None:
            return None
        return f"{(fee - Decimal(self.get_paid_amount(obj))):.2f}"

    def get_batch_end_date(self, obj):
        e = self._get_enrollment(obj)
        return e.batch.end_date if e and e.batch else None



    def _payment(self, obj, number):
        e = self._get_enrollment(obj)
        if not e:
            return None
        item = e.student_installment_items.filter(
            installment_number=number
        ).first()
        if not item:
            return None
        paid = sum(
            p.amount_paid
            for p in item.course_payments.filter(student=obj)
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
