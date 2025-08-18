from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from accounts.serializers.user import (
    ProfileSerializer,
    AssignPermissionSerializer,
    CreateUserWithPermissionsSerializer
)
from accounts.permissions import HasModulePermission
from accounts.models import CustomUser, ModulePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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
    


class CreateStaffWithPermissionsView(APIView):
    permission_classes = [IsAdminUser, HasModulePermission]
    required_module = 'setup'
    def post(self, request):
        serializer = CreateUserWithPermissionsSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "status": "1",
                "message": "User created and permissions assigned.",
                "user_id": user.id,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
                return Response({"status": "0", "message": "Staff user not found"}, status=status.HTTP_200_OK)
        staff_users = CustomUser.objects.filter(is_staff=True, is_superuser=False).values('id', 'email', 'first_name', 'last_name')
        return Response({"status": "1", "message": "success", "data": list(staff_users)})
    
    
    def patch(self, request, staff_id=None):
        if not staff_id:
            return Response({"error": "Staff ID is required for update."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staff_user = CustomUser.objects.get(id=staff_id, is_staff=True, is_superuser=False)
        except CustomUser.DoesNotExist:
            return Response({"error": "Staff user not found."}, status=status.HTTP_200_OK)

        # Partial update
        data = request.data
        staff_user.first_name = data.get("first_name", staff_user.first_name)
        staff_user.last_name = data.get("last_name", staff_user.last_name)
        password = data.get("password")
        if password:
            staff_user.set_password(password)
        staff_user.save()

        # Update permissions
        modules = data.get("modules")
        if modules is not None:
            ModulePermission.objects.filter(user=staff_user).delete()
            ModulePermission.objects.bulk_create([
                ModulePermission(user=staff_user, module_name=module)
                for module in modules
            ])
        
        data = {
            "id": staff_user.id,
            "email": staff_user.email,
            "first_name": staff_user.first_name,
            "last_name": staff_user.last_name,
            "modules": [mp.module_name for mp in ModulePermission.objects.filter(user=staff_user)]
        }

        return Response({"status": "1", "message": "Staff user updated successfully.", "data": data}, status=status.HTTP_200_OK)
    
    def delete(self, request, staff_id=None):
        if not staff_id:
            return Response({"status": "0", "message": "Staff ID is required for deletion."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staff_user = CustomUser.objects.get(id=staff_id, is_staff=True, is_superuser=False)
            staff_user.delete()
            return Response({"status": "1", "message": "Staff user deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"status": "0", "message": "Staff user not found."}, status=status.HTTP_200_OK)
    

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
    
    