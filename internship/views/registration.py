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
        "profile__user__first_name",
        "profile__user__last_name",
        "profile__phone_number",
        "student_id",
    ]

    filterset_fields = {
        "created_at": ["date", "date__gte", "date__lte"],
        "center": ["exact"],
        "councellor": ["exact"],
        "status": ["exact"],
    }

    ordering_fields = [
        "created_at",
        "student_id",
        "start_date",
        "status",
    ]

    ordering = ["-created_at"]

    queryset = (
        Student.objects.select_related(
            "profile__user",
            "center",
            "councellor",
        )
        .prefetch_related(
            "course_payments",
            Prefetch(
                "enrollments",
                queryset=StudentCourseEnrollment.objects.select_related(
                    "course",
                    "batch",
                    "installment_plan",
                ).prefetch_related(
                    Prefetch(
                        "student_installment_items",
                        queryset=StudentInstallmentItem.objects.prefetch_related(
                            "course_payments"
                        ),
                    ),
                    "batch__faculties__user__user",
                ),
            ),
        )
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        # Course Filter
        course = self.request.query_params.get("course")
        if course:
            queryset = queryset.filter(
                enrollments__course__title__icontains=course
            )

        # Payment Status Filter
        payment_status = self.request.query_params.get("payment_status")

        if payment_status:
            serializer = self.serializer_class()

            ids = []

            for student in queryset:
                status = serializer.get_payment_status(student)

                if (
                    status
                    and status.lower() == payment_status.lower()
                ):
                    ids.append(student.id)

            queryset = queryset.filter(id__in=ids)

        return queryset.distinct()