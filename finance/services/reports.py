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
            'account__id', 'account__name', 'account__account_number',
            'account__parent_account__id', 'account__parent_account__name', 'account__parent_account__account_number'
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

            account_data = {
                "id": item['account__id'],
                "account": item['account__name'],
                "account_number": item['account__account_number'],
                "amount": float(net_amount)
            }
            parent_name = item['account__parent_account__name']
            if parent_name:
                if parent_name not in temp_accounts:
                    temp_accounts[parent_name] = {
                        "id": item['account__parent_account__id'],
                        "parent": parent_name,
                        "account_number": item['account__parent_account__account_number'],
                        "children": []
                    }
                temp_accounts[parent_name]['children'].append(account_data)
            else:
                # Handle root-level accounts if any (unlikely with strict hierarchy)
                temp_accounts[item['account__name']] = {
                    "id": item['account__id'],
                    "parent": item['account__name'],
                    "account_number": item['account__account_number'],
                    "balance": account_data,
                    "children": temp_accounts.get(item['account__name'], {}).get('children', [])
                }

        structured = []
        for parent_name, data in temp_accounts.items():
            structured.append({
                "id": data.get("id"),
                "parent": parent_name,
                "account_number": data.get("account_number"),
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
        'account__id', 'account__name', 'account__account_number', 'account__type', 
        'account__parent_account__id', 'account__parent_account__name', 'account__parent_account__account_number'
    ).annotate(
        debit_sum=Coalesce(Sum('debit'), Decimal(0)),
        credit_sum=Coalesce(Sum('credit'), Decimal(0))
    )

    grouped = {label: {} for code, label in ACCOUNT_TYPES}
    total_debit = Decimal(0)
    total_credit = Decimal(0)

    for item in balances:
        acc_type_label = dict(ACCOUNT_TYPES).get(item['account__type'])
        if not acc_type_label: continue

        debit, credit = item['debit_sum'], item['credit_sum']
        net_debit = max(debit - credit, Decimal(0))
        net_credit = max(credit - debit, Decimal(0))
        total_debit += net_debit
        total_credit += net_credit

        account_data = {
            "id": item['account__id'],
            "account": item['account__name'], 
            "account_number": item['account__account_number'],
            "debit": float(net_debit), 
            "credit": float(net_credit)
        }
        parent_name = item['account__parent_account__name']
        
        # Ensure parent exists in grouped
        if parent_name:
            if parent_name not in grouped[acc_type_label]:
                 grouped[acc_type_label][parent_name] = {
                     "id": item['account__parent_account__id'],
                     "parent": parent_name, 
                     "account_number": item['account__parent_account__account_number'],
                     "balance": {"account": parent_name, "debit": 0, "credit": 0}, 
                     "children": []
                 }
            grouped[acc_type_label][parent_name]["children"].append(account_data)
        else:
             # Fallback for Level 1 accounts (shouldn't happen with strict posting rules, but safe to keep)
            grouped[acc_type_label][item['account__name']] = {
                "id": item['account__id'],
                "parent": item['account__name'], 
                "account_number": item['account__account_number'],
                "balance": account_data, 
                "children": []
            }

    # Was: for category in grouped.values(): ... (Removed as we now populate grouped directly)

    accounts_by_type = []
    for code, label in ACCOUNT_TYPES:
        category_accounts = [{"id": d.get("id"), "parent": p, "account_number": d.get("account_number"), "balance": d["balance"], "children": d["children"]} for p, d in grouped[label].items()]
        
        # Add Type Number (X.0000)
        prefix = Account.TYPE_PREFIX_MAP.get(code, "0")
        type_number = f"{prefix}.0000"

        accounts_by_type.append({
            "type": label, 
            "type_number": type_number,
            "accounts": category_accounts
        })

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
            'account__id', 'account__name', 'account__account_number',
            'account__parent_account__id', 'account__parent_account__name', 'account__parent_account__account_number'
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

            acc_id, acc_name, acc_num = item['account__id'], item['account__name'], item['account__account_number']
            parent_id, parent_name, parent_num = item['account__parent_account__id'], item['account__parent_account__name'], item['account__parent_account__account_number']
            
            acc_data = {
                "id": acc_id,
                "account": acc_name,
                "account_number": acc_num,
                "amount": float(net_amount)
            }

            if parent_id:
                if parent_id not in accounts_map:
                    accounts_map[parent_id] = {
                        "id": parent_id,
                        "parent": parent_name,
                        "account_number": parent_num,
                        "balance": {"account": parent_name, "amount": 0},
                        "children": []
                    }
                accounts_map[parent_id]["children"].append(acc_data)
            else:
                accounts_map[acc_id]["balance"] = acc_data
                accounts_map[acc_id]["id"] = acc_id
                accounts_map[acc_id]["account_number"] = acc_num

        structured = [
            {
                "id": data.get("id"),
                "parent": data["balance"]["account"],
                "account_number": data.get("account_number"),
                "balance": data["balance"],
                "children": data.get("children", [])
            } for acc_id, data in accounts_map.items()
        ]
        return float(total), structured

    assets_total, assets_accounts = get_balances('asset')
    liabilities_total, liabilities_accounts = get_balances('liability')
    equity_total, equity_accounts = get_balances('equity')

    equity_total += float(net_profit)
    check = assets_total - (liabilities_total + equity_total)

    def get_type_meta(code, label):
        prefix = Account.TYPE_PREFIX_MAP.get(code, "0")
        return {"label": label, "number": f"{prefix}.0000"}

    return {
        "title": "Balance Sheet",
        "period": f"{from_date} to {to_date}",
        "assets": {
            "total": assets_total, 
            "metadata": get_type_meta('asset', 'Asset'),
            "accounts": assets_accounts
        },
        "liabilities": {
            "total": liabilities_total, 
            "metadata": get_type_meta('liability', 'Liability'),
            "accounts": liabilities_accounts
        },
        "equity": {
            "total": equity_total, 
            "metadata": get_type_meta('equity', 'Equity'),
            "accounts": equity_accounts
        },
        "net_profit_used": float(net_profit),
        "check": check
    }


def get_hierarchical_balances(filters):
    """
    Expert Accounting Audit Version: 
    Returns total balances grouped by hierarchy (Type -> Parent -> Child).
    Ensures Parent Totals = Sum(Children) + Parent's Own Balance.
    Filters: type, parent_account, child_account, start_date, end_date.
    """
    from django.db.models import Value, DecimalField, Sum
    from django.db.models.functions import Coalesce
    from django.db import models
    from ..models import Account
    
    debit_normal_types = Account.DEBIT_BALANCE_TYPES
    
    # Build date filter for movement
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    line_filter = models.Q()
    if start_date:
        line_filter &= models.Q(journalline__journal__date__gte=start_date)
    if end_date:
        line_filter &= models.Q(journalline__journal__date__lte=end_date)
    
    # Get ALL active accounts with their totals via 1 efficient query
    all_accounts = list(Account.objects.filter(status='active').annotate(
        total_debit=Coalesce(
            Sum('journalline__debit', filter=line_filter),
            Value(0), output_field=DecimalField()
        ),
        total_credit=Coalesce(
            Sum('journalline__credit', filter=line_filter),
            Value(0), output_field=DecimalField()
        )
    ).order_by('account_number'))
    
    # 1. Classification & In-memory Grouping
    acc_type_filter = filters.get('type')
    parent_id = str(filters.get('parent_account')) if filters.get('parent_account') else None
    child_id = str(filters.get('child_account')) if filters.get('child_account') else None
    
    parents_by_type = {code: [] for code, _ in Account.ACCOUNT_TYPES}
    children_by_parent = {}
    
    for acc in all_accounts:
        # Calculate individual account balance (respecting Normal Balance side)
        if acc.type in debit_normal_types:
            movement = float(acc.total_debit - acc.total_credit)
        else:
            movement = float(acc.total_credit - acc.total_debit)
            
        # Attach calculated balance to the object for later use
        acc.calculated_balance = movement + (float(acc.opening_balance) if not start_date else 0)
        
        if acc.parent_account_id is None:
            if acc_type_filter and acc.type != acc_type_filter: continue
            if parent_id and str(acc.id) != parent_id: continue
            parents_by_type.setdefault(acc.type, []).append(acc)
        else:
            if child_id and str(acc.id) != child_id: continue
            children_by_parent.setdefault(acc.parent_account_id, []).append(acc)
    
    # 2. Build Structured Output
    formatted_output = {}
    
    for type_code, type_label in Account.ACCOUNT_TYPES:
        if acc_type_filter and acc_type_filter != type_code: continue
            
        prefix = Account.TYPE_PREFIX_MAP.get(type_code, "0")
        type_number = f"{prefix}.0000"
        
        parent_accounts = parents_by_type.get(type_code, [])
        parents_list = []
        type_total = 0.0
        
        for parent in parent_accounts:
            children = children_by_parent.get(parent.id, [])
            
            # Audit Check: Only hide parent if we are filtering by a specific child and it's not present
            if child_id and not children:
                continue
            
            children_list = []
            # DERIVE parent_total: Sum(children) + Parent's own balance (if any)
            # Ideally Parent is Level 2 and should be non-posting, but audit catch-all includes its balance.
            parent_total = parent.calculated_balance
            
            for child in children:
                children_list.append({
                    'id': child.id,
                    'account': child.name,
                    'account_number': child.account_number,
                    'total': child.calculated_balance
                })
                parent_total += child.calculated_balance
            
            parents_list.append({
                'id': parent.id,
                'parent': parent.name,
                'account_number': parent.account_number,
                'total': parent_total,
                'children': children_list
            })
            type_total += parent_total
        
        # Omit types if they have no relevant parents due to child/parent filters
        if (child_id or parent_id) and not parents_list:
            continue
            
        formatted_output[type_code] = {
            'label': type_label,
            'number': type_number,
            'total': type_total,
            'accounts': parents_list
        }
    
    return formatted_output

