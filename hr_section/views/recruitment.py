from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination

from accounts.permissions import HasModulePermission
from activity_logs.base_view import BaseAPIView
from ..models import (
    Designation,
    JobPosting,
    JobApplication,
)
from ..serializers import (
    DesignationSerializer,
    JobPostingSerializer,
    JobPostingListSerializer,
    JobPostingCreateSerializer,
    JobApplicationSerializer,
    JobApplicationWithoutJobSerializer,
    JobApplicationDisplaySerializer,
    JobApplicationListSerializer,
    JobApplicationStatusUpdateSerializer,
)


class DesignationView(BaseAPIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAuthenticated(), HasModulePermission()]

    def get(self, request):
        designations = Designation.objects.all()
        serializer = DesignationSerializer(designations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DesignationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DesignationDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get_object(self, pk):
        return get_object_or_404(Designation, pk=pk)

    def get(self, request, pk):
        designation = self.get_object(pk)
        serializer = DesignationSerializer(designation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        designation = self.get_object(pk)
        serializer = DesignationSerializer(designation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        designation = self.get_object(pk)
        designation.delete()
        return Response(
            {'message': 'Designation deleted successfully'},
            status=status.HTTP_200_OK
        )


class JobPostingView(BaseAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request):
        job_postings = JobPosting.objects.all().order_by('-created_at')
        serializer = JobPostingSerializer(job_postings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = JobPostingCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({'message': 'Job created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobPostingDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get_object(self, pk):
        return get_object_or_404(JobPosting, pk=pk)

    def get(self, request, pk):
        job_posting = self.get_object(pk)
        serializer = JobPostingSerializer(job_posting)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        job_posting = self.get_object(pk)
        serializer = JobPostingCreateSerializer(job_posting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Job updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        job_posting = self.get_object(pk)
        job_posting.delete()
        return Response({'message': 'Job deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class JobPostingDisplayForUserView(APIView):
    def get(self, request, job_id=None):
        if job_id is not None:
            job_posting = get_object_or_404(JobPosting, id=job_id, status='active')
            serializer = JobPostingSerializer(job_posting)
        else:
            job_postings = JobPosting.objects.filter(status='active').order_by('-created_at')
            serializer = JobPostingListSerializer(job_postings, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class JobPostingStats(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        total_openings = JobPosting.objects.count()
        total_active_jobs = JobPosting.objects.filter(status='active').count()

        today_posting_count = JobPosting.objects.filter(
            created_at__gte=start_of_day,
            created_at__lt=end_of_day
        ).count()

        return Response({
            "total_openings": total_openings,
            "total_active_jobs": total_active_jobs,
            "today_posting_count": today_posting_count,
        })


class JobApplicationView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, job_id):
        job_posting = get_object_or_404(JobPosting, id=job_id)
        serializer = JobApplicationSerializer(
            data=request.data,
            context={'job': job_posting}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application submitted successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationWithoutJob(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = JobApplicationWithoutJobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application submitted successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationPagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        page_size = request.query_params.get('page_size')
        if page_size is None:
            return None
        return int(page_size)


class JobApplicationListView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request):
        applications = JobApplication.objects.all().order_by('-applied_at')
        
        paginator = JobApplicationPagination()
        result_page = paginator.paginate_queryset(applications, request)

        if result_page is not None:
            serializer = JobApplicationListSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = JobApplicationListSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JobApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request, application_id):
        application = get_object_or_404(JobApplication, id=application_id)
        serializer = JobApplicationDisplaySerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JobApplicationStatusUpdateView(BaseAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def patch(self, request, application_id):
        application = get_object_or_404(JobApplication, id=application_id)
        serializer = JobApplicationStatusUpdateSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application status updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request):
        name = request.query_params.get('name', '')
        email = request.query_params.get('email', '')
        phone = request.query_params.get('phone', '')
        status_filter = request.query_params.get('status', '')
        designation = request.query_params.get('designation', '')
        sort = request.query_params.get('sort', '-applied_at')
        job = request.query_params.get('job', '')

        applications = JobApplication.objects.all()

        if name:
            applications = applications.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )

        if email:
            applications = applications.filter(email__icontains=email)

        if phone:
            applications = applications.filter(phone__icontains=phone)

        if status_filter:
            applications = applications.filter(status=status_filter)

        if designation:
            applications = applications.filter(designation_id=designation)

        if job == 'null':
            applications = applications.filter(job__isnull=True)
        elif job not in ['', 'all', None]:
            try:
                job_id = int(job)
                applications = applications.filter(job__id=job_id)
            except ValueError:
                pass

        applications = applications.order_by(sort)

        paginator = JobApplicationPagination()
        result_page = paginator.paginate_queryset(applications, request)
        if result_page is not None:
            serializer = JobApplicationListSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = JobApplicationListSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JobApplicationStatsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request):
        try:
            local_now = timezone.localtime()

            start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_yesterday = start_of_today - timedelta(days=1)
            start_of_week = start_of_today - timedelta(days=start_of_today.weekday())

            base_queryset = JobApplication.objects.select_related('designation')

            today_count = base_queryset.filter(
                applied_at__gte=start_of_today,
                applied_at__lt=start_of_today + timedelta(days=1)
            ).count()

            yesterday_count = base_queryset.filter(
                applied_at__gte=start_of_yesterday,
                applied_at__lt=start_of_today
            ).count()

            if yesterday_count > 0:
                percentage_change = round(
                    ((today_count - yesterday_count) / yesterday_count) * 100, 2
                )
            else:
                percentage_change = 100.0 if today_count > 0 else 0.0

            most_designation = (
                base_queryset
                .exclude(
                    Q(designation__isnull=True) |
                    Q(designation__name__isnull=True) |
                    Q(designation__name__exact='') |
                    Q(designation__name__exact=' ')
                )
                .values('designation_id', 'designation__name')
                .annotate(total_count=Count('id'))
                .order_by('-total_count')
                .first()
            )

            if most_designation:
                designation_id = most_designation['designation_id']
                designation_name = most_designation['designation__name'].strip()
                total_designation_count = most_designation['total_count']

                this_week_for_designation = base_queryset.filter(
                    designation_id=designation_id,
                    applied_at__gte=start_of_week,
                    applied_at__lte=local_now
                ).count()
            else:
                designation_name = "No designation data"
                total_designation_count = 0
                this_week_for_designation = 0

            shortlisted_this_week = base_queryset.filter(
                status='shortlisted',
                applied_at__gte=start_of_week,
                applied_at__lte=local_now
            ).count()

            stats = {
                "new_applications_today": {
                    "count": today_count,
                    "percentage_change": percentage_change
                },
                "most_applied_designation": {
                    "name": designation_name,
                    "count": total_designation_count,
                    "applications_this_week": this_week_for_designation
                },
                "shortlisted_this_week": shortlisted_this_week
            }

            return Response(stats, status=status.HTTP_200_OK)

        except Exception:
            return Response({
                "error": "Unable to calculate statistics",
                "new_applications_today": {"count": 0, "percentage_change": 0},
                "most_applied_designation": {"name": "Error", "count": 0, "applications_this_week": 0},
                "shortlisted_this_week": 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

