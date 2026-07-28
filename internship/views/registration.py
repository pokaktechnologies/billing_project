from decimal import Decimal

from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import ListAPIView

from internship.models import (Student,StudentCourseEnrollment,StudentInstallmentItem)
from internship.serializers.registration import StudentRegistrationReportSerializer


class StudentRegistrationReportView(ListAPIView):
    serializer_class = StudentRegistrationReportSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "student__profile__user__first_name",
        "student__profile__user__last_name",
        "student__profile__phone_number",
        "student__student_id",
    ]

    filterset_fields = {
        "enrollment_date": ["exact", "gte", "lte"],
        "student__center": ["exact"],
        "student__councellor": ["exact"],
        "student__status": ["exact"],
        "course": ["exact"],
    }

    ordering_fields = [
        "enrollment_date",
        "student__student_id",
        "student__start_date",
        "student__status",
    ]

    ordering = ["-enrollment_date"]

    queryset = (
        StudentCourseEnrollment.objects
        .select_related(
            "student__profile__user",
            "student__center",
            "student__councellor",
            "course",
            "batch",
            "installment_plan",
        )
        .prefetch_related(
            Prefetch(
                "student_installment_items",
                queryset=StudentInstallmentItem.objects.prefetch_related(
                    "course_payments"
                ),
            ),
            "student__course_payments",
            "batch__faculties__user__user",
        )
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        # Course Search
        course = self.request.query_params.get("course")
        if course:
            queryset = queryset.filter(
                course__title__icontains=course
            )

        # Payment Status Filter
        payment_status = self.request.query_params.get("payment_status")
        if payment_status:
            serializer = self.serializer_class()

            enrollment_ids = []

            for enrollment in queryset:
                status = serializer.get_payment_status(enrollment)

                if (
                    status
                    and status.lower() == payment_status.lower()
                ):
                    enrollment_ids.append(enrollment.id)

            queryset = queryset.filter(id__in=enrollment_ids)

        return queryset