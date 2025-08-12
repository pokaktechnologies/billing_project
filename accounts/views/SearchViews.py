from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from accounts.permissions import HasModulePermission
from accounts.models import CustomUser, ModulePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.models import *
from accounts.serializers.serializers import *
from django.db.models import Q

class QuatationSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'quotation'

    def get(self, request, format=None):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        client = request.query_params.get('client')
        search = request.query_params.get('search')  # Optional keyword search
        salesperson = request.query_params.get('salesperson')

        quotations = QuotationOrderModel.objects.all().order_by('-id')

        # Filter by date range
        if start_date and end_date:
            quotations = quotations.filter(quotation_date__range=[start_date, end_date])

        # Filter by client ID
        if client:
            quotations = quotations.filter(client__id=client)
        
        if salesperson:
            quotations = quotations.filter(client__salesperson=salesperson)

        # Optional search in client name or project name
        if search:
            quotations = quotations.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(project_name__icontains=search)
            )

        serializer = QuotationOrderSerializer(quotations, many=True)

        return Response({
            "status": "1",
            "message": "Quotations fetched successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
