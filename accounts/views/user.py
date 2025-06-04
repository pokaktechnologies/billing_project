from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from accounts.serializers.user import (
    ProfileSerializer,
    AssignPermissionSerializer,
    CreateUserWithPermissionsSerializer
)
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
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CreateUserWithPermissionsSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created and permissions assigned.",
                "user_id": user.id,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserModulesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules = ModulePermission.objects.filter(user=request.user).values_list('module_name', flat=True)
        return Response({"modules": list(modules)})