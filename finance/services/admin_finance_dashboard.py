from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Case, Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounts.models import (
    InvoiceModel,
    QuotationOrderModel,
    ReceiptModel,
    SalesReturnModel,
)
from finance.models import (
    CreditNote,
    DebitNote,
    FinancialYear,
    JournalEntry,
    PaymentVoucher,
)
from finance.services.reports import get_profit_and_loss_data

ZERO_DEC = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))


def _client_display_name(client):
    if not client:
        return "Unknown Client"
    full_name = f"{getattr(client, 'first_name', '') or ''} {getattr(client, 'last_name', '') or ''}".strip()
    return full_name or getattr(client, "company_name", None) or f"Client #{client.id}"


def _intern_display_name(intern):
    if not intern or not getattr(intern, "user", None):
        return "Unknown Intern"
    return intern.user.get_full_name() or intern.staff_email or f"Intern #{intern.id}"


def _party_display_name(record_type, client, intern):
    if record_type == "intern":
        return _intern_display_name(intern)
    return _client_display_name(client)


def _date_bounds_filter(field_name, from_date, to_date):
    q = Q()
    if from_date:
        q &= Q(**{f"{field_name}__gte": from_date})
    if to_date:
        q &= Q(**{f"{field_name}__lte": to_date})
    return q


