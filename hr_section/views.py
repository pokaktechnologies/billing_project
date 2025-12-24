from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from rest_framework import permissions, status as drf_status
from django.db.models import Count, Q, F
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta

from .models import *
from .serializers import *



# ========== Views for Enquiry ==========

class EnquiryCreateView(APIView):
    required_module = 'hr_section'

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
    required_module = 'hr_section'

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


class EnquiryStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'

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
    required_module = 'hr_section'

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
            }
            ,
            'unread_enquiries': unread_enquiries,
            'reviewed_enquiries': reviewed_enquiries,
            'responsed_enquiries': responsed_enquiries
        }

        return Response(statistics, status=status.HTTP_200_OK)




class SearchEnquiryView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'

    def get(self, request):
        client_name = request.query_params.get('client_name', '')
        email = request.query_params.get('email', '')
        phone = request.query_params.get('phone', '')
        status_filter = request.query_params.get('status', '')
        sort = request.query_params.get('sort', '-created_at')  # default: latest first

        # Start building the query
        query = Q()

        if client_name:
            query &= Q(first_name__icontains=client_name) | Q(last_name__icontains=client_name)
        if email:
            query &= Q(email__icontains=email)
        if phone:
            query &= Q(phone__icontains=phone)
        if status_filter:
            query &= Q(status__iexact=status_filter)

        # Apply filtering and sorting
        enquiries = Enquiry.objects.filter(query).order_by(sort)

        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data, status=drf_status.HTTP_200_OK)

# ========= end of Views for Enquiry ==========


# ========== Views for Designation ==========

class DesignationView(APIView):
    required_module = 'hr_section'

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



class DesignationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'

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


class JobPostingView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'

    def get(self, request):
        job_postings = JobPosting.objects.all().order_by('-created_at')
        serializer = JobPostingListSerializer(job_postings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = JobPostingCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({'message': 'Job created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobPostingDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'

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
            job_posting = get_object_or_404(JobPosting, id=job_id,status='active')
            serializer = JobPostingSerializer(job_posting)
        else:
            job_postings = JobPosting.objects.filter(status='active').order_by('-created_at')
            serializer = JobPostingListSerializer(job_postings, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
class JobPostingStats(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total_openings = JobPosting.objects.all().count()
        total_active_jobs = JobPosting.objects.filter(status='active').count()
        today_posting_count = JobPosting.objects.filter(created_at__date=timezone.now().date()).count()

        stats = {
            'total_openings': total_openings,
            'total_active_jobs': total_active_jobs,
            'today_posting_count': today_posting_count,
        }

        return Response(stats, status=status.HTTP_200_OK)


class JobApplicationView(APIView):
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


class JobApplicationWithoutJob(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = JobApplicationWithoutJobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application submitted successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationListView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    def get(self, request):
        applications = JobApplication.objects.all().order_by('-applied_at')
        serializer = JobApplicationListSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JobApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    def get(self, request, application_id):
        application = get_object_or_404(JobApplication, id=application_id)
        serializer = JobApplicationDisplaySerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)



class JobApplicationStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    def patch(self, request, application_id):
        application = get_object_or_404(JobApplication, id=application_id)
        serializer = JobApplicationStatusUpdateSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application status updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    
    def get(self, request):
        name = request.query_params.get('name', '')
        email = request.query_params.get('email', '')
        phone = request.query_params.get('phone', '')
        status_filter = request.query_params.get('status', '')
        designation = request.query_params.get('designation', '')
        sort = request.query_params.get('sort', '-applied_at')  # default sorting
        job = request.query_params.get('job', '')

        applications = JobApplication.objects.all()

        # Filter by name (first_name or last_name)
        if name:
            applications = applications.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )

        # Filter by email
        if email:
            applications = applications.filter(email__icontains=email)

        # Filter by phone
        if phone:
            applications = applications.filter(phone__icontains=phone)

        # Filter by status
        if status_filter:
            applications = applications.filter(status=status_filter)

        # Filter by designation name
        if designation:
            applications = applications.filter(designation_id=designation)
        
        # ✅ Proper job filter handling
        if job == 'null':
            applications = applications.filter(job__isnull=True)
        elif job not in ['', 'all', None]:
            try:
                job_id = int(job)
                applications = applications.filter(job__id=job_id)
            except ValueError:
                pass  # ignore invalid job value

        # Sorting
        applications = applications.order_by(sort)

        serializer = JobApplicationListSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)







class JobApplicationStatsAPIView(APIView):
    """
    API endpoint that returns job application statistics.

    Permissions:
    - Requires authentication
    - Requires 'hr_section' module access

    Returns:
        - new_applications_today: counts ALL applications created today (any status)
        - percentage_change: vs yesterday
        - most_applied_designation: all-time top designation (any status) 
        - applications_this_week: count for that designation from Monday 00:00 through now
        - shortlisted_this_week: count shortlisted from Monday 00:00 through now
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'

    def get(self, request):
        try:
            # Current local time (timezone-aware)
            local_now = timezone.localtime()

            # Date ranges
            start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_yesterday = start_of_today - timedelta(days=1)
            start_of_week = start_of_today - timedelta(days=start_of_today.weekday())

            # Base queryset
            base_queryset = JobApplication.objects.select_related('designation')

            # Applications today
            today_count = base_queryset.filter(
                applied_at__gte=start_of_today,
                applied_at__lt=start_of_today + timedelta(days=1)
            ).count()

            # Applications yesterday
            yesterday_count = base_queryset.filter(
                applied_at__gte=start_of_yesterday,
                applied_at__lt=start_of_today
            ).count()

            # Percentage change
            if yesterday_count > 0:
                percentage_change = round(
                    ((today_count - yesterday_count) / yesterday_count) * 100, 2
                )
            else:
                percentage_change = 100.0 if today_count > 0 else 0.0

            # Most applied designation
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

                # Applications this week for that designation
                this_week_for_designation = base_queryset.filter(
                    designation_id=designation_id,
                    applied_at__gte=start_of_week,
                    applied_at__lte=local_now
                ).count()
            else:
                designation_name = "No designation data"
                total_designation_count = 0
                this_week_for_designation = 0

            # Shortlisted this week
            shortlisted_this_week = base_queryset.filter(
                status='shortlisted',
                applied_at__gte=start_of_week,
                applied_at__lte=local_now
            ).count()

            # Final response
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
            # Safe fallback in case of errors
            return Response({
                "error": "Unable to calculate statistics",
                "new_applications_today": {"count": 0, "percentage_change": 0},
                "most_applied_designation": {"name": "Error", "count": 0, "applications_this_week": 0},
                "shortlisted_this_week": 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
