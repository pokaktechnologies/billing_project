# Standard library imports
from collections import defaultdict
from decimal import Decimal

# Django imports
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

# Third-party imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

# Local app imports
from .models import *
from .serializers import *
from .filters import *
from .utils import *


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



class ProfitAndLossView(APIView):
    def get(self, request):
        from_date = parse_date(request.GET.get("from_date", "2024-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))

        lines = JournalLine.objects.filter(
            journal__date__range=(from_date, to_date),
            account__status='active'
        )

        def get_balances(account_type, is_credit_positive=True):
            """
            Returns parent-child structured balances for an account type
            """
            qs = lines.filter(account__type=account_type)

            # Annotate net balance
            annotated = qs.values(
                'account__id',
                'account__name',
                'account__parent_account__id',
                'account__parent_account__name'
            ).annotate(
                debit_sum=Coalesce(Sum('debit'), Decimal(0)),
                credit_sum=Coalesce(Sum('credit'), Decimal(0))
            )

            temp_accounts = defaultdict(lambda: {})
            total = Decimal(0)

            for item in annotated:
                debit = item['debit_sum']
                credit = item['credit_sum']
                net_debit = max(debit - credit, Decimal(0))
                net_credit = max(credit - debit, Decimal(0))
                net_amount = net_credit - net_debit if is_credit_positive else net_debit - net_credit

                total += net_amount

                account_data = {
                    "account": item['account__name'],
                    "amount": float(net_amount)
                }

                parent_name = item['account__parent_account__name']
                if parent_name:
                    if 'children' not in temp_accounts[parent_name]:
                        temp_accounts[parent_name]['children'] = []
                    temp_accounts[parent_name]['children'].append(account_data)
                else:
                    temp_accounts[item['account__name']] = {
                        "balance": account_data,
                        "children": temp_accounts.get(item['account__name'], {}).get('children', [])
                    }

            structured = []
            for parent_name, data in temp_accounts.items():
                structured.append({
                    "parent": parent_name,
                    "balance": data.get('balance', {"account": parent_name, "amount": 0}),
                    "children": data.get('children', [])
                })

            return float(total), structured

        # P&L Sections
        sales_total, sales_accounts = get_balances('sales', is_credit_positive=True)
        cost_total, cost_accounts = get_balances('cost_of_sales', is_credit_positive=False)
        revenue_total, revenue_accounts = get_balances('revenue', is_credit_positive=True)
        expense_total, expense_accounts = get_balances('general_expenses', is_credit_positive=False)

        gross_profit = sales_total - cost_total
        operating_profit = gross_profit - expense_total
        net_profit = operating_profit + revenue_total
        profit_type = "Net Profit" if net_profit >= 0 else "Net Loss"
        total_income = sales_total + revenue_total
        profit_margin = (net_profit / total_income * 100) if total_income != 0 else 0

        data = {
            "title": "Profit & Loss Statement",
            "period": f"{from_date} to {to_date}",
            "sales": {"total": sales_total, "accounts": sales_accounts},
            "cost_of_sales": {"total": cost_total, "accounts": cost_accounts},
            "gross_profit": gross_profit,
            "revenue": {"total": revenue_total, "accounts": revenue_accounts},
            "general_expenses": {"total": expense_total, "accounts": expense_accounts},
            "operating_profit": operating_profit,
            "summary": {
                "gross_profit": gross_profit,
                "operating_profit": operating_profit,
                "net_profit": net_profit,
                "type": profit_type,
                "profit_margin": round(profit_margin, 2),
            }
        }

        return Response(data)



class TrialBalanceView(APIView):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('sales', 'Sales'),
        ('cost_of_sales', 'Cost of Sales'),
        ('revenue', 'Revenue'),
        ('general_expenses', 'General Expenses'),
    ]

    def get(self, request):
        from_date = parse_date(request.GET.get("from_date", "2024-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))

        # Fetch posted journal lines
        lines = JournalLine.objects.filter(
            journal__date__range=(from_date, to_date),
            account__status='active'
        )

        # Group balances by account
        balances = (
            lines
            .values(
                'account__id',
                'account__name',
                'account__type',
                'account__parent_account__id',
                'account__parent_account__name'
            )
            .annotate(
                debit_sum=Coalesce(Sum('debit'), Decimal(0)),
                credit_sum=Coalesce(Sum('credit'), Decimal(0))
            )
        )

        # Organize by account type with parent-child logic
        grouped = defaultdict(list)
        total_debit = Decimal(0)
        total_credit = Decimal(0)

        # Temporary structure to store parent balances and children
        temp_accounts = defaultdict(lambda: {})

        for item in balances:
            debit = item['debit_sum']
            credit = item['credit_sum']

            # Calculate net balance
            net_debit = max(debit - credit, Decimal(0))
            net_credit = max(credit - debit, Decimal(0))

            total_debit += net_debit
            total_credit += net_credit

            account_data = {
                "account": item['account__name'],
                "debit": float(net_debit),
                "credit": float(net_credit)
            }

            parent_name = item['account__parent_account__name']
            if parent_name:
                # Child account
                if 'children' not in temp_accounts[parent_name]:
                    temp_accounts[parent_name]['children'] = []
                temp_accounts[parent_name]['children'].append(account_data)
            else:
                # Parent account itself
                temp_accounts[item['account__name']] = {
                    "balance": account_data,
                    "children": temp_accounts.get(item['account__name'], {}).get('children', [])
                }

        # Convert temp_accounts to final grouped format
        for code, label in self.ACCOUNT_TYPES:
            accounts_list = []
            for parent_name, data in temp_accounts.items():
                accounts_list.append({
                    "parent": parent_name,
                    "balance": data.get('balance', {"account": parent_name, "debit": 0, "credit": 0}),
                    "children": data.get('children', [])
                })
            grouped[label] = accounts_list

        data = {
            "title": "Trial Balance",
            "period": f"{from_date} to {to_date}",
            "accounts_by_type": [{"type": k, "accounts": v} for k, v in grouped.items()],
            "totals": {
                "total_debit": float(total_debit),
                "total_credit": float(total_credit),
                "balanced": round(total_debit, 2) == round(total_credit, 2)
            }
        }

        return Response(data)


class BalanceSheetView(APIView):
    def get(self, request):
        from_date = parse_date(request.GET.get("from_date", "2025-01-01"))
        to_date = parse_date(request.GET.get("to_date", "2025-12-31"))
        net_profit = Decimal(request.GET.get("net_profit", 0))

        lines = JournalLine.objects.filter(
            journal__date__range=(from_date, to_date),
            account__status='active'
        )

        def get_balances(account_type):
            qs = lines.filter(account__type=account_type)
            annotated = qs.values(
                'account__id',
                'account__name',
                'account__parent_account__id',
                'account__parent_account__name'
            ).annotate(
                debit_sum=Coalesce(Sum('debit'), Decimal(0)),
                credit_sum=Coalesce(Sum('credit'), Decimal(0))
            )

            accounts_map = defaultdict(lambda: {"children": []})
            total = Decimal(0)

            for item in annotated:
                debit = item['debit_sum']
                credit = item['credit_sum']
                net_amount = credit - debit if account_type in ['liability', 'equity'] else debit - credit
                total += net_amount

                acc_id = item['account__id']
                acc_name = item['account__name']
                parent_id = item['account__parent_account__id']
                parent_name = item['account__parent_account__name']

                acc_data = {"account": acc_name, "amount": float(net_amount)}

                if parent_id:
                    accounts_map[parent_id]["children"].append(acc_data)
                    if "balance" not in accounts_map[parent_id]:
                        accounts_map[parent_id]["balance"] = {"account": parent_name, "amount": 0}
                else:
                    accounts_map[acc_id]["balance"] = acc_data

            structured = []
            for acc_id, data in accounts_map.items():
                structured.append({
                    "parent": data["balance"]["account"],
                    "balance": data["balance"],
                    "children": data.get("children", [])
                })

            return float(total), structured

        # Get totals and account structures
        assets_total, assets_accounts = get_balances('asset')
        liabilities_total, liabilities_accounts = get_balances('liability')
        equity_total, equity_accounts = get_balances('equity')

        # Add net profit into equity
        equity_total += float(net_profit)

        # Proper balance sheet check
        check = assets_total - (liabilities_total + equity_total)

        data = {
            "title": "Balance Sheet",
            "period": f"{from_date} to {to_date}",
            "assets": {"total": assets_total, "accounts": assets_accounts},
            "liabilities": {"total": liabilities_total, "accounts": liabilities_accounts},
            "equity": {"total": equity_total, "accounts": equity_accounts},
            "net_profit_used": float(net_profit),
            "check": check
        }

        return Response([data])
