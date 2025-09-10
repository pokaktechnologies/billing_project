from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from accounts.serializers.user import *
from accounts.permissions import HasModulePermission
from accounts.models import CustomUser, ModulePermission , Department ,StaffProfile, JobDetail, StaffDocument
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser ,JSONParser
from django.db import transaction
from rest_framework import generics


class DepartmentView(APIView):
    permission_classes = [IsAdminUser, HasModulePermission]
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
    permission_classes = [IsAdminUser]  # Only admin can assign

    def post(self, request):
        serializer = AssignPermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Permissions assigned successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from django.db import transaction, IntegrityError

class CreateStaffWithPermissionsView(APIView):
    permission_classes = [IsAdminUser, HasModulePermission]
    required_module = 'hr_section'
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Create a new staff with user, profile, job, documents, and permissions"""

        try:
            with transaction.atomic():
                # Create user + permissions
                user_serializer = CreateUserWithPermissionsSerializer(data=request.data)
                if not user_serializer.is_valid():
                    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                user = user_serializer.save()

                # Validate unique employee_id ---
                employee_id = request.data.get("employee_id")
                if employee_id and JobDetail.objects.filter(employee_id=employee_id).exists():
                    return Response(
                        {"status": "0", "message": f"Employee ID '{employee_id}' already exists. Please use a unique ID."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create staff profile
                staff_profile = StaffProfile.objects.create(
                    user=user,
                    phone_number=request.data.get("phone_number"),
                    profile_image=request.FILES.get("profile_image"),
                    date_of_birth=request.data.get("date_of_birth"),
                    address=request.data.get("address")
                )
                

                # Optional: create job detail
                if request.data.get("employee_id"):
                    department_id = request.data.get("department")
                    department = None
                    if department_id:
                        # ✅ Friendly validation instead of DB error
                        if not Department.objects.filter(id=department_id).exists():
                            raise ValueError("Invalid department ID. Please select a valid department.")
                        department = Department.objects.get(id=department_id)

                    JobDetail.objects.create(
                        staff=staff_profile,
                        employee_id=request.data["employee_id"],
                        department=department,
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

        except ValueError as ve:
            return Response(
                {"status": "0", "message": str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except IntegrityError as ie:
            # Handle database-level unique constraints (extra safety)
            return Response(
                {"status": "0", "message": f"Database error: {str(ie)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # Log full traceback for debugging
            import traceback
            traceback.print_exc()
            return Response(
                {"status": "0", "message": "Unexpected error occurred while creating staff."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            if staff_id:
                # Single staff user
                try:
                    staff_user = CustomUser.objects.select_related('staff_profile').get(
                        id=staff_id,
                        is_staff=True,
                        is_superuser=False
                    )
                    serializer = StaffUserSerializer(staff_user)
                    return Response({"status": "1", "message": "success", "data": serializer.data})
                except CustomUser.DoesNotExist:
                    return Response({"status": "0", "message": "Staff user not found"}, status=status.HTTP_404_NOT_FOUND)

            # All staff users
            staff_users = CustomUser.objects.filter(
                is_staff=True,
                is_superuser=False
            ).select_related('staff_profile').prefetch_related(
                'module_permissions'
            ).order_by('-id')

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
    permission_classes = [IsAdminUser, HasModulePermission]
    required_module = 'hr_section'
    queryset = CustomUser.objects.filter(is_staff=True, is_superuser=False)
    serializer_class = StaffUserUpdateSerializer
    lookup_field = "id"
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class UpdateJobDetailView(generics.UpdateAPIView):
    permission_classes = [IsAdminUser, HasModulePermission]
    required_module = 'hr_section'
    queryset = JobDetail.objects.all()
    serializer_class = JobDetailUpdateSerializer
    lookup_field = "id"   


# Add a new document
class StaffDocumentCreateView(generics.CreateAPIView):
    permission_classes = [IsAdminUser, HasModulePermission]
    required_module = 'hr_section'    
    serializer_class = StaffDocumentSerializer
    # permission_classes = [permissions.IsAuthenticated]

class StaffDocumentUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAdminUser, HasModulePermission]
    required_module = 'hr_section'
    queryset = StaffDocument.objects.all()
    serializer_class = StaffDocumentSerializer
    lookup_field = "id"   

class StaffDocumentDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdminUser, HasModulePermission]
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
        


class ListStaffView(APIView):
    permission_classes = [IsAdminUser]

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
    
    