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
            'DN': (DebitNote,'debit_note_number','DN')
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
            "revenue": {"total": revenue_total, "accounts": revenue_accounts},
            "general_expenses": {"total": expense_total, "accounts": expense_accounts},
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

        # Query posted journal lines
        lines = JournalLine.objects.filter(
            journal__date__range=(from_date, to_date),
            account__status='active'
        )

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

        # -----------------------------
        # FIX 1: Proper grouping by TYPE
        # -----------------------------
        grouped = {
            label: {}     # will store parent accounts only
            for code, label in self.ACCOUNT_TYPES
        }

        total_debit = Decimal(0)
        total_credit = Decimal(0)

        # Temporary: store children under parents
        parent_children = defaultdict(list)

        # First pass: calculate balances and group children
        for item in balances:

            acc_type = item['account__type']  # ex: "asset"
            acc_type_label = dict(self.ACCOUNT_TYPES).get(acc_type)

            if not acc_type_label:
                # Skip ANY account with invalid type
                continue

            debit = item['debit_sum']
            credit = item['credit_sum']

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
                # Child → temporarily grouped under parent
                parent_children[parent_name].append(account_data)
            else:
                # Parent → store in the category directly
                grouped[acc_type_label][item['account__name']] = {
                    "balance": account_data,
                    "children": []
                }

        # Second pass: attach children to parents
        for category in grouped.values():
            for parent_name, children in parent_children.items():
                if parent_name in category:
                    category[parent_name]["children"] = children

        # -----------------------------
        # Prepare final output structure
        # -----------------------------
        accounts_by_type = []
        for code, label in self.ACCOUNT_TYPES:
            category_accounts = []

            for parent_name, data in grouped[label].items():
                category_accounts.append({
                    "parent": parent_name,
                    "balance": data["balance"],
                    "children": data["children"],
                })

            accounts_by_type.append({
                "type": label,
                "accounts": category_accounts
            })

        # Final response
        data = {
            "title": "Trial Balance",
            "period": f"{from_date} to {to_date}",
            "accounts_by_type": accounts_by_type,
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



# -------------------------------
# List & Create (GET, POST)
# -------------------------------



class CashflowCategoryMappingListCreateView(generics.ListCreateAPIView):
    serializer_class = CashflowCategoryMappingSerializer

    def get_queryset(self):
        queryset = CashflowCategoryMapping.objects.all()

        # Get query params
        category = self.request.query_params.get('category')
        sub_category = self.request.query_params.get('sub_category')

        # Filter by category (exact match)
        if category:
            queryset = queryset.filter(category__iexact=category)

        # Filter by sub_category (partial match, case-insensitive)
        if sub_category:
            queryset = queryset.filter(sub_category__icontains=sub_category)

        return queryset


# -------------------------------
# Retrieve, Update, Delete (GET, PUT/PATCH, DELETE)
# -------------------------------
class CashflowCategoryMappingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CashflowCategoryMapping.objects.all()
    serializer_class = CashflowCategoryMappingSerializer


from decimal import Decimal
from django.db.models import Sum, Value, Q, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Account, JournalLine, CashflowCategoryMapping


from decimal import Decimal
from datetime import datetime
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from datetime import datetime, timedelta
from .models import JournalLine, CashflowCategoryMapping


class CashflowStatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        # ✅ Initialize empty filter
        filters = Q()

        # --- Build date filter safely ---
        if from_date and to_date:
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
            to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            filters &= Q(journal__date__range=[from_date, to_date])
        elif from_date:
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
            filters &= Q(journal__date__gte=from_date)
        elif to_date:
            to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            filters &= Q(journal__date__lte=to_date)

        # --- Initialize totals ---
        report_sections = []
        totals = {"operating": Decimal(0), "investing": Decimal(0), "financing": Decimal(0)}

        # --- Build each category section ---
        for category, category_label in CashflowCategoryMapping.CATEGORY_CHOICES:
            mappings = CashflowCategoryMapping.objects.filter(category=category)
            category_items = []
            category_total = Decimal(0)

            for mapping in mappings:
                account_ids = mapping.accounts.values_list("id", flat=True)
                lines = JournalLine.objects.filter(filters, account_id__in=account_ids)

                debit_total = lines.aggregate(
                    total=Coalesce(Sum("debit"), Value(0), output_field=DecimalField())
                )["total"]
                credit_total = lines.aggregate(
                    total=Coalesce(Sum("credit"), Value(0), output_field=DecimalField())
                )["total"]

                net = credit_total - debit_total
                category_total += net

                sign = "+" if net >= 0 else "-"
                category_items.append({
                    "label": mapping.sub_category,
                    "amount": f"{sign}₹{abs(net):,.0f}"
                })

            totals[category] = category_total

            report_sections.append({
                "heading": category_label,
                "items": category_items,
                "net_amount": f"₹{category_total:,.0f}"
            })

        # --- Compute summary based on actual Cash & Bank balances ---
        cash_accounts = CashflowCategoryMapping.objects.filter(
            sub_category__iregex=r"(cash|bank)"
        ).values_list("accounts", flat=True)
        # list the accounts each of the name
        cash_accounts_opening_balances = Account.objects.filter(id__in=cash_accounts).values_list('opening_balance', flat=True)
        opening_cash_balance = sum(cash_accounts_opening_balances)


        # Net Cash Change=Operating Cash Flow+Investing Cash Flow+Financing cash flow.
        net_cash_change = totals["operating"] + totals["investing"] + totals["financing"]

        # Ending Cash Balance=Beginning Cash Balance+Net Cash Change
        ending_cash_balance = opening_cash_balance + net_cash_change

        summary = {
            "Operating Cash Flow": f"₹{totals['operating']:,.0f}",
            "Cash and Cash Equivalents at Beginning of Period": f"₹{opening_cash_balance:,.0f}",
            "Ending Cash Balance": f"₹{ending_cash_balance:,.0f}",
            "Net Cash Change": f"₹{net_cash_change:,.0f}"
        }

        # --- Final report payload ---
        report = {
            "report_period": {
                "from_date": from_date or "ALL",
                "to_date": to_date or "ALL",
            },
            "title": "Cash Flow Statement",
            "subtitle": f"For the period from {from_date or 'beginning'} to {to_date or 'today'}",
            "sections": report_sections,
            "summary": summary,
        }

        return Response(report)

