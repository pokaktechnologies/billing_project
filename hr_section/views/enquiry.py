from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, permissions, status as drf_status, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from accounts.permissions import HasModulePermission
from activity_logs.base_view import BaseAPIView
from ..models import Enquiry, ErpEnquiry
from ..serializers import (
    EnquirySerializer,
    EnquiryStatusUpdateSerializer,
    ErpEnquirySerializer,
    ErpEnquiryStatusUpdateSerializer,
)


class Pagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        page_size = request.query_params.get('page_size')
        if page_size is None:
            return None 
        return int(page_size)


# ========== Views for Enquiry ==========

class EnquiryCreateView(BaseAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
        return [IsAuthenticated(), HasModulePermission()]

    def get(self, request):
        enquiries = Enquiry.objects.all()
        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = EnquirySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EnquiryDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get_object(self, pk):
        try:
            return Enquiry.objects.get(pk=pk)
        except Enquiry.DoesNotExist:
            return None

    def get(self, request, pk):
        enquiry = self.get_object(pk)
        if enquiry is None:
            return Response({'error': 'Enquiry not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EnquirySerializer(enquiry)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EnquiryStatusUpdateView(BaseAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get_object(self, pk):
        try:
            return Enquiry.objects.get(pk=pk)
        except Enquiry.DoesNotExist:
            return None

    def patch(self, request, pk):
        enquiry = self.get_object(pk)
        if enquiry is None:
            return Response({'error': 'Enquiry not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EnquiryStatusUpdateSerializer(enquiry, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EnquiryStatisticsView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request):
        now = timezone.now()

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now

        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start

        total_enquiries_today = Enquiry.objects.filter(
            created_at__range=(today_start, today_end)
        ).count()

        total_enquiries_yesterday = Enquiry.objects.filter(
            created_at__range=(yesterday_start, yesterday_end)
        ).count()

        if total_enquiries_yesterday > 0:
            percentage_change = (
                (total_enquiries_today - total_enquiries_yesterday)
                / total_enquiries_yesterday
            ) * 100
        else:
            percentage_change = 0
        unread_enquiries = Enquiry.objects.filter(status='new').count()
        reviewed_enquiries = Enquiry.objects.filter(status='reviewed').count()
        responsed_enquiries = Enquiry.objects.filter(status='responded').count()

        statistics = {
            'total_enquiries': {
                'today': total_enquiries_today,
                'yesterday': total_enquiries_yesterday,
                'percentage_change': percentage_change
            },
            'unread_enquiries': unread_enquiries,
            'reviewed_enquiries': reviewed_enquiries,
            'responsed_enquiries': responsed_enquiries
        }

        return Response(statistics, status=status.HTTP_200_OK)


class SearchEnquiryView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request):
        client_name = request.query_params.get('client_name', '')
        email = request.query_params.get('email', '')
        phone = request.query_params.get('phone', '')
        status_filter = request.query_params.get('status', '')
        sort = request.query_params.get('sort', '-created_at')

        query = Q()

        if client_name:
            query &= Q(first_name__icontains=client_name) | Q(last_name__icontains=client_name)
        if email:
            query &= Q(email__icontains=email)
        if phone:
            query &= Q(phone__icontains=phone)
        if status_filter:
            query &= Q(status__iexact=status_filter)

        enquiries = Enquiry.objects.filter(query).order_by(sort)

        paginator = Pagination()
        paginated_enquiries = paginator.paginate_queryset(enquiries, request)
        if paginated_enquiries is not None:
            serializer = EnquirySerializer(paginated_enquiries, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data, status=drf_status.HTTP_200_OK)


# ========== Views for ERP Enquiry ==========

class ErpEnquiryListCreateView(generics.ListCreateAPIView):
    queryset = ErpEnquiry.objects.all()
    serializer_class = ErpEnquirySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'heard_about']
    search_fields = ['full_name', 'work_email', 'company_name']

    def get_queryset(self):
        queryset = super().get_queryset()

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            start = timezone.make_aware(
                datetime.strptime(start_date, "%Y-%m-%d")
            )
            queryset = queryset.filter(created_at__gte=start)

        if end_date:
            end = timezone.make_aware(
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            )
            queryset = queryset.filter(created_at__lt=end)

        return queryset


class ErpEnquiryDetailView(generics.RetrieveAPIView):
    queryset = ErpEnquiry.objects.all()
    serializer_class = ErpEnquirySerializer


class ErpEnquiryStatusUpdateView(generics.UpdateAPIView):
    queryset = ErpEnquiry.objects.all()
    serializer_class = ErpEnquiryStatusUpdateSerializer
    http_method_names = ['patch']


class ErpEnquiryStatisticsView(APIView):
    def get(self, request):
        now = timezone.now()

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now

        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start

        total_today = ErpEnquiry.objects.filter(
            created_at__range=(today_start, today_end)
        ).count()

        total_yesterday = ErpEnquiry.objects.filter(
            created_at__range=(yesterday_start, yesterday_end)
        ).count()

        if total_yesterday > 0:
            percentage_change = (
                (total_today - total_yesterday) / total_yesterday
            ) * 100
        else:
            percentage_change = 0

        statistics = {
            'total_enquiries': {
                'today': total_today,
                'yesterday': total_yesterday,
                'percentage_change': round(percentage_change, 2),
            },
            'by_status': {
                'new': ErpEnquiry.objects.filter(status='new').count(),
                'reviewed': ErpEnquiry.objects.filter(status='reviewed').count(),
                'responded': ErpEnquiry.objects.filter(status='responded').count(),
            }
        }

        return Response(statistics, status=status.HTTP_200_OK)

