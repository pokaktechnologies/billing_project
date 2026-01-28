from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from ..models import Account, JournalLine, CashflowCategoryMapping

def get_cashflow_statement_data(from_date_str=None, to_date_str=None):
    filters = Q()
    from_date = None
    to_date = None
    if from_date_str and to_date_str:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d") + timedelta(days=1)
        filters &= Q(journal__date__range=[from_date, to_date])
    elif from_date_str:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
        filters &= Q(journal__date__gte=from_date)
    elif to_date_str:
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d") + timedelta(days=1)
        filters &= Q(journal__date__lte=to_date)

    report_sections = []
    totals = {"operating": Decimal(0), "investing": Decimal(0), "financing": Decimal(0)}

    for category, category_label in CashflowCategoryMapping.CATEGORY_CHOICES:
        mappings = CashflowCategoryMapping.objects.filter(category=category)
        category_items = []
        category_total = Decimal(0)

        for mapping in mappings:
            account_ids = mapping.accounts.values_list("id", flat=True)
            lines = JournalLine.objects.filter(filters, account_id__in=account_ids)

            res = lines.aggregate(
                debit=Coalesce(Sum("debit"), Value(0), output_field=DecimalField()),
                credit=Coalesce(Sum("credit"), Value(0), output_field=DecimalField())
            )
            net = res["credit"] - res["debit"]
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

    cash_accounts = CashflowCategoryMapping.objects.filter(
        sub_category__iregex=r"(cash|bank)"
    ).values_list("accounts", flat=True)
    
    cash_accounts_opening_balances = Account.objects.filter(id__in=cash_accounts).values_list('opening_balance', flat=True)
    opening_cash_balance = sum(cash_accounts_opening_balances)

    net_cash_change = totals["operating"] + totals["investing"] + totals["financing"]
    ending_cash_balance = opening_cash_balance + net_cash_change

    summary = {
        "Operating Cash Flow": f"₹{totals['operating']:,.0f}",
        "Cash and Cash Equivalents at Beginning of Period": f"₹{opening_cash_balance:,.0f}",
        "Ending Cash Balance": f"₹{ending_cash_balance:,.0f}",
        "Net Cash Change": f"₹{net_cash_change:,.0f}"
    }

    return {
        "report_period": {"from_date": from_date_str or "ALL", "to_date": to_date_str or "ALL"},
        "title": "Cash Flow Statement",
        "subtitle": f"For the period from {from_date_str or 'beginning'} to {to_date_str or 'today'}",
        "sections": report_sections,
        "summary": summary,
    }

def get_profit_and_loss_data(from_date, to_date):
    lines = JournalLine.objects.filter(journal__date__range=(from_date, to_date), account__status='active')

    def get_balances(account_type, is_credit_positive=True):
        qs = lines.filter(account__type=account_type)
        annotated = qs.values(
            'account__id', 'account__name', 'account__parent_account__id', 'account__parent_account__name'
        ).annotate(
            debit_sum=Coalesce(Sum('debit'), Decimal(0)),
            credit_sum=Coalesce(Sum('credit'), Decimal(0))
        )

        temp_accounts = defaultdict(lambda: {})
        total = Decimal(0)

        for item in annotated:
            debit, credit = item['debit_sum'], item['credit_sum']
            net_debit = max(debit - credit, Decimal(0))
            net_credit = max(credit - debit, Decimal(0))
            net_amount = net_credit - net_debit if is_credit_positive else net_debit - net_credit
            total += net_amount

            account_data = {"account": item['account__name'], "amount": float(net_amount)}
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

    sales_total, sales_accounts = get_balances('sales', is_credit_positive=True)
    cost_total, cost_accounts = get_balances('cost_of_sales', is_credit_positive=False)
    revenue_total, revenue_accounts = get_balances('revenue', is_credit_positive=True)
    expense_total, expense_accounts = get_balances('general_expenses', is_credit_positive=False)

    gross_profit = sales_total - cost_total
    operating_profit = gross_profit - expense_total
    net_profit = operating_profit + revenue_total
    total_income = sales_total + revenue_total
    profit_margin = (net_profit / total_income * 100) if total_income != 0 else 0

    return {
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
            "type": "Net Profit" if net_profit >= 0 else "Net Loss",
            "profit_margin": round(profit_margin, 2),
        }
    }

