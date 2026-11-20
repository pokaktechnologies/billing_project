from datetime import datetime, time
from decimal import Decimal
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import (
    InvoiceModel,
    QuotationOrderModel,
    ReceiptModel,
    SalesReturnModel,
)
from accounts.serializers.pending_dashboard import SalesPendingDashboardSerializer


def _date_to_aware_dt(date_val):
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return timezone.make_aware(date_val) if timezone.is_naive(date_val) else date_val
    return timezone.make_aware(datetime.combine(date_val, time.min))


def _client_display_name(client):
    if not client:
        return "Unknown Client"
    full_name = f"{getattr(client, 'first_name', '') or ''} {getattr(client, 'last_name', '') or ''}".strip()
    return full_name or getattr(client, "company_name", None) or f"Client #{client.id}"


class SalesPendingDashboardAPIView(APIView):
    """
    Sales Module Pending Controls Dashboard API.

    Returns all actionable pending tasks across Sales submodules:
      - quotation: Draft quotations not yet sent, sent quotations awaiting client response
      - invoice: Unpaid client invoices, partially paid client invoices with outstanding balance
      - receipt: Client receipts unlinked to an invoice, receipts with incomplete cheque details
      - sales_return: Pending approval returns, approved returns pending settlement, unlinked returns

    Query Parameters:
      - tab: 'all' (default), 'quotation', 'invoice', 'receipt', 'sales_return'
      - urgency: 'high', 'medium', 'low'
      - search: Search text across item titles, descriptions, and meta
      - limit: Maximum items to return (default: 100)
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "quotation", "label": "Quotations"},
        {"key": "invoice", "label": "Invoices"},
        {"key": "receipt", "label": "Receipts"},
        {"key": "sales_return", "label": "Sales Returns"},
    ]

    def get(self, request):
        today = timezone.localdate()

        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(
            tab_key,
            work_type,
            work_type_label,
            title,
            description,
            urgency,
            record_id=None,
            item_id=None,
            created_at=None,
            due_date=None,
            action_url=None,
            meta=None,
        ):
            if not item_id:
                item_id = f"{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {
                    "key": work_type,
                    "label": work_type_label,
                    "count": 0,
                }
            tab_categories[tab_key][work_type]["count"] += 1

            tab_label = next(
                (t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key),
                tab_key.replace("_", " ").title(),
            )

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": tab_label,
                "work_type": work_type,
                "work_type_label": work_type_label,
                "title": title,
                "description": description,
                "urgency": urgency,
                "created_at": created_at,
                "due_date": due_date,
                "action_url": action_url,
                "meta": meta or {},
            })

        # =========================================================================
        # 1. TAB: QUOTATION (QuotationOrderModel)
        # =========================================================================
        pending_quotations = (
            QuotationOrderModel.objects.filter(status__in=["draft", "sent"])
            .select_related("client", "client__salesperson")
            .order_by("-quotation_date", "-id")
        )

        for q in pending_quotations:
            client_name = _client_display_name(q.client)
            days_since = (today - q.quotation_date).days if q.quotation_date else 0
            created_dt = _date_to_aware_dt(q.quotation_date)
            common_meta = {
                "quotation_number": q.quotation_number,
                "client_id": q.client_id,
                "client_name": client_name,
                "project_name": q.project_name or "",
                "grand_total": str(q.grand_total or Decimal("0.00")),
                "status": q.status,
                "quotation_date": str(q.quotation_date) if q.quotation_date else None,
                "days_pending": days_since,
            }

            if q.status == "draft":
                urgency = "high" if days_since > 3 else "medium"
                add_item(
                    tab_key="quotation",
                    work_type="quotation_draft",
                    work_type_label="Draft Quotation",
                    title=f"{q.quotation_number} ({client_name}) - Not Yet Sent",
                    description=f"Quotation dated {q.quotation_date.strftime('%d-%b-%Y') if q.quotation_date else 'N/A'} for ₹{q.grand_total} is still in draft and has not been sent to the client.",
                    urgency=urgency,
                    record_id=q.id,
                    item_id=f"quot_draft_{q.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/quotation/{q.id}/",
                    meta=common_meta,
                )
            elif q.status == "sent":
                urgency = "high" if days_since > 7 else "medium"
                add_item(
                    tab_key="quotation",
                    work_type="quotation_awaiting_response",
                    work_type_label="Awaiting Client Response",
                    title=f"{q.quotation_number} ({client_name}) - Awaiting Approval",
                    description=f"Quotation sent ({days_since} days ago) for ₹{q.grand_total}. Follow-up with client is pending.",
                    urgency=urgency,
                    record_id=q.id,
                    item_id=f"quot_sent_{q.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/quotation/{q.id}/",
                    meta=common_meta,
                )

        # =========================================================================
        # 2. TAB: INVOICE (InvoiceModel, client invoices with pending balance)
        # =========================================================================
        zero_dec = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))

        receipt_sum_subquery = (
            ReceiptModel.objects.filter(invoice=OuterRef("pk"))
            .values("invoice")
            .annotate(total=Sum("cheque_amount"))
            .values("total")[:1]
        )
        return_sum_subquery = (
            SalesReturnModel.objects.filter(invoice=OuterRef("pk"))
            .exclude(status="rejected")
            .values("invoice")
            .annotate(total=Sum("grand_total"))
            .values("total")[:1]
        )

        pending_invoices = (
            InvoiceModel.objects.filter(invoice_type="client")
            .select_related("client")
            .annotate(
                total_received=Coalesce(Subquery(receipt_sum_subquery), zero_dec),
                total_returned=Coalesce(Subquery(return_sum_subquery), zero_dec),
            )
            .annotate(
                net_pending=F("invoice_grand_total") - F("total_received") - F("total_returned")
            )
            .filter(net_pending__gt=0)
            .order_by("-invoice_date", "-id")
        )

        for inv in pending_invoices:
            client_name = _client_display_name(inv.client)
            days_since = (today - inv.invoice_date).days if inv.invoice_date else 0
            created_dt = inv.created_at or _date_to_aware_dt(inv.invoice_date)
            inv_meta = {
                "invoice_number": inv.invoice_number,
                "client_id": inv.client_id,
                "client_name": client_name,
                "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
                "invoice_grand_total": str(inv.invoice_grand_total),
                "total_received": str(inv.total_received),
                "total_returned": str(inv.total_returned),
                "net_pending": str(inv.net_pending),
                "days_pending": days_since,
            }

            if inv.total_received <= 0:
                urgency = "high" if days_since > 7 else "medium"
                add_item(
                    tab_key="invoice",
                    work_type="invoice_unpaid",
                    work_type_label="Unpaid Invoice",
                    title=f"{inv.invoice_number} ({client_name}) - Unpaid (₹{inv.net_pending})",
                    description=f"Client invoice dated {inv.invoice_date.strftime('%d-%b-%Y') if inv.invoice_date else 'N/A'} has no payments received yet. Pending balance: ₹{inv.net_pending}.",
                    urgency=urgency,
                    record_id=inv.id,
                    item_id=f"inv_unpaid_{inv.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/invoice/{inv.id}/",
                    meta=inv_meta,
                )
            else:
                add_item(
                    tab_key="invoice",
                    work_type="invoice_partial_payment",
                    work_type_label="Partial Payment Pending",
                    title=f"{inv.invoice_number} ({client_name}) - Balance Due ₹{inv.net_pending}",
                    description=f"Received ₹{inv.total_received} of ₹{inv.invoice_grand_total}. Remaining balance of ₹{inv.net_pending} is still pending.",
                    urgency="high",
                    record_id=inv.id,
                    item_id=f"inv_partial_{inv.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/invoice/{inv.id}/",
                    meta=inv_meta,
                )

        # =========================================================================
        # 3. TAB: RECEIPT (ReceiptModel, client receipts)
        # =========================================================================
        client_receipts = (
            ReceiptModel.objects.filter(receipt_type="client")
            .filter(
                Q(invoice__isnull=True)
                | (
                    Q(cheque_number__isnull=False)
                    & ~Q(cheque_number="")
                    & (
                        Q(bank_name__isnull=True)
                        | Q(bank_name="")
                        | Q(cheque_amount__isnull=True)
                        | Q(cheque_amount__lte=0)
                    )
                )
            )
            .select_related("client", "invoice")
            .order_by("-receipt_date", "-id")
        )

        for rec in client_receipts:
            client_name = _client_display_name(rec.client)
            created_dt = rec.created_at or _date_to_aware_dt(rec.receipt_date)
            rec_meta = {
                "receipt_number": rec.receipt_number,
                "client_id": rec.client_id,
                "client_name": client_name,
                "invoice_id": rec.invoice_id,
                "receipt_date": str(rec.receipt_date) if rec.receipt_date else None,
                "cheque_number": rec.cheque_number or "",
                "bank_name": rec.bank_name or "",
                "cheque_amount": str(rec.cheque_amount or Decimal("0.00")),
                "total_amount": str(rec.total_amount or Decimal("0.00")),
            }

            if rec.invoice_id is None:
                add_item(
                    tab_key="receipt",
                    work_type="receipt_unlinked_invoice",
                    work_type_label="Receipt Unlinked to Invoice",
                    title=f"{rec.receipt_number} ({client_name}) - No Invoice Linked",
                    description=f"Client receipt for ₹{rec.cheque_amount or rec.total_amount or 0} is not linked to any invoice.",
                    urgency="high",
                    record_id=rec.id,
                    item_id=f"rec_unlinked_{rec.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/receipts/{rec.id}/",
                    meta=rec_meta,
                )

            has_cheque = bool((rec.cheque_number or "").strip())
            missing_cheque_info = not (rec.bank_name or "").strip() or not rec.cheque_amount or rec.cheque_amount <= 0
            if has_cheque and missing_cheque_info:
                add_item(
                    tab_key="receipt",
                    work_type="receipt_incomplete_cheque",
                    work_type_label="Incomplete Cheque Details",
                    title=f"{rec.receipt_number} ({client_name}) - Incomplete Cheque Info",
                    description=f"Cheque #{rec.cheque_number} is missing bank name or valid cheque amount.",
                    urgency="medium",
                    record_id=rec.id,
                    item_id=f"rec_cheque_{rec.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/receipts/{rec.id}/",
                    meta=rec_meta,
                )

        # =========================================================================
        # 4. TAB: SALES RETURN (SalesReturnModel)
        # =========================================================================
        pending_returns = (
            SalesReturnModel.objects.filter(
                Q(status__in=["pending", "approved"])
                | (Q(invoice__isnull=True) & ~Q(status="rejected"))
            )
            .select_related("client", "invoice")
            .order_by("-return_date", "-id")
        )

        for sr in pending_returns:
            client_name = _client_display_name(sr.client)
            days_since = (today - sr.return_date).days if sr.return_date else 0
            created_dt = sr.created_at or _date_to_aware_dt(sr.return_date)
            sr_meta = {
                "sales_return_number": sr.sales_return_number,
                "client_id": sr.client_id,
                "client_name": client_name,
                "invoice_id": sr.invoice_id,
                "invoice_number": sr.invoice.invoice_number if sr.invoice else None,
                "return_date": str(sr.return_date) if sr.return_date else None,
                "grand_total": str(sr.grand_total or Decimal("0.00")),
                "status": sr.status,
                "days_pending": days_since,
            }

            if sr.status == "pending":
                urgency = "high" if days_since > 3 else "medium"
                add_item(
                    tab_key="sales_return",
                    work_type="sales_return_pending_approval",
                    work_type_label="Return Pending Approval",
                    title=f"{sr.sales_return_number} ({client_name}) - Approval Pending",
                    description=f"Sales return of ₹{sr.grand_total} dated {sr.return_date.strftime('%d-%b-%Y') if sr.return_date else 'N/A'} is waiting for approval.",
                    urgency=urgency,
                    record_id=sr.id,
                    item_id=f"sr_pending_{sr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/sales-returns/{sr.id}/",
                    meta=sr_meta,
                )
            elif sr.status == "approved":
                add_item(
                    tab_key="sales_return",
                    work_type="sales_return_pending_settlement",
                    work_type_label="Return Pending Settlement",
                    title=f"{sr.sales_return_number} ({client_name}) - Settlement Pending",
                    description=f"Approved sales return of ₹{sr.grand_total} is awaiting refund or credit adjustment.",
                    urgency="high",
                    record_id=sr.id,
                    item_id=f"sr_settlement_{sr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/sales-returns/{sr.id}/",
                    meta=sr_meta,
                )

            if sr.invoice_id is None and sr.status != "rejected":
                add_item(
                    tab_key="sales_return",
                    work_type="sales_return_unlinked_invoice",
                    work_type_label="Return Unlinked to Invoice",
                    title=f"{sr.sales_return_number} ({client_name}) - No Invoice Linked",
                    description=f"Sales return of ₹{sr.grand_total} is not linked to an original invoice.",
                    urgency="high",
                    record_id=sr.id,
                    item_id=f"sr_unlinked_{sr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/sales-returns/{sr.id}/",
                    meta=sr_meta,
                )

        # =========================================================================
        # BUILD TAB METADATA & FILTERING
        # =========================================================================
        tab_counts = {tab["key"]: len(tab_items[tab["key"]]) for tab in self.TAB_DEFINITIONS}
        total_pending_count = sum(tab_counts.values())

        tabs_data = []
        for tab_def in self.TAB_DEFINITIONS:
            k = tab_def["key"]
            tabs_data.append({
                "key": k,
                "label": tab_def["label"],
                "count": tab_counts[k],
                "categories": list(tab_categories[k].values()),
            })

        if active_tab in tab_items:
            combined_items = tab_items[active_tab]
        else:
            active_tab = "all"
            combined_items = []
            for t in self.TAB_DEFINITIONS:
                combined_items.extend(tab_items[t["key"]])

        if urgency_filter in ["high", "medium", "low"]:
            combined_items = [it for it in combined_items if it["urgency"] == urgency_filter]

        if search_query:
            combined_items = [
                it for it in combined_items
                if search_query in it["title"].lower()
                or search_query in it["description"].lower()
                or search_query in str(it.get("meta", {})).lower()
            ]

        urgency_priority = {"high": 1, "medium": 2, "low": 3}
        combined_items.sort(key=lambda x: urgency_priority.get(x["urgency"], 4))

        if limit_param.isdigit():
            limit_val = int(limit_param)
            if limit_val > 0:
                combined_items = combined_items[:limit_val]

        response_data = {
            "module": "sales",
            "module_label": "Sales",
            "total_pending_count": total_pending_count,
            "tab_counts": tab_counts,
            "tabs": tabs_data,
            "active_tab": active_tab,
            "items_count": len(combined_items),
            "items": combined_items,
        }

        serializer = SalesPendingDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
