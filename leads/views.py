from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Lead
from .serializers import LeadSerializer

class LeadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leads = Lead.objects.filter(CustomUser=request.user)
        serializer = LeadSerializer(leads, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(CustomUser=request.user)
            return Response({
                "status": "1",
                "message": "Lead created successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "0",
            "message": "Lead creation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LeadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Lead.objects.get(pk=pk, CustomUser=user)
        except Lead.DoesNotExist:
            return None

    def get(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeadSerializer(lead)
        return Response({"status": "1", "message": "success", "data": [serializer.data]})

    def patch(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Lead updated successfully", "data": serializer.data})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            lead.delete()
        except Exception as e:
            return Response({"status": "0", "message": "Lead deletion failed", "errors": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # If deletion is successful, return a success message
        return Response({"status": "1", "message": "Lead deleted successfully"}, status=status.HTTP_200_OK)