def _build_sales_records(from_date, to_date, today):
    # 1. Quotations
    quot_qs = QuotationOrderModel.objects.filter(
        _date_bounds_filter("quotation_date", from_date, to_date)
    )
    quot_agg = quot_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("grand_total"), ZERO_DEC),
        draft_count=Count("id", filter=Q(status="draft")),
        sent_count=Count("id", filter=Q(status="sent")),
        approved_count=Count("id", filter=Q(status="approved")),
        rejected_count=Count("id", filter=Q(status="rejected")),
    )
    recent_quotations = [
        {
            "id": q.id,
            "quotation_number": q.quotation_number,
            "client_name": _client_display_name(q.client),
            "quotation_date": str(q.quotation_date) if q.quotation_date else None,
            "grand_total": str(q.grand_total or Decimal("0.00")),
            "status": q.status,
        }
        for q in quot_qs.select_related("client").order_by("-quotation_date", "-id")[:3]
    ]

    # 2. Invoices
    inv_qs = InvoiceModel.objects.filter(
        _date_bounds_filter("invoice_date", from_date, to_date)
    )
    inv_agg = inv_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("invoice_grand_total"), ZERO_DEC),
        client_count=Count("id", filter=Q(invoice_type="client")),
        client_amount=Coalesce(Sum("invoice_grand_total", filter=Q(invoice_type="client")), ZERO_DEC),
        intern_count=Count("id", filter=Q(invoice_type="intern")),
        intern_amount=Coalesce(Sum("invoice_grand_total", filter=Q(invoice_type="intern")), ZERO_DEC),
        receipted_count=Count("id", filter=Q(is_receipted=True)),
        unreceipted_count=Count("id", filter=Q(is_receipted=False)),
    )

    receipt_sum_subquery = (
        ReceiptModel.objects.filter(invoice=OuterRef("pk"))
        .annotate(
            eff_amount=Case(
                When(total_amount__gt=0, then=F("total_amount")),
                default=Coalesce(F("cheque_amount"), ZERO_DEC),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .values("invoice")
        .annotate(total=Sum("eff_amount"))
        .values("total")[:1]
    )
    return_sum_subquery = (
        SalesReturnModel.objects.filter(invoice=OuterRef("pk"))
        .exclude(status="rejected")
        .values("invoice")
        .annotate(total=Sum("grand_total"))
        .values("total")[:1]
    )
    outstanding_agg = (
        inv_qs.annotate(
            total_received=Coalesce(Subquery(receipt_sum_subquery), ZERO_DEC),
            total_returned=Coalesce(Subquery(return_sum_subquery), ZERO_DEC),
        )
        .annotate(
            net_pending=F("invoice_grand_total") - F("total_received") - F("total_returned")
        )
        .filter(net_pending__gt=0)
        .aggregate(outstanding_amount=Coalesce(Sum("net_pending"), ZERO_DEC))
    )
    overdue_cutoff = today - timedelta(days=30)
    overdue_count = inv_qs.filter(
        invoice_type="client",
        is_receipted=False,
        invoice_date__lt=overdue_cutoff,
    ).count()

    recent_invoices = [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_type": inv.invoice_type,
            "party_name": _party_display_name(inv.invoice_type, inv.client, inv.intern),
            "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
            "invoice_grand_total": str(inv.invoice_grand_total or Decimal("0.00")),
            "is_receipted": inv.is_receipted,
        }
        for inv in inv_qs.select_related("client", "intern", "intern__user").order_by("-invoice_date", "-id")[:3]
    ]

    # 3. Receipts
    rec_qs = ReceiptModel.objects.filter(
        _date_bounds_filter("receipt_date", from_date, to_date)
    ).annotate(
        effective_amount=Case(
            When(total_amount__gt=0, then=F("total_amount")),
            default=Coalesce(F("cheque_amount"), ZERO_DEC),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )
    rec_agg = rec_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("effective_amount"), ZERO_DEC),
        client_count=Count("id", filter=Q(receipt_type="client")),
        client_amount=Coalesce(Sum("effective_amount", filter=Q(receipt_type="client")), ZERO_DEC),
        intern_count=Count("id", filter=Q(receipt_type="intern")),
        intern_amount=Coalesce(Sum("effective_amount", filter=Q(receipt_type="intern")), ZERO_DEC),
        unlinked_count=Count("id", filter=Q(receipt_type="client", invoice__isnull=True)),
    )
    recent_receipts = [
        {
            "id": rec.id,
            "receipt_number": rec.receipt_number,
            "receipt_type": rec.receipt_type,
            "party_name": _party_display_name(rec.receipt_type, rec.client, rec.intern),
            "receipt_date": str(rec.receipt_date) if rec.receipt_date else None,
            "amount": str(rec.effective_amount or Decimal("0.00")),
            "invoice_number": rec.invoice.invoice_number if rec.invoice else None,
        }
        for rec in rec_qs.select_related("client", "intern", "intern__user", "invoice").order_by("-receipt_date", "-id")[:3]
    ]

    # 4. Sales Returns
    sr_qs = SalesReturnModel.objects.filter(
        _date_bounds_filter("return_date", from_date, to_date)
    )
    sr_agg = sr_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("grand_total"), ZERO_DEC),
        pending_count=Count("id", filter=Q(status="pending")),
        approved_count=Count("id", filter=Q(status="approved")),
        settled_count=Count("id", filter=Q(status="settled")),
        rejected_count=Count("id", filter=Q(status="rejected")),
        pending_settlement_amount=Coalesce(Sum("grand_total", filter=Q(status="approved")), ZERO_DEC),
    )
    recent_sales_returns = [
        {
            "id": sr.id,
            "sales_return_number": sr.sales_return_number,
            "client_name": _client_display_name(sr.client),
            "return_date": str(sr.return_date) if sr.return_date else None,
            "grand_total": str(sr.grand_total or Decimal("0.00")),
            "status": sr.status,
            "invoice_number": sr.invoice.invoice_number if sr.invoice else None,
        }
        for sr in sr_qs.select_related("client", "invoice").order_by("-return_date", "-id")[:3]
    ]

    return {
        "quotations": {
            "total_count": quot_agg["total_count"],
            "total_amount": str(quot_agg["total_amount"]),
            "draft": quot_agg["draft_count"],
            "sent": quot_agg["sent_count"],
            "approved": quot_agg["approved_count"],
            "rejected": quot_agg["rejected_count"],
            "recent": recent_quotations,
        },
        "invoices": {
            "total_count": inv_agg["total_count"],
            "total_amount": str(inv_agg["total_amount"]),
            "client_count": inv_agg["client_count"],
            "client_amount": str(inv_agg["client_amount"]),
            "intern_count": inv_agg["intern_count"],
            "intern_amount": str(inv_agg["intern_amount"]),
            "receipted_count": inv_agg["receipted_count"],
            "unreceipted_count": inv_agg["unreceipted_count"],
            "outstanding_amount": str(outstanding_agg["outstanding_amount"]),
            "overdue_count": overdue_count,
            "recent": recent_invoices,
        },
        "receipts": {
            "total_count": rec_agg["total_count"],
            "total_amount": str(rec_agg["total_amount"]),
            "client_count": rec_agg["client_count"],
            "client_amount": str(rec_agg["client_amount"]),
            "intern_count": rec_agg["intern_count"],
            "intern_amount": str(rec_agg["intern_amount"]),
            "unlinked_count": rec_agg["unlinked_count"],
            "recent": recent_receipts,
        },
        "sales_returns": {
            "total_count": sr_agg["total_count"],
            "total_amount": str(sr_agg["total_amount"]),
            "pending": sr_agg["pending_count"],
            "approved": sr_agg["approved_count"],
            "settled": sr_agg["settled_count"],
            "rejected": sr_agg["rejected_count"],
            "pending_settlement_amount": str(sr_agg["pending_settlement_amount"]),
            "recent": recent_sales_returns,
        },
    }


