from django.views import View
from django.http import HttpResponse
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import *
from .serializers import *

from .utils import generate_next_number


from rest_framework import generics
from .models import Account
from .serializers import AccountSerializer
from .filters import JournalLineFlatFilter

class AccountListCreateAPIView(generics.ListCreateAPIView):
    queryset = Account.objects.all().order_by('-created_at')
    serializer_class = AccountSerializer

class AccountRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

class JournalEntryListCreateView(generics.ListCreateAPIView):
    queryset = JournalEntry.objects.all().order_by('-created_at')
    serializer_class = JournalEntrySerializer

class JournalEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

class ListJournalVoucherView(generics.ListAPIView):
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JournalEntry.objects.filter(type='journal_voucher').order_by('-created_at')

class FinaceNumberGeneratorView(APIView):
    def get(self, request):
        model_type = request.query_params.get('type')

        model_map = {
            'ACT': (Account, 'account_number', 'ACT'),
            'JE': (JournalEntry, 'type_number', 'JE'),
            'CN': (CreditNote, 'credit_note_number', 'CN'),
        }

        if model_type not in model_map:
            return Response({
                'status': '0',
                'message': 'Invalid order type',
            }, status=status.HTTP_400_BAD_REQUEST)

        model, field_name, prefix = model_map[model_type]
        number = generate_next_number(model, field_name, prefix, 6)

        return Response({
            'status': '1',
            'message': 'Success',
            'number': number
        }, status=status.HTTP_200_OK)


class JournalLineListView(generics.ListAPIView):
    serializer_class = JournalLineListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalLineFlatFilter
    def get_queryset(self):
        # Optimized: fetch related objects in one query
        return (
            JournalLine.objects
            .select_related('journal', 'journal__user', 'journal__salesperson', 'account')
            .order_by('-created_at')
        )


class JournalLineDetailView(generics.RetrieveAPIView):
    queryset = JournalLine.objects.select_related(
        'journal', 'account', 'journal__user'
    )
    serializer_class = JournalLineDetailSerializer
    lookup_field = 'id'


# Credit Note Views
class CreditNoteListCreateAPIView(generics.ListCreateAPIView):
    queryset = CreditNote.objects.all().order_by('-created_at')
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]


class CreditNoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CreditNote.objects.all()
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]




class DebitNoteListCreateAPIView(generics.ListCreateAPIView):
    queryset = DebitNote.objects.all().order_by('-created_at')
    serializer_class = DebitNoteSerializer
    permission_classes = [IsAuthenticated]


class DebitNoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DebitNote.objects.all()
    serializer_class = DebitNoteSerializer
    permission_classes = [IsAuthenticated]


# finance/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.utils.dateparse import parse_date
from decimal import Decimal
from .models import Account, JournalLine

from decimal import Decimal
from django.db.models import Sum, F
from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework.response import Response

from decimal import Decimal
from django.db.models import Sum, F
from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework.response import Response

from decimal import Decimal
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import JournalLine  # adjust import based on your project

class ProfitAndLossView(APIView):
    def get(self, request):
        # --------------------------
        # Date Range
        # --------------------------
        from_date = parse_date(request.GET.get("from_date", "2024-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))

        # --------------------------
        # Base Query
        # --------------------------
        lines = JournalLine.objects.filter(
            journal__date__range=(from_date, to_date),
            account__status='active'
        )

        # --------------------------
        # Helper function for totals
        # --------------------------
        def calc_total(account_type, is_credit_positive=True):
            """
            Calculate total for an account type.
            
            Args:
                account_type: Type of account to filter
                is_credit_positive: True if credit increases the account (Revenue/Sales)
                                   False if debit increases the account (Expenses/Cost)
            
            Returns:
                tuple: (total, breakdown_list)
            """
            qs = lines.filter(account__type=account_type)
            # For revenue accounts: credit - debit (credit increases balance)
            # For expense accounts: debit - credit (debit increases balance)
            expr = F('credit') - F('debit') if is_credit_positive else F('debit') - F('credit')
            
            total = qs.aggregate(
                total=Coalesce(Sum(expr, output_field=DecimalField()), Decimal(0))
            )['total']
            
            breakdown = list(
                qs.values('account__name')
                .annotate(amount=Coalesce(Sum(expr, output_field=DecimalField()), Decimal(0)))
                .order_by('-amount')
            )
            
            return total, breakdown

        # --------------------------
        # P&L Account Sections
        # --------------------------
        # Account Type 4: Sales (Credit increases)
        sales_total, sales_breakdown = calc_total('sales', is_credit_positive=True)
        
        # Account Type 5: Cost of Sales (Debit increases)
        cost_total, cost_breakdown = calc_total('cost_of_sales', is_credit_positive=False)
        
        # Account Type 6: Other Revenue (Credit increases)
        revenue_total, revenue_breakdown = calc_total('revenue', is_credit_positive=True)
        
        # Account Type 7: General Expenses (Debit increases)
        expense_total, expense_breakdown = calc_total('general_expenses', is_credit_positive=False)

        # --------------------------
        # Profit Calculations
        # --------------------------
        # P&L Formula:
        # Gross Profit = Sales - Cost of Sales (4 - 5)
        # Operating Profit = Gross Profit - General Expenses (GP - 7)
        # Net Profit/Loss = Operating Profit + Other Revenue (OP + 6)
        # Simplified: (4 - 5) + (6 - 7) = Net Profit/Loss
        
        gross_profit = sales_total - cost_total
        operating_profit = gross_profit - expense_total
        net_profit = operating_profit + revenue_total
        
        # Alternatively (same result):
        # net_profit = gross_profit + (revenue_total - expense_total)
        
        profit_type = "Net Profit" if net_profit >= 0 else "Net Loss"
        
        # Calculate profit margin
        total_income = sales_total + revenue_total
        profit_margin = (net_profit / total_income * 100) if total_income != 0 else 0

        # --------------------------
        # Response
        # --------------------------
        data = {
            "title": "Profit & Loss Statement",
            "period": f"{from_date} to {to_date}",
            "sales": {
                "total": float(sales_total),
                "accounts": [
                    {"name": item["account__name"], "amount": float(item["amount"])}
                    for item in sales_breakdown
                ],
            },
            "cost_of_sales": {
                "total": float(cost_total),
                "accounts": [
                    {"name": item["account__name"], "amount": float(item["amount"])}
                    for item in cost_breakdown
                ],
            },
            "gross_profit": float(gross_profit),
            "revenue": {
                "total": float(revenue_total),
                "accounts": [
                    {"name": item["account__name"], "amount": float(item["amount"])}
                    for item in revenue_breakdown
                ],
            },
            "general_expenses": {
                "total": float(expense_total),
                "accounts": [
                    {"name": item["account__name"], "amount": float(item["amount"])}
                    for item in expense_breakdown
                ],
            },
            "operating_profit": float(operating_profit),
            "summary": {
                "gross_profit": float(gross_profit),
                "operating_profit": float(operating_profit),
                "net_profit": float(net_profit),
                "type": profit_type,
                "profit_margin": round(profit_margin, 2),
            },
        }

        return Response(data)