def get_trial_balance_data(from_date, to_date):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'), ('liability', 'Liability'), ('equity', 'Equity'),
        ('sales', 'Sales'), ('cost_of_sales', 'Cost of Sales'),
        ('revenue', 'Revenue'), ('general_expenses', 'General Expenses'),
    ]
    lines = JournalLine.objects.filter(journal__date__range=(from_date, to_date), account__status='active')
    balances = lines.values(
        'account__id', 'account__name', 'account__type', 'account__parent_account__id', 'account__parent_account__name'
    ).annotate(
        debit_sum=Coalesce(Sum('debit'), Decimal(0)),
        credit_sum=Coalesce(Sum('credit'), Decimal(0))
    )

    grouped = {label: {} for code, label in ACCOUNT_TYPES}
    total_debit = Decimal(0)
    total_credit = Decimal(0)
    parent_children = defaultdict(list)

    for item in balances:
        acc_type_label = dict(ACCOUNT_TYPES).get(item['account__type'])
        if not acc_type_label: continue

        debit, credit = item['debit_sum'], item['credit_sum']
        net_debit = max(debit - credit, Decimal(0))
        net_credit = max(credit - debit, Decimal(0))
        total_debit += net_debit
        total_credit += net_credit

        account_data = {"account": item['account__name'], "debit": float(net_debit), "credit": float(net_credit)}
        parent_name = item['account__parent_account__name']
        if parent_name:
            parent_children[parent_name].append(account_data)
        else:
            grouped[acc_type_label][item['account__name']] = {"balance": account_data, "children": []}

    for category in grouped.values():
        for parent_name, children in parent_children.items():
            if parent_name in category:
                category[parent_name]["children"] = children

    accounts_by_type = []
    for code, label in ACCOUNT_TYPES:
        category_accounts = [{"parent": p, "balance": d["balance"], "children": d["children"]} for p, d in grouped[label].items()]
        accounts_by_type.append({"type": label, "accounts": category_accounts})

    return {
        "title": "Trial Balance",
        "period": f"{from_date} to {to_date}",
        "accounts_by_type": accounts_by_type,
        "totals": {
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "balanced": round(total_debit, 2) == round(total_credit, 2)
        }
    }

def get_balance_sheet_data(from_date, to_date, net_profit=0):
    lines = JournalLine.objects.filter(journal__date__range=(from_date, to_date), account__status='active')

    def get_balances(account_type):
        qs = lines.filter(account__type=account_type)
        annotated = qs.values(
            'account__id', 'account__name', 'account__parent_account__id', 'account__parent_account__name'
        ).annotate(
            debit_sum=Coalesce(Sum('debit'), Decimal(0)),
            credit_sum=Coalesce(Sum('credit'), Decimal(0))
        )

        accounts_map = defaultdict(lambda: {"children": []})
        total = Decimal(0)

        for item in annotated:
            debit, credit = item['debit_sum'], item['credit_sum']
            net_amount = credit - debit if account_type in ['liability', 'equity'] else debit - credit
            total += net_amount

            acc_id, acc_name = item['account__id'], item['account__name']
            parent_id, parent_name = item['account__parent_account__id'], item['account__parent_account__name']
            acc_data = {"account": acc_name, "amount": float(net_amount)}

            if parent_id:
                accounts_map[parent_id]["children"].append(acc_data)
                if "balance" not in accounts_map[parent_id]:
                    accounts_map[parent_id]["balance"] = {"account": parent_name, "amount": 0}
            else:
                accounts_map[acc_id]["balance"] = acc_data

        structured = [{"parent": data["balance"]["account"], "balance": data["balance"], "children": data.get("children", [])} for acc_id, data in accounts_map.items()]
        return float(total), structured

    assets_total, assets_accounts = get_balances('asset')
    liabilities_total, liabilities_accounts = get_balances('liability')
    equity_total, equity_accounts = get_balances('equity')

    equity_total += float(net_profit)
    check = assets_total - (liabilities_total + equity_total)

    return {
        "title": "Balance Sheet",
        "period": f"{from_date} to {to_date}",
        "assets": {"total": assets_total, "accounts": assets_accounts},
        "liabilities": {"total": liabilities_total, "accounts": liabilities_accounts},
        "equity": {"total": equity_total, "accounts": equity_accounts},
        "net_profit_used": float(net_profit),
        "check": check
    }