def _build_accounting_summary(from_date, to_date, active_fy, today):
    pnl_from = from_date or (active_fy.start_date if active_fy else today.replace(month=1, day=1))
    pnl_to = to_date or (active_fy.end_date if active_fy else today)

    pnl_from_dt = timezone.make_aware(datetime.combine(pnl_from, time.min))
    pnl_to_dt = timezone.make_aware(datetime.combine(pnl_to, time.max))
    pnl_raw = get_profit_and_loss_data(pnl_from_dt, pnl_to_dt)

    profit_and_loss = {
        "period": f"{pnl_from} to {pnl_to}",
        "sales_total": pnl_raw["sales"]["total"],
        "cost_of_sales_total": pnl_raw["cost_of_sales"]["total"],
        "revenue_total": pnl_raw["revenue"]["total"],
        "general_expenses_total": pnl_raw["general_expenses"]["total"],
        "gross_profit": pnl_raw["summary"]["gross_profit"],
        "operating_profit": pnl_raw["summary"]["operating_profit"],
        "net_profit": pnl_raw["summary"]["net_profit"],
        "profit_margin": pnl_raw["summary"]["profit_margin"],
        "type": pnl_raw["summary"]["type"],
    }

    pv_qs = PaymentVoucher.objects.filter(_date_bounds_filter("date", from_date, to_date))
    pv_agg = pv_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("amount"), ZERO_DEC),
        draft_count=Count("id", filter=Q(status="draft")),
        draft_amount=Coalesce(Sum("amount", filter=Q(status="draft")), ZERO_DEC),
        posted_count=Count("id", filter=Q(status="posted")),
        posted_amount=Coalesce(Sum("amount", filter=Q(status="posted")), ZERO_DEC),
    )
    recent_vouchers = [
        {
            "id": pv.id,
            "voucher_number": pv.voucher_number,
            "pay_to": pv.pay_to,
            "date": str(pv.date) if pv.date else None,
            "amount": str(pv.amount or Decimal("0.00")),
            "payment_method": pv.payment_method,
            "status": pv.status,
        }
        for pv in pv_qs.order_by("-date", "-id")[:3]
    ]

    cn_qs = CreditNote.objects.filter(_date_bounds_filter("date", from_date, to_date))
    cn_agg = cn_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("grand_total"), ZERO_DEC),
        unposted_count=Count("id", filter=Q(journal_entry__isnull=True)),
    )

    dn_qs = DebitNote.objects.filter(_date_bounds_filter("date", from_date, to_date))
    dn_agg = dn_qs.aggregate(
        total_count=Count("id"),
        total_amount=Coalesce(Sum("grand_total"), ZERO_DEC),
        unposted_count=Count("id", filter=Q(journal_entry__isnull=True)),
    )

    je_qs = JournalEntry.objects.all()
    if from_date:
        je_qs = je_qs.filter(date__gte=timezone.make_aware(datetime.combine(from_date, time.min)))
    if to_date:
        je_qs = je_qs.filter(date__lte=timezone.make_aware(datetime.combine(to_date, time.max)))

    je_annotated = je_qs.annotate(
        line_count=Count("lines"),
        debit_sum=Coalesce(Sum("lines__debit"), ZERO_DEC),
        credit_sum=Coalesce(Sum("lines__credit"), ZERO_DEC),
    )
    unbalanced_count = sum(
        1 for je in je_annotated if je.line_count == 0 or round(je.debit_sum, 2) != round(je.credit_sum, 2)
    )

    posted_invoice_numbers = set(
        JournalEntry.objects.filter(type="invoice").values_list("type_number", flat=True)
    )
    posted_receipt_numbers = set(
        JournalEntry.objects.filter(type="receipt").values_list("type_number", flat=True)
    )
    inv_missing_journal = (
        InvoiceModel.objects.filter(_date_bounds_filter("invoice_date", from_date, to_date))
        .filter(invoice_grand_total__gt=0)
        .exclude(invoice_number__in=posted_invoice_numbers)
        .count()
    )
    rec_missing_journal = (
        ReceiptModel.objects.filter(_date_bounds_filter("receipt_date", from_date, to_date))
        .filter(Q(cheque_amount__gt=0) | Q(total_amount__gt=0))
        .exclude(receipt_number__in=posted_receipt_numbers)
        .count()
    )

    return {
        "profit_and_loss": profit_and_loss,
        "payment_vouchers": {
            "total_count": pv_agg["total_count"],
            "total_amount": str(pv_agg["total_amount"]),
            "draft_count": pv_agg["draft_count"],
            "draft_amount": str(pv_agg["draft_amount"]),
            "posted_count": pv_agg["posted_count"],
            "posted_amount": str(pv_agg["posted_amount"]),
            "recent": recent_vouchers,
        },
        "credit_notes": {
            "total_count": cn_agg["total_count"],
            "total_amount": str(cn_agg["total_amount"]),
            "unposted_count": cn_agg["unposted_count"],
        },
        "debit_notes": {
            "total_count": dn_agg["total_count"],
            "total_amount": str(dn_agg["total_amount"]),
            "unposted_count": dn_agg["unposted_count"],
        },
        "ledger_health": {
            "total_journal_entries": je_qs.count(),
            "unbalanced_journal_entries": unbalanced_count,
            "invoices_missing_journal": inv_missing_journal,
            "receipts_missing_journal": rec_missing_journal,
            "has_active_financial_year": active_fy is not None,
        },
    }


def build_admin_finance_dashboard(from_date=None, to_date=None):
    """
    Aggregate financial records from `accounts` (quotations, invoices, receipts,
    sales returns) and `finance` (financial year, P&L, payment vouchers, credit/debit
    notes, ledger health) for the Admin Dashboard.
    """
    today = timezone.localdate()
    active_fy = FinancialYear.objects.filter(is_current=True, status="open").first()

    effective_from = from_date if from_date is not None else (active_fy.start_date if active_fy else None)
    effective_to = to_date if to_date is not None else (active_fy.end_date if active_fy else None)

    fy_data = None
    if active_fy:
        fy_data = {
            "id": active_fy.id,
            "name": active_fy.name,
            "start_date": str(active_fy.start_date),
            "end_date": str(active_fy.end_date),
            "status": active_fy.status,
        }

    return {
        "financial_year": fy_data,
        "sales_records": _build_sales_records(effective_from, effective_to, today),
        "accounting": _build_accounting_summary(effective_from, effective_to, active_fy, today),
    }
