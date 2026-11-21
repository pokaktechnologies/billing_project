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
    MaterialReceive,
    MaterialReceiveItem,
    PurchaseOrder,
    PurchaseOrderItem,
    QuotationOrderModel,
    ReceiptModel,
    SalesReturnModel,
    Supplier,
)
from accounts.serializers.pending_dashboard import (
    PurchasePendingDashboardSerializer,
    SalesPendingDashboardSerializer,
)


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


def _supplier_display_name(supplier):
    if not supplier:
        return "Unknown Supplier"
    if getattr(supplier, "supplier_type", None) == "Business" and (getattr(supplier, "company_name", "") or "").strip():
        return supplier.company_name.strip()
    full_name = f"{getattr(supplier, 'first_name', '') or ''} {getattr(supplier, 'last_name', '') or ''}".strip()
    return full_name or (getattr(supplier, "company_name", "") or "").strip() or getattr(supplier, "supplier_number", None) or f"Supplier #{supplier.id}"


class _BasePendingDashboardAPIView(APIView):
    """Shared collector, filter, sort, and response builder for accounts pending dashboards."""
    permission_classes = [IsAuthenticated]
    TAB_DEFINITIONS = []
    module_key = ""
    module_label = ""
    serializer_class = None

    def _init_buckets(self):
        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}
        tab_labels = {tab["key"]: tab["label"] for tab in self.TAB_DEFINITIONS}

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

            tab_label = tab_labels.get(tab_key, tab_key.replace("_", " ").title())
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

        return tab_items, tab_categories, add_item

    def _build_response(self, request, tab_items, tab_categories):
        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()

        tab_counts = {tab["key"]: len(tab_items[tab["key"]]) for tab in self.TAB_DEFINITIONS}
        total_pending_count = sum(tab_counts.values())

        tabs_data = [
            {
                "key": tab_def["key"],
                "label": tab_def["label"],
                "count": tab_counts[tab_def["key"]],
                "categories": list(tab_categories[tab_def["key"]].values()),
            }
            for tab_def in self.TAB_DEFINITIONS
        ]

        if active_tab in tab_items:
            combined_items = list(tab_items[active_tab])
        else:
            active_tab = "all"
            combined_items = []
            for tab_def in self.TAB_DEFINITIONS:
                combined_items.extend(tab_items[tab_def["key"]])

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
            "module": self.module_key,
            "module_label": self.module_label,
            "total_pending_count": total_pending_count,
            "tab_counts": tab_counts,
            "tabs": tabs_data,
            "active_tab": active_tab,
            "items_count": len(combined_items),
            "items": combined_items,
        }

        serializer = self.serializer_class(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalesPendingDashboardAPIView(_BasePendingDashboardAPIView):
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
    module_key = "sales"
    module_label = "Sales"
    serializer_class = SalesPendingDashboardSerializer

    TAB_DEFINITIONS = [
        {"key": "quotation", "label": "Quotations"},
        {"key": "invoice", "label": "Invoices"},
        {"key": "receipt", "label": "Receipts"},
        {"key": "sales_return", "label": "Sales Returns"},
    ]

    def get(self, request):
        today = timezone.localdate()
        tab_items, tab_categories, add_item = self._init_buckets()

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

        return self._build_response(request, tab_items, tab_categories)


class PurchasePendingDashboardAPIView(_BasePendingDashboardAPIView):
    """
    Purchases Module Pending Controls Dashboard API.

    Returns all actionable pending tasks across Purchase submodules:
      - purchase_order: Empty POs, draft POs, overdue deliveries, unreceived POs, partially received POs
      - material_receive: Unverified GRNs, empty GRNs, supplier mismatches, over-received/unmatched items, total mismatches
      - supplier: Active suppliers with incomplete profile details or missing payment terms

    Query Parameters:
      - tab: 'all' (default), 'purchase_order', 'material_receive', 'supplier'
      - urgency: 'high', 'medium', 'low'
      - search: Search text across item titles, descriptions, and meta
      - limit: Maximum items to return (default: 100)
    """
    module_key = "purchases"
    module_label = "Purchases"
    serializer_class = PurchasePendingDashboardSerializer

    TAB_DEFINITIONS = [
        {"key": "purchase_order", "label": "Purchase Orders"},
        {"key": "material_receive", "label": "Material Receives"},
        {"key": "supplier", "label": "Suppliers"},
    ]

    def get(self, request):
        today = timezone.localdate()
        tab_items, tab_categories, add_item = self._init_buckets()

        # =========================================================================
        # 1. TAB: PURCHASE ORDER (PurchaseOrder)
        # =========================================================================
        pending_pos = list(
            PurchaseOrder.objects.exclude(status__in=["received", "closed", "cancelled"])
            .select_related("supplier", "terms_and_conditions")
            .order_by("-purchase_order_date", "-id")
        )
        po_ids = [po.id for po in pending_pos]

        ordered_by_po = {}
        received_by_po = {}
        if po_ids:
            for row in (
                PurchaseOrderItem.objects.filter(purchase_order_id__in=po_ids)
                .values("purchase_order_id", "product_id")
                .annotate(qty=Sum("quantity"))
            ):
                ordered_by_po.setdefault(row["purchase_order_id"], {})[row["product_id"]] = row["qty"] or 0

            for row in (
                MaterialReceiveItem.objects.filter(material_receive__purchase_order_id__in=po_ids)
                .exclude(material_receive__status="rejected")
                .values("material_receive__purchase_order_id", "product_id")
                .annotate(qty=Sum("quantity"))
            ):
                po_id = row["material_receive__purchase_order_id"]
                received_by_po.setdefault(po_id, {})[row["product_id"]] = row["qty"] or 0

        for po in pending_pos:
            supplier_name = _supplier_display_name(po.supplier)
            ord_map = ordered_by_po.get(po.id, {})
            rec_map = received_by_po.get(po.id, {})

            total_ordered_qty = sum(ord_map.values())
            total_received_qty = sum(
                min(rec_map.get(pid, 0), ord_qty)
                for pid, ord_qty in ord_map.items()
            )
            pending_qty = total_ordered_qty - total_received_qty

            days_since = (today - po.purchase_order_date).days if po.purchase_order_date else 0
            created_dt = _date_to_aware_dt(po.purchase_order_date)
            due_date = po.expected_delivery_date
            is_overdue = bool(due_date and due_date < today)
            days_overdue = (today - due_date).days if is_overdue else 0

            po_meta = {
                "purchase_order_number": po.purchase_order_number,
                "supplier_id": po.supplier_id,
                "supplier_name": supplier_name,
                "status": po.status,
                "purchase_order_date": str(po.purchase_order_date) if po.purchase_order_date else None,
                "expected_delivery_date": str(due_date) if due_date else None,
                "grand_total": str(po.grand_total or Decimal("0.00")),
                "total_ordered_qty": total_ordered_qty,
                "total_received_qty": total_received_qty,
                "pending_qty": pending_qty,
                "days_pending": days_since,
                "days_overdue": days_overdue,
            }

            if total_ordered_qty == 0:
                urgency = "high" if days_since > 3 else "medium"
                add_item(
                    tab_key="purchase_order",
                    work_type="po_empty_items",
                    work_type_label="Purchase Order Without Items",
                    title=f"{po.purchase_order_number} ({supplier_name}) - No Items Added",
                    description="Purchase order has no line items configured and cannot be fulfilled.",
                    urgency=urgency,
                    record_id=po.id,
                    item_id=f"po_empty_{po.id}",
                    created_at=created_dt,
                    due_date=due_date,
                    action_url=f"/accounts/purchase-orders/{po.id}/",
                    meta=po_meta,
                )
            elif po.status == "draft":
                urgency = "high" if (days_since > 3 or is_overdue) else "medium"
                add_item(
                    tab_key="purchase_order",
                    work_type="po_draft",
                    work_type_label="Draft Purchase Order",
                    title=f"{po.purchase_order_number} ({supplier_name}) - Not Yet Sent",
                    description=f"Purchase order dated {po.purchase_order_date.strftime('%d-%b-%Y') if po.purchase_order_date else 'N/A'} for ₹{po.grand_total} is still in draft and has not been sent to the supplier.",
                    urgency=urgency,
                    record_id=po.id,
                    item_id=f"po_draft_{po.id}",
                    created_at=created_dt,
                    due_date=due_date,
                    action_url=f"/accounts/purchase-orders/{po.id}/",
                    meta=po_meta,
                )
            elif po.status in ("sent", "partially_received") and pending_qty > 0:
                if is_overdue:
                    add_item(
                        tab_key="purchase_order",
                        work_type="po_overdue_delivery",
                        work_type_label="Overdue Delivery",
                        title=f"{po.purchase_order_number} ({supplier_name}) - Overdue by {days_overdue} Day(s)",
                        description=f"Expected delivery date {due_date.strftime('%d-%b-%Y')} has passed with {pending_qty} of {total_ordered_qty} unit(s) still pending.",
                        urgency="high",
                        record_id=po.id,
                        item_id=f"po_overdue_{po.id}",
                        created_at=created_dt,
                        due_date=due_date,
                        action_url=f"/accounts/purchase-orders/{po.id}/",
                        meta=po_meta,
                    )
                elif total_received_qty == 0:
                    urgency = "high" if days_since > 7 else "medium"
                    add_item(
                        tab_key="purchase_order",
                        work_type="po_unreceived",
                        work_type_label="Awaiting Material Receipt",
                        title=f"{po.purchase_order_number} ({supplier_name}) - No Goods Received",
                        description=f"Purchase order sent ({days_since} days ago) for {total_ordered_qty} unit(s) has no material receive recorded yet.",
                        urgency=urgency,
                        record_id=po.id,
                        item_id=f"po_unreceived_{po.id}",
                        created_at=created_dt,
                        due_date=due_date,
                        action_url=f"/accounts/purchase-orders/{po.id}/",
                        meta=po_meta,
                    )
                else:
                    add_item(
                        tab_key="purchase_order",
                        work_type="po_partially_received",
                        work_type_label="Partially Received PO",
                        title=f"{po.purchase_order_number} ({supplier_name}) - {pending_qty} Unit(s) Pending",
                        description=f"Received {total_received_qty} of {total_ordered_qty} ordered unit(s). Remaining {pending_qty} unit(s) pending delivery.",
                        urgency="high",
                        record_id=po.id,
                        item_id=f"po_partial_{po.id}",
                        created_at=created_dt,
                        due_date=due_date,
                        action_url=f"/accounts/purchase-orders/{po.id}/",
                        meta=po_meta,
                    )

        # =========================================================================
        # 2. TAB: MATERIAL RECEIVE (MaterialReceive)
        # =========================================================================
        active_mrs = list(
            MaterialReceive.objects.exclude(status="rejected")
            .select_related("supplier", "purchase_order", "purchase_order__supplier")
            .order_by("-received_date", "-id")
        )
        mr_ids = [mr.id for mr in active_mrs]
        ref_po_ids = {mr.purchase_order_id for mr in active_mrs if mr.purchase_order_id}

        mr_items_map = {}
        if mr_ids:
            for item in (
                MaterialReceiveItem.objects.filter(material_receive_id__in=mr_ids)
                .select_related("product")
            ):
                mr_items_map.setdefault(item.material_receive_id, []).append(item)

        po_ordered_for_mr = {}
        po_received_for_mr = {}
        if ref_po_ids:
            for row in (
                PurchaseOrderItem.objects.filter(purchase_order_id__in=ref_po_ids)
                .values("purchase_order_id", "product_id")
                .annotate(qty=Sum("quantity"))
            ):
                po_ordered_for_mr.setdefault(row["purchase_order_id"], {})[row["product_id"]] = row["qty"] or 0

            for row in (
                MaterialReceiveItem.objects.filter(material_receive__purchase_order_id__in=ref_po_ids)
                .exclude(material_receive__status="rejected")
                .values("material_receive__purchase_order_id", "product_id")
                .annotate(qty=Sum("quantity"))
            ):
                po_id = row["material_receive__purchase_order_id"]
                po_received_for_mr.setdefault(po_id, {})[row["product_id"]] = row["qty"] or 0

        for mr in active_mrs:
            supplier_name = _supplier_display_name(mr.supplier)
            items = mr_items_map.get(mr.id, [])
            item_count = len(items)
            calc_total = sum((Decimal(str(it.sub_total or 0)) for it in items), Decimal("0.00"))
            days_since = (today - mr.received_date).days if mr.received_date else 0
            created_dt = _date_to_aware_dt(mr.received_date)

            mr_meta = {
                "material_receive_number": mr.material_receive_number,
                "supplier_id": mr.supplier_id,
                "supplier_name": supplier_name,
                "purchase_order_id": mr.purchase_order_id,
                "purchase_order_number": mr.purchase_order.purchase_order_number if mr.purchase_order else None,
                "received_date": str(mr.received_date) if mr.received_date else None,
                "grand_total": str(mr.grand_total or Decimal("0.00")),
                "calculated_total": str(calc_total),
                "status": mr.status,
                "item_count": item_count,
                "days_pending": days_since,
            }

            if mr.status == "pending_verification":
                urgency = "high" if days_since > 3 else "medium"
                add_item(
                    tab_key="material_receive",
                    work_type="mr_pending_verification",
                    work_type_label="GRN Pending Verification",
                    title=f"{mr.material_receive_number} ({supplier_name}) - Verification Pending",
                    description=f"Material receive dated {mr.received_date.strftime('%d-%b-%Y') if mr.received_date else 'N/A'} for ₹{mr.grand_total} is awaiting quality/quantity verification.",
                    urgency=urgency,
                    record_id=mr.id,
                    item_id=f"mr_verify_{mr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/material-receive/{mr.id}/",
                    meta=mr_meta,
                )

            if item_count == 0:
                add_item(
                    tab_key="material_receive",
                    work_type="mr_empty_items",
                    work_type_label="GRN Without Items",
                    title=f"{mr.material_receive_number} ({supplier_name}) - No Items Recorded",
                    description="Material receive has zero line items and did not update product stock.",
                    urgency="high",
                    record_id=mr.id,
                    item_id=f"mr_empty_{mr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/material-receive/{mr.id}/",
                    meta=mr_meta,
                )

            if mr.purchase_order and mr.supplier_id != mr.purchase_order.supplier_id:
                po_supplier_name = _supplier_display_name(mr.purchase_order.supplier)
                add_item(
                    tab_key="material_receive",
                    work_type="mr_supplier_mismatch",
                    work_type_label="Supplier Mismatch",
                    title=f"{mr.material_receive_number} ({supplier_name}) - Supplier Mismatch",
                    description=f"GRN supplier '{supplier_name}' does not match PO {mr.purchase_order.purchase_order_number} supplier '{po_supplier_name}'.",
                    urgency="high",
                    record_id=mr.id,
                    item_id=f"mr_sup_mismatch_{mr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/material-receive/{mr.id}/",
                    meta={
                        **mr_meta,
                        "po_supplier_id": mr.purchase_order.supplier_id,
                        "po_supplier_name": po_supplier_name,
                    },
                )

            if mr.purchase_order_id and item_count > 0:
                ord_map = po_ordered_for_mr.get(mr.purchase_order_id, {})
                rec_map = po_received_for_mr.get(mr.purchase_order_id, {})
                discrepancies = []
                seen_pids = set()
                for it in items:
                    pid = it.product_id
                    if pid in seen_pids:
                        continue
                    seen_pids.add(pid)
                    ordered_qty = ord_map.get(pid, 0)
                    total_rec_qty = rec_map.get(pid, 0)
                    prod_name = it.product.name if it.product else f"Product #{pid}"
                    if pid not in ord_map:
                        discrepancies.append({
                            "product_id": pid,
                            "product_name": prod_name,
                            "ordered_qty": 0,
                            "received_qty": total_rec_qty,
                            "reason": "not_in_purchase_order",
                        })
                    elif total_rec_qty > ordered_qty:
                        discrepancies.append({
                            "product_id": pid,
                            "product_name": prod_name,
                            "ordered_qty": ordered_qty,
                            "received_qty": total_rec_qty,
                            "reason": "exceeds_ordered_quantity",
                        })

                if discrepancies:
                    add_item(
                        tab_key="material_receive",
                        work_type="mr_over_received",
                        work_type_label="Over-Received / Unmatched Items",
                        title=f"{mr.material_receive_number} ({supplier_name}) - Quantity Exceeds PO",
                        description=f"Material receive against {mr.purchase_order.purchase_order_number} has {len(discrepancies)} product(s) exceeding or absent from the PO.",
                        urgency="high",
                        record_id=mr.id,
                        item_id=f"mr_over_{mr.id}",
                        created_at=created_dt,
                        action_url=f"/accounts/material-receive/{mr.id}/",
                        meta={**mr_meta, "discrepancies": discrepancies},
                    )

            if item_count > 0 and (mr.grand_total <= 0 or abs(mr.grand_total - calc_total) > Decimal("0.01")):
                add_item(
                    tab_key="material_receive",
                    work_type="mr_total_mismatch",
                    work_type_label="GRN Total Mismatch",
                    title=f"{mr.material_receive_number} ({supplier_name}) - Grand Total Mismatch",
                    description=f"Recorded grand total (₹{mr.grand_total}) does not match item sum (₹{calc_total}).",
                    urgency="medium",
                    record_id=mr.id,
                    item_id=f"mr_total_{mr.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/material-receive/{mr.id}/",
                    meta=mr_meta,
                )

        # =========================================================================
        # 3. TAB: SUPPLIER (Supplier)
        # =========================================================================
        active_suppliers = (
            Supplier.objects.filter(is_active=True)
            .select_related("payment_terms")
            .order_by("-created_at", "-id")
        )

        for sup in active_suppliers:
            supplier_name = _supplier_display_name(sup)
            created_dt = sup.created_at or _date_to_aware_dt(sup.date)
            sup_meta = {
                "supplier_number": sup.supplier_number,
                "supplier_type": sup.supplier_type,
                "supplier_name": supplier_name,
                "email": sup.email,
                "phone": sup.phone,
                "mobile": sup.mobile,
                "is_active": sup.is_active,
            }

            missing_fields = []
            if sup.supplier_type == "Business":
                if not (sup.company_name or "").strip():
                    missing_fields.append("company_name")
                if not (sup.contact_person_name or "").strip():
                    missing_fields.append("contact_person_name")
                if not (sup.contact_person_number or "").strip():
                    missing_fields.append("contact_person_number")
            else:
                if not (sup.first_name or "").strip():
                    missing_fields.append("first_name")
            if not (sup.address or "").strip():
                missing_fields.append("address")

            if missing_fields:
                add_item(
                    tab_key="supplier",
                    work_type="supplier_incomplete_profile",
                    work_type_label="Incomplete Supplier Profile",
                    title=f"{sup.supplier_number} ({supplier_name}) - Incomplete Profile",
                    description=f"Supplier profile is missing: {', '.join(missing_fields)}.",
                    urgency="medium",
                    record_id=sup.id,
                    item_id=f"sup_profile_{sup.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/suppliers/{sup.id}/",
                    meta={**sup_meta, "missing_fields": missing_fields},
                )

            if sup.payment_terms_id is None:
                add_item(
                    tab_key="supplier",
                    work_type="supplier_missing_payment_terms",
                    work_type_label="Missing Payment Terms",
                    title=f"{sup.supplier_number} ({supplier_name}) - No Payment Terms",
                    description="Supplier has no default payment terms assigned.",
                    urgency="low",
                    record_id=sup.id,
                    item_id=f"sup_terms_{sup.id}",
                    created_at=created_dt,
                    action_url=f"/accounts/suppliers/{sup.id}/",
                    meta=sup_meta,
                )

        return self._build_response(request, tab_items, tab_categories)
