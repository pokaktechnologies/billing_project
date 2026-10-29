from datetime import datetime
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_logs.base_view import BaseAPIView
from ..models import ClientContract
from ..serializers import ClientContractSerializer
from .pagination import ReportPagination


class ClientContractView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        contracts = ClientContract.objects.all().order_by('-created_at')
        serializer = ClientContractSerializer(contracts, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = ClientContractSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {"status": "1", "message": "Contract created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Contract creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class ClientContractDetailView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_contract(self, pk, user):
        try:
            return ClientContract.objects.get(pk=pk)
        except ClientContract.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        contract = self.get_contract(pk, request.user)
        if not contract:
            return Response(
                {"status": "0", "message": "Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClientContractSerializer(contract)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        contract = self.get_contract(pk, request.user)
        if not contract:
            return Response(
                {"status": "0", "message": "Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClientContractSerializer(contract, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Contract updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Contract update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        contract = self.get_contract(pk, request.user)
        if not contract:
            return Response(
                {"status": "0", "message": "Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        contract.delete()
        return Response(
            {"status": "1", "message": "Contract deleted successfully"},
            status=status.HTTP_200_OK
        )


class ContractReportView(APIView):
    def get(self, request):
        contract_date_from = request.query_params.get('contract_date_from')
        contract_date_to = request.query_params.get('contract_date_to')
        search = request.query_params.get('search')

        contracts = ClientContract.objects.select_related(
            'client'
        ).order_by('-created_at')

        # SEARCH FILTER
        if search:
            contracts = contracts.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(contract_name__icontains=search)
            )

        # DATE FILTER
        if contract_date_from and contract_date_to:
            try:
                contract_date_from = datetime.strptime(contract_date_from, "%Y-%m-%d").date()
                contract_date_to = datetime.strptime(contract_date_to, "%Y-%m-%d").date()

                contracts = contracts.filter(
                    contract_date__range=[contract_date_from, contract_date_to]
                )

            except ValueError:
                return Response({
                    "status": "0",
                    "message": "Invalid date format. Use YYYY-MM-DD"
                })

        paginator = ReportPagination()
        paginated_qs = paginator.paginate_queryset(contracts, request)
        if paginated_qs is not None:
            serializer = ClientContractSerializer(paginated_qs, many=True)
            return paginator.get_paginated_response({
                "status": "1",
                "message": "success",
                "data": serializer.data
            })

        serializer = ClientContractSerializer(contracts, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )
