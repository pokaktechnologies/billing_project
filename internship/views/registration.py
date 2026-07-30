from decimal import Decimal

import django_filters
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import ListAPIView

from internship.models import (Student,StudentCourseEnrollment,StudentInstallmentItem)
from internship.serializers.registration import StudentRegistrationReportSerializer






class StudentRegistrationReportFilter(django_filters.FilterSet):

    center = django_filters.NumberFilter(
        field_name="student__center"
    )

    councellor = django_filters.NumberFilter(
        field_name="student__councellor"
    )

    status = django_filters.CharFilter(
        field_name="student__status"
    )

    created_at__date = django_filters.DateFilter(
        field_name="enrollment_date"
    )

    created_at__date__gte = django_filters.DateFilter(
        field_name="enrollment_date",
        lookup_expr="gte"
    )

    created_at__date__lte = django_filters.DateFilter(
        field_name="enrollment_date",
        lookup_expr="lte"
    )

    class Meta:
        model = StudentCourseEnrollment
        fields = []

from rest_framework.filters import OrderingFilter
class StudentRegistrationOrderingFilter(OrderingFilter):

    ordering_map = {
        "created_at": "enrollment_date",
        "student_code": "student__student_id",
        "status": "student__status",
        "center": "student__center__name",
        "councellor": "student__councellor__profile__user__first_name",
        "course": "course__title",
        "form_type": "form_type",
    }

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)

        if not params:
            return getattr(view, "ordering", None)

        ordering = []

        for field in params.split(","):
            desc = field.startswith("-")
            key = field.lstrip("-")

            mapped = self.ordering_map.get(key, key)

            if desc:
                mapped = "-" + mapped

            ordering.append(mapped)

        return ordering
class StudentRegistrationReportView(ListAPIView):
    serializer_class = StudentRegistrationReportSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        StudentRegistrationOrderingFilter,
    ]

    search_fields = [
        "student__profile__user__first_name",
        "student__profile__user__last_name",
        "student__profile__phone_number",
        "student__student_id",
    ]

    filterset_class = StudentRegistrationReportFilter


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