from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_date
from ..services.reports import (
    get_profit_and_loss_data,
    get_trial_balance_data,
    get_balance_sheet_data,
    get_cashflow_statement_data
)

class ProfitAndLossView(APIView):
    def get(self, request):
        from_date = parse_date(request.GET.get("from_date", "2024-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))
        data = get_profit_and_loss_data(from_date, to_date)
        return Response(data)

class TrialBalanceView(APIView):
    def get(self, request):
        from_date = parse_date(request.GET.get("from_date", "2024-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))
        data = get_trial_balance_data(from_date, to_date)
        return Response(data)

class BalanceSheetView(APIView):
    def get(self, request):
        from_date = parse_date(request.GET.get("from_date", "2025-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))
        net_profit = request.GET.get("net_profit", 0)
        data = get_balance_sheet_data(from_date, to_date, net_profit)
        return Response([data])

class CashflowStatementView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        data = get_cashflow_statement_data(from_date, to_date)
        return Response(data)
