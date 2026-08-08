from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from ..models import InternshipApplication
from ..serializers.application import (
    InternshipApplicationListSerializer,
    InternshipApplicationSerializer,
    ConvertToStudentSerializer
)
from ..utils import StudentConversionService

class InternshipApplicationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params and "page_size" not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            },
            status=status.HTTP_200_OK,
        )


class InternshipApplicationAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = InternshipApplicationPagination

    def get_queryset(self):
        return InternshipApplication.objects.prefetch_related("documents").order_by(
            "-created_at"
        )

    def filter_queryset(self, queryset):
        params = self.request.query_params

        form_type = params.get("form_type")
        if form_type:
            queryset = queryset.filter(form_type=form_type)

            
        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(primary_phone__icontains=search)
                | Q(course_applied_for__icontains=search)
                | Q(course__title__icontains=search)
                | Q(councellor__first_name__icontains=search)
            )

        course = params.get("course")
        if course:
            queryset = queryset.filter(course_id=course)
            
        councellor = params.get("councellor")
        if councellor:
            queryset = queryset.filter(councellor_id=councellor)

        qualification = params.get("qualification")
        if qualification:
            queryset = queryset.filter(qualification=qualification)

        gender = params.get("gender")
        if gender:
            queryset = queryset.filter(gender=gender)

        course_type = params.get("course_type")
        if course_type:
            queryset = queryset.filter(course_type=course_type)

        source = params.get("where_did_you_find_us")
        if source:
            queryset = queryset.filter(where_did_you_find_us=source)

        state = params.get("state")
        if state:
            queryset = queryset.filter(state__icontains=state)

        district = params.get("district")
        if district:
            queryset = queryset.filter(district__icontains=district)

        created_at = params.get("created_at")
        if created_at:
            queryset = queryset.filter(created_at__date=created_at)

        created_at_after = params.get("created_at_after")
        if created_at_after:
            queryset = queryset.filter(created_at__date__gte=created_at_after)

        created_at_before = params.get("created_at_before")
        if created_at_before:
            queryset = queryset.filter(created_at__date__lte=created_at_before)

        return queryset

    def get(self, request, pk=None):
        if pk is not None:
            application = get_object_or_404(self.get_queryset(), pk=pk)
            serializer = InternshipApplicationSerializer(
                application,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        try:
            paginated_queryset = paginator.paginate_queryset(
                queryset,
                request,
                view=self,
            )
        except NotFound:
            return Response(
                {
                    "count": queryset.count(),
                    "next": None,
                    "previous": None,
                    "results": [],
                    "detail": "Not found.",
                },
                status=status.HTTP_200_OK,
            )

        if paginated_queryset is None:
            serializer = InternshipApplicationListSerializer(
                queryset,
                many=True,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = InternshipApplicationListSerializer(
            paginated_queryset,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = InternshipApplicationSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        application = serializer.save()

        response_serializer = InternshipApplicationSerializer(
            application,
            context={"request": request},
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk=None):
        if pk is None:
            return Response(
                {"detail": "Application id is required for delete."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application = get_object_or_404(self.get_queryset(), pk=pk)
        application.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConvertApplicationToStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        application = get_object_or_404(
            InternshipApplication,
            pk=pk,
        )

        serializer = ConvertToStudentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:

            student = StudentConversionService.convert(
                application=application,
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                center=serializer.validated_data["center"],
                start_date=serializer.validated_data["start_date"],
                # councellor=serializer.validated_data.get("councellor"),# old
                councellor=application.councellor,
                status=serializer.validated_data["status"],
            )

        except ValueError as exc:

            return Response(
                {
                    "status": "0",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "1",
                "message": "Student converted successfully.",
                "student_id": student.id,
                "student_code": student.student_id,
            },
            status=status.HTTP_201_CREATED,
        )


import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.filters import OrderingFilter
from ..serializers.application import InternshipApplicationReportSerializer


class InternshipApplicationReportFilter(django_filters.FilterSet):
    form_type = django_filters.CharFilter(field_name="form_type")
    councellor = django_filters.NumberFilter(field_name="councellor")
    course = django_filters.NumberFilter(field_name="course")
    course_type = django_filters.CharFilter(field_name="course_type")
    qualification = django_filters.CharFilter(field_name="qualification")
    gender = django_filters.CharFilter(field_name="gender")
    is_converted = django_filters.BooleanFilter(field_name="is_converted")
    where_did_you_find_us = django_filters.CharFilter(field_name="where_did_you_find_us")
    state = django_filters.CharFilter(field_name="state", lookup_expr="icontains")
    district = django_filters.CharFilter(field_name="district", lookup_expr="icontains")

    created_at__date = django_filters.DateFilter(field_name="created_at__date")
    created_at__date__gte = django_filters.DateFilter(field_name="created_at__date", lookup_expr="gte")
    created_at__date__lte = django_filters.DateFilter(field_name="created_at__date", lookup_expr="lte")

    slot_payment_date = django_filters.DateFilter(field_name="slot_payment_date")
    slot_payment_date__gte = django_filters.DateFilter(field_name="slot_payment_date", lookup_expr="gte")
    slot_payment_date__lte = django_filters.DateFilter(field_name="slot_payment_date", lookup_expr="lte")

    class Meta:
        model = InternshipApplication
        fields = []


class InternshipApplicationOrderingFilter(OrderingFilter):
    ordering_map = {
        "created_at": "created_at",
        "first_name": "first_name",
        "last_name": "last_name",
        "applicant_name": "first_name",
        "email": "email",
        "councellor": "councellor__first_name",
        "course": "course__title",
        "slot_amount": "slot_amount",
        "slot_payment_date": "slot_payment_date",
        "is_converted": "is_converted",
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


class InternshipApplicationReportView(generics.ListAPIView):
    serializer_class = InternshipApplicationReportSerializer
    pagination_class = InternshipApplicationPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        InternshipApplicationOrderingFilter,
    ]
    filterset_class = InternshipApplicationReportFilter

    search_fields = [
        "first_name",
        "last_name",
        "email",
        "primary_phone",
        "secondary_phone",
        "course_name",
        "course__title",
        "academic_counselor",
        "councellor__first_name",
        "councellor__last_name",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            InternshipApplication.objects.select_related(
                "course",
                "councellor",
                "converted_students",
            )
            .prefetch_related("documents")
            .order_by("-created_at")
        )

