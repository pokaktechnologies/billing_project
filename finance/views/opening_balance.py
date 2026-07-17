from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from activity_logs.base_view import BaseGenericAPIView

from ..models import Account, FinancialYear,AccountOpeningBalance, JournalEntry
from ..serializers.opening_balance import (
    FinancialYearSerializer,
    OpeningBalanceDashboardSerializer,
    OpeningBalanceBulkUpdateSerializer,
)

class OpeningBalanceDashboardAPIView(BaseGenericAPIView, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        financial_year_id = request.query_params.get("financial_year")
        account_type = request.query_params.get("type")
        if not financial_year_id:
            return Response(
                {
                    "detail": "Financial Year is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            financial_year = FinancialYear.objects.get(
                id=financial_year_id
            )
        except FinancialYear.DoesNotExist:

            return Response(
                {
                    "detail": "Financial Year not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
        queryset = Account.objects.filter(
            is_posting=True,
            status="active"
        ).order_by("account_number")
        if account_type:
            queryset = queryset.filter(type=account_type)
        serializer = OpeningBalanceDashboardSerializer(
            queryset,
            many=True,
            context={
                "financial_year": financial_year
            }
        )
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):

        serializer = OpeningBalanceBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "status": "1",
                "detail": "Opening balances updated successfully."
            },
            status=status.HTTP_200_OK
        )


class FinancialYearListCreateAPIView(BaseGenericAPIView, generics.ListCreateAPIView):
    queryset = FinancialYear.objects.all().order_by("-start_date")
    serializer_class = FinancialYearSerializer
    permission_classes = [IsAuthenticated]

class FinancialYearRetrieveUpdateDestroyAPIView(BaseGenericAPIView, generics.RetrieveUpdateDestroyAPIView):
    queryset = FinancialYear.objects.all()
    serializer_class = FinancialYearSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):

        financial_year = self.get_object()

        # Check Journal Entries
        if JournalEntry.objects.filter(
            date__date__gte=financial_year.start_date,
            date__date__lte=financial_year.end_date,
        ).exists():

            return Response(
                {
                    "status": "0",
                    "detail": (
                        "This financial year cannot be deleted because "
                        "journal entries already exist."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)