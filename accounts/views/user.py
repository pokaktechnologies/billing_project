from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.serializers.user import *
from accounts.permissions import HasModulePermission
from accounts.models import CustomUser, ModulePermission , Department ,StaffProfile, JobDetail, StaffDocument , SalesPerson
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser ,JSONParser
from django.db import transaction
from rest_framework import generics
from django.core.mail import send_mail
import random
from django.conf import settings
from django.db.models import Q

from attendance.models import DailyAttendance
from attendance.serializers import DailyAttendanceSessionDetailSerializer
from django.utils.dateparse import parse_date
from datetime import datetime



class DepartmentView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    def get(self, request):
        """List all departments"""
        departments = Department.objects.all().order_by('-id')
        serializer = DepartmentSerializer(departments, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        """Create a new department"""
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Department created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"status": "0", "message": "Validation error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, department_id=None):
        """Partially update an existing department"""
        department = get_object_or_404(Department, id=department_id)
        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Department updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"status": "0", "message": "Validation error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, department_id=None):
        """Delete a department"""
        department = get_object_or_404(Department, id=department_id)
        department.delete()
        return Response(
            {"status": "1", "message": "Department deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

    

class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = ProfileSerializer(user)
        return Response({"status": "1", "message": "success", "data": [serializer.data]})


class AssignPermissionView(APIView):
    permission_classes = [IsAuthenticated]  # Only admin can assign

    def post(self, request):
        serializer = AssignPermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Permissions assigned successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from django.db import transaction, IntegrityError
import traceback
class CreateStaffWithPermissionsView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Create a new staff with user, profile, job, documents, and permissions"""

        # --- 1. Validate user serializer first ---
        user_serializer = CreateUserWithPermissionsSerializer(data=request.data)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # --- 2. Pre-validate employee_id ---
        employee_id = request.data.get("employee_id")
        if employee_id and JobDetail.objects.filter(employee_id=employee_id).exists():
            return Response(
                {"status": "0", "message": f"Employee ID '{employee_id}' already exists. Please use a unique ID."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- 3. Pre-validate department ---
        department_id = request.data.get("department")
        department = None
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
            except Department.DoesNotExist:
                return Response(
                    {"status": "0", "message": "Invalid department ID. Please select a valid department."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # --- 4. Create objects inside a transaction ---
        try:
            with transaction.atomic():
                # Create user
                user = user_serializer.save()

                # Create staff profile
                staff_profile = StaffProfile.objects.create(
                    user=user,
                    phone_number=request.data.get("phone_number"),
                    staff_email=request.data.get("staff_email"),
                    profile_image=request.FILES.get("profile_image"),
                    date_of_birth=request.data.get("date_of_birth"),
                    address=request.data.get("address")
                )

                # Create job detail if provided
                if employee_id:
                    JobDetail.objects.create(
                        staff=staff_profile,
                        employee_id=employee_id,
                        department=department,
                        job_type=request.data.get("job_type"),
                        signature_image=request.FILES.get("signature_image"),
                        role=request.data.get("role"),
                        salary=request.data.get("salary"),
                        start_date=request.data.get("start_date"),
                        status=request.data.get("status", "active"),
                    )

                # Handle multiple documents
                i = 0
                while True:
                    doc_type = request.data.get(f"documents[{i}][doc_type]")
                    file = request.FILES.get(f"documents[{i}][file]")
                    if not (doc_type or file):
                        break
                    if file:
                        StaffDocument.objects.create(
                            staff=staff_profile,
                            doc_type=doc_type or "Other",
                            file=file
                        )
                    i += 1

        except IntegrityError as ie:
            # Handle database-level unique constraints safely
            return Response(
                {"status": "0", "message": f"Database error: {str(ie)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # Log full traceback for debugging
            traceback.print_exc()
            return Response(
                {"status": "0", "message": "Unexpected error occurred while creating staff."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # --- 5. Success response ---
        return Response(
            {
                "status": "1",
                "message": "Staff created successfully with all details.",
                "user_id": user.id,
                "email": user.email
            },
            status=status.HTTP_201_CREATED
        )

    def get(self, request, staff_id=None):
        department = request.query_params.get('department')
        status = request.query_params.get('status')
        search = request.query_params.get('search')  # name/email/employee_id
        job_type = request.query_params.get('job_type')

        # ===========================
        #  SINGLE STAFF
        # ===========================
        if staff_id:
            try:
                staff_user = CustomUser.objects.select_related(
                    'staff_profile',
                    'staff_profile__job_detail'
                ).get(
                    id=staff_id,
                    is_staff=True,
                    is_superuser=False
                )
                serializer = StaffUserSerializer(staff_user)
                return Response({"status": "1", "message": "success", "data": serializer.data})
            except CustomUser.DoesNotExist:
                return Response({"status": "0", "message": "Staff user not found"},
                                status=status.HTTP_404_NOT_FOUND)

        # ===========================
        #  STAFF LIST + FILTERS
        # ===========================
        staff_users = CustomUser.objects.filter(
            is_staff=True,
            is_superuser=False
        ).select_related(
            'staff_profile',
            'staff_profile__job_detail',
            'staff_profile__job_detail__department'
        ).prefetch_related(
            'module_permissions'
        ).order_by('-id')

        # Filter: department
        if department:
            staff_users = staff_users.filter(
                staff_profile__job_detail__department__id=department
            )

        # Filter: status
        if status:
            staff_users = staff_users.filter(
                staff_profile__job_detail__status=status
            )

        # Filter: name/email/employee_id
        if search:
            staff_users = staff_users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(staff_profile__job_detail__employee_id__icontains=search)
            )

        # Filter: job_type
        if job_type:
            staff_users = staff_users.filter(
                staff_profile__job_detail__job_type__iexact=job_type
            )

        serializer = StaffUserSerializer(staff_users, many=True)

        return Response({"status": "1", "message": "success", "data": serializer.data})

                   


    def delete(self, request, staff_id=None):
        if not staff_id:
            return Response({"status": "0", "message": "Staff ID is required for deletion."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staff_user = CustomUser.objects.get(id=staff_id, is_staff=True, is_superuser=False)
            staff_user.delete()
            return Response({"status": "1", "message": "Staff user deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"status": "0", "message": "Staff user not found."}, status=status.HTTP_200_OK)



#  update
class UpdateStaffUserView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    queryset = CustomUser.objects.filter(is_staff=True, is_superuser=False)
    serializer_class = StaffUserUpdateSerializer
    lookup_field = "id"
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class UpdateJobDetailView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    queryset = JobDetail.objects.all()
    serializer_class = JobDetailUpdateSerializer
    lookup_field = "id"   


# Add a new document
class StaffDocumentCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'    
    serializer_class = StaffDocumentSerializer
    # permission_classes = [permissions.IsAuthenticated]

class StaffDocumentUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    queryset = StaffDocument.objects.all()
    serializer_class = StaffDocumentSerializer
    lookup_field = "id"   

class StaffDocumentDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'hr_section'
    serializer_class = StaffDocumentSerializer
    queryset = StaffDocument.objects.all()
    lookup_field = "id"

class UserModulePermissionUpdateView(generics.GenericAPIView):
    serializer_class = ModulePermissionSerializer

    def patch(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        modules = request.data.get('modules', [])  # Expecting a list of module names

        # Delete existing permissions
        ModulePermission.objects.filter(user=user).delete()

        # Create new permissions
        new_permissions = [ModulePermission(user=user, module_name=mod) for mod in modules]
        ModulePermission.objects.bulk_create(new_permissions)

        return Response({"detail": "Permissions updated successfully."}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    # permission_classes = [IsAuthenticated]

    def patch(self, request):

        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Use the target_user set in the serializer
        user = serializer.context['target_user']
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"detail": f"Password updated successfully for {user.email}."}, status=200)



class AdminForgotPasswordRequestView(APIView):
    """Generate OTP and send to admin user's email"""

    def post(self, request):
        from accounts.serializers.user import AdminForgotPasswordRequestSerializer

        serializer = AdminForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.context['target_user']

        # generate otp
        otp = str(random.randint(10000, 99999))

        print(otp)

        user.otp = otp
        user.is_otp_verified = False
        user.save(update_fields=['otp', 'is_otp_verified'])

        # send email
        subject = "Password Reset OTP"
        message = f"Your OTP for admin password reset is {otp}."
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        try:
            send_mail(subject, message, from_email, [user.email], fail_silently=False)
        except Exception:
            # If email sending fails, still return success with a message advising to check email backend
            return Response({"detail": "OTP generated and stored. Failed to send email; check email backend."}, status=status.HTTP_200_OK)

        return Response({"detail": "OTP sent to admin email."}, status=status.HTTP_200_OK)


class AdminForgotPasswordVerifyView(APIView):
    """Verify OTP for admin user"""

    def post(self, request):
        from accounts.serializers.user import AdminForgotPasswordVerifySerializer

        serializer = AdminForgotPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.context['target_user']
        # Mark as verified
        user.is_otp_verified = True
        user.save(update_fields=['is_otp_verified'])

        return Response({"detail": "OTP verified. You can now reset the password."}, status=status.HTTP_200_OK)


class AdminForgotPasswordResetView(APIView):
    """Reset password for admin after OTP verification"""

    def post(self, request):
        from accounts.serializers.user import AdminForgotPasswordResetSerializer

        serializer = AdminForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.context['target_user']

        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        # clear otp flags
        user.otp = None
        user.is_otp_verified = False
        user.save(update_fields=['password', 'otp', 'is_otp_verified'])

        return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)


class StaffModulesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_superuser:
            # Return all possible modules if user is admin
            all_modules = [choice[0] for choice in ModulePermission.MODULE_CHOICES]
            # all_modules.append("users")
            return Response({"modules": all_modules})
        else:
            modules = ModulePermission.objects.filter(user=request.user).values_list('module_name', flat=True)
            return Response({"modules": list(modules)})


class StaffModulesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        all_modules = [choice[0] for choice in ModulePermission.MODULE_CHOICES]
        # all_modules.append("users")
        return Response({"modules": all_modules})


class ListStaffView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, staff_id=None):
        if staff_id:
            # If staff_id is provided, return details of that specific staff member
            try:
                staff_user = CustomUser.objects.get(id=staff_id, is_staff=True, is_superuser=False)
                data = {
                    "id": staff_user.id,
                    "email": staff_user.email,
                    "first_name": staff_user.first_name,
                    "last_name": staff_user.last_name,
                    "modules": [mp.module_name for mp in ModulePermission.objects.filter(user=staff_user)]
                }
                return Response({"status": "1", "message": "success", "data": data})
            except CustomUser.DoesNotExist:
                return Response({"status": "0", "message": "Staff user not found"}, status=status.HTTP_404_NOT_FOUND)
        staff_users = CustomUser.objects.filter(is_staff=True, is_superuser=False).values('id', 'email', 'first_name', 'last_name')
        return Response({"status": "1", "message": "success", "data": list(staff_users)})
    
class StaffPersonalInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_staff:
            serializer = StaffPersonalInfoSerializer(user)
            return Response({"status": "1", "message": "success", "data": serializer.data})
        return Response({"status": "0", "message": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

class StaffPersonalAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        user = request.user
        if user.is_staff:
            # validation check start_date <= end_date
            if start_date and end_date:
                start = parse_date(start_date)
                end = parse_date(end_date)  
                if start > end:
                    raise ValidationError("Start date cannot be after end date.")
                
            queryset = DailyAttendance.objects.filter(staff__id=user.staff_profile.id).order_by('-date')

            if start_date:
                queryset = queryset.filter(date__gte=start)
            if end_date:
                queryset = queryset.filter(date__lte=end)
            # Get staff start date from JobDetail
            start_date_str = StaffPersonalInfoSerializer(user).data.get('profile', {}).get('job_detail', {}).get('start_date')
            
            # Convert string to datetime object
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            today = datetime.today().date()

            # Calculate difference in days
            total_days = (today - start_date).days

            # 👇 status field in model is `leave`, `half_day`, `full_day`
            present_days = queryset.filter(status='full_day').count()
            absent_days = queryset.filter(status='leave').count()
            half_days = queryset.filter(status='half_day').count()

            days_count = {
                    "total_days": total_days,
                    "present_days": present_days,
                    "half_days": half_days,
                    "absent_days": absent_days,
            }
                
            serializer = DailyAttendanceSessionDetailSerializer(queryset, many=True)
            return Response({"days_count":days_count,"session_data": serializer.data}, status=200)
        return Response({"status": "0", "message": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)


# list all staff users that not assigned to salesperson
class UnassignedStaffListView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request):

        # 1️⃣ Get all staff IDs already assigned to a SalesPerson
        assigned_staff_ids = SalesPerson.objects.filter(
            assigned_staff__isnull=False
        ).values_list('assigned_staff_id', flat=True)

        # 2️⃣ Get all staff that are NOT assigned
        unassigned_staff = StaffProfile.objects.exclude(
            id__in=assigned_staff_ids
        )

        # 3️⃣ Convert staff → CustomUser for serializer (your serializer expects user)
        users = CustomUser.objects.filter(
            staff_profile__in=unassigned_staff
        )

        serializer = StaffUserSerializer(users, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        })
