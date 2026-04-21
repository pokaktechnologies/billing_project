from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import InternshipApplication
from ..serializers.application import (
    InternshipApplicationListSerializer,
    InternshipApplicationSerializer,
)


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
    permission_classes = [IsAuthenticated]
    pagination_class = InternshipApplicationPagination

    def get_queryset(self):
        return InternshipApplication.objects.prefetch_related("documents").order_by(
            "-created_at"
        )

    def filter_queryset(self, queryset):
        params = self.request.query_params

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(primary_phone__icontains=search)
                | Q(course_applied_for__icontains=search)
            )

        academic_counselor = params.get("academic_counselor")
        if academic_counselor:
            queryset = queryset.filter(
                academic_counselor__icontains=academic_counselor
            )

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
