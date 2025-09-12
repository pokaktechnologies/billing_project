from rest_framework import generics, permissions, views
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.mail import EmailMessage
from django.http import HttpResponse
from .models import Certificate
from .serializers import CertificateSerializer
from accounts.permissions import HasModulePermission
from accounts.models import JobDetail, StaffProfile, CustomUser  # Import here to avoid circular imports
import base64
import logging

logger = logging.getLogger(__name__)

class CertificateListCreateView(generics.ListCreateAPIView):
    serializer_class = CertificateSerializer
    permission_classes = [HasModulePermission]

    def get_permissions(self):
        if self.request.method == 'POST':
            return []  # Allow unauthenticated POST
        return [HasModulePermission()]  # Require permission for GET
    required_module = 'certificate'

    def get_queryset(self):
        queryset = Certificate.objects.all()
        status = self.request.query_params.get('status', None)
        category = self.request.query_params.get('category', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        search = self.request.query_params.get('search', None)

        queryset = queryset.order_by('-requested_at')
        if status:
            queryset = queryset.filter(status__iexact=status)
        if category:
            queryset = queryset.filter(category__iexact=category)
        if start_date:
            queryset = queryset.filter(requested_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(requested_at__lte=end_date)
        if search:
            queryset = queryset.filter(full_name__icontains=search) | queryset.filter(email__icontains=search)
        return queryset

    def perform_create(self, serializer):
        serializer.save()

class CertificateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in partial_update for certificate {kwargs.get('pk')}: {str(e)}")
            raise

class CertificateProofView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def get(self, request, pk):
        try:
            certificate = Certificate.objects.get(pk=pk)
            if certificate.proof_document:
                return Response({"proof_document": request.build_absolute_uri(certificate.proof_document.url)})
            return Response({"proof_document": None}, status=status.HTTP_404_NOT_FOUND)
        except Certificate.DoesNotExist:
            return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)

class CertificateDataView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def get(self, request, pk):
        try:
            certificate = Certificate.objects.get(pk=pk)
            if certificate.status not in ['Approved', 'Issued'] and not certificate.is_internal:
                return Response({"error": "Only approved, issued, or internal certificates can be retrieved for generation"}, status=status.HTTP_400_BAD_REQUEST)
            data = {
                "id": certificate.id,
                "full_name": certificate.full_name,
                "designation": certificate.designation,
                "category": certificate.category,
                "start_date": certificate.start_date.isoformat(),
                "end_date": certificate.end_date.isoformat(),
                "email": certificate.email,
                "issued_date": certificate.processed_at.isoformat() if certificate.processed_at else timezone.now().isoformat()
            }
            return Response(data)
        except Certificate.DoesNotExist:
            return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)

class CertificateSendView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def post(self, request, pk):
        try:
            certificate = Certificate.objects.get(pk=pk)
            if certificate.status != 'Issued':
                return Response({"error": "Only issued certificates can be sent"}, status=status.HTTP_400_BAD_REQUEST)
            email = request.data.get('email', certificate.email)
            pdf_data = request.data.get('pdf_data')
            if not pdf_data:
                return Response({"error": "PDF data is required"}, status=status.HTTP_400_BAD_REQUEST)

            pdf_binary = base64.b64decode(pdf_data)
            email_msg = EmailMessage(
                subject=f"Certificate for {certificate.full_name}",
                body=f"Dear {certificate.full_name},\n\nPlease find your certificate attached.\n\nBest regards,\nPokak Billing Team",
                from_email='from@example.com',
                to=[email],
            )
            email_msg.attach('certificate.pdf', pdf_binary, 'application/pdf')
            email_msg.send()

            return Response({"message": "Certificate sent successfully", "certificate_id": pk})
        except Certificate.DoesNotExist:
            return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error sending certificate {pk}: {str(e)}")
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CertificateDownloadView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def post(self, request, pk):
        try:
            certificate = Certificate.objects.get(pk=pk)
            if certificate.status != 'Issued':
                return Response({"error": "Only issued certificates can be downloaded"}, status=status.HTTP_400_BAD_REQUEST)
            pdf_data = request.data.get('pdf_data')
            if not pdf_data:
                return Response({"error": "PDF data is required"}, status=status.HTTP_400_BAD_REQUEST)

            pdf_binary = base64.b64decode(pdf_data)
            response = HttpResponse(pdf_binary, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{pk}.pdf"'
            return response
        except Certificate.DoesNotExist:
            return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error downloading certificate {pk}: {str(e)}")
            return Response({"error": f"Failed to generate download: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# New Views for Staff Certificates
class StaffListView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def get(self, request):
        if not (request.user.is_superuser or (request.user.is_staff and HasModulePermission().has_permission(request, self))):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        staff = JobDetail.objects.filter(status='active').select_related('staff__user')
        staff_data = [
            {
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'designation': job.role
            }
            for job in staff
            for user in [job.staff.user] if user.is_staff
        ]
        return Response(staff_data)

class StaffDetailView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def get(self, request, id):
        if not (request.user.is_superuser or (request.user.is_staff and HasModulePermission().has_permission(request, self))):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = CustomUser.objects.get(id=id)
            staff_profile = StaffProfile.objects.get(user=user)
            job_detail = JobDetail.objects.get(staff=staff_profile)
            data = {
                'full_name': f"{user.first_name} {user.last_name}",
                'designation': job_detail.role,
                'email': user.email,
                'start_date': job_detail.start_date.isoformat()
            }
            return Response(data)
        except (CustomUser.DoesNotExist, StaffProfile.DoesNotExist, JobDetail.DoesNotExist):
            return Response({"error": "Staff details not found"}, status=status.HTTP_404_NOT_FOUND)

class EmployeeCertificateCreateView(views.APIView):
    permission_classes = [HasModulePermission]
    required_module = 'certificate'

    def post(self, request):
        if not (request.user.is_superuser or (request.user.is_staff and HasModulePermission().has_permission(request, self))):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_id = request.data.get('user_id')
            user = CustomUser.objects.get(id=user_id)
            staff_profile = StaffProfile.objects.get(user=user)
            job_detail = JobDetail.objects.get(staff=staff_profile)

            certificate_data = {
                'full_name': f"{user.first_name} {user.last_name}",
                'start_date': job_detail.start_date,
                'end_date': timezone.now().date(),  # Default to current date; can be overridden
                'designation': job_detail.role,
                'email': user.email,
                'category': request.data.get('category', 'Employee'),  # Default to 'Employee' category
                'is_internal': True,
                'employee': user,
                'status': 'Issued',  # Auto-issue for staff
                'processed_at': timezone.now()
            }
            serializer = CertificateSerializer(data=certificate_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except (CustomUser.DoesNotExist, StaffProfile.DoesNotExist, JobDetail.DoesNotExist):
            return Response({"error": "Invalid user or staff details"}, status=status.HTTP_400_BAD_REQUEST)