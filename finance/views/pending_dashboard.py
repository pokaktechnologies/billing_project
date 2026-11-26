from datetime import datetime, time, timedelta
from decimal import Decimal
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import (
    InvoiceModel,
    ReceiptModel,
    SalesReturnModel,
)
from finance.models import (
    Account,
    CashflowCategoryMapping,
    CreditNote,
    DebitNote,
    FinancialYear,
    JournalEntry,
    PaymentVoucher,
    TaxSettings,
)
from internship.models import (
    InternshipApplication,
    StudentInstallmentItem,
)
from payroll.models import Payroll


def _date_to_aware_dt(date_val):
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return timezone.make_aware(date_val) if timezone.is_naive(date_val) else date_val
    return timezone.make_aware(datetime.combine(date_val, time.min))


class FinancePendingDashboardAPIView(APIView):
    """
    Finance Module Pending Controls Dashboard API.

    Aggregates actionable pending items across Finance & cross-module financial flows:
      - payment_voucher: Draft payment vouchers, posted vouchers missing journal entries
      - journal_entries: Unbalanced journal entries, entries with no lines, missing narration
      - transactions: Unposted/unlinked credit notes, unposted/zero-amount debit notes
      - invoices_receipts: Invoices/receipts missing journal entries, overdue receivables, approved sales returns awaiting settlement
      - accounts_admissions: Overdue student installments, unreceipted intern invoices, unconfirmed admission slots
      - financial_year: Missing current open FY, expired open FY, unmapped cashflow accounts, no active tax settings
      - payroll: Draft/unpaid payroll records

    Query Parameters:
      - tab: 'all' (default), 'payment_voucher', 'journal_entries', 'transactions',
             'invoices_receipts', 'accounts_admissions', 'financial_year', 'payroll'
      - urgency: 'high', 'medium', 'low'
      - search: Case-insensitive search across title, description, and meta
      - limit: Maximum items to return (default: 100)
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "payment_voucher", "label": "Payment Vouchers"},
        {"key": "journal_entries", "label": "Journal Entries"},
        {"key": "transactions", "label": "Credit & Debit Notes"},
        {"key": "invoices_receipts", "label": "Invoices & Receipts"},
        {"key": "accounts_admissions", "label": "Admissions & Fees"},
        {"key": "financial_year", "label": "Financial Year & Setup"},
        {"key": "payroll", "label": "Payroll Disbursements"},
    ]

    def get(self, request):
        today = timezone.localdate()

        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()

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

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": tab_labels.get(tab_key, tab_key.replace("_", " ").title()),
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

        # =====================================================================
        # 1. TAB: PAYMENT VOUCHERS
        # =====================================================================
        draft_vouchers = PaymentVoucher.objects.filter(status="draft")
        for pv in draft_vouchers:
            days_pending = (today - pv.date).days if pv.date else 0
            urgency = "high" if days_pending > 3 else "medium"
            add_item(
                tab_key="payment_voucher",
                work_type="payment_voucher_draft",
                work_type_label="Draft Payment Voucher",
                title=f"{pv.voucher_number} ({pv.pay_to}) - Draft",
                description=f"Payment voucher for ₹{pv.amount} dated {pv.date.strftime('%d-%b-%Y')} is still in draft.",
                urgency=urgency,
                record_id=pv.id,
                item_id=f"fin_pv_draft_{pv.id}",
                created_at=pv.created_at,
                action_url=f"/finance/payment-vouchers/{pv.id}/",
                meta={
                    "voucher_number": pv.voucher_number,
                    "pay_to": pv.pay_to,
                    "amount": str(pv.amount),
                    "payment_method": pv.payment_method,
                    "days_pending": days_pending,
                },
            )

        unposted_vouchers = PaymentVoucher.objects.filter(status="posted", journal_entry__isnull=True)
        for pv in unposted_vouchers:
            add_item(
                tab_key="payment_voucher",
                work_type="payment_voucher_unposted_journal",
                work_type_label="Posted Voucher Missing Journal",
                title=f"{pv.voucher_number} ({pv.pay_to}) - Missing Journal Entry",
                description=f"Posted payment voucher for ₹{pv.amount} has no linked journal entry.",
                urgency="high",
                record_id=pv.id,
                item_id=f"fin_pv_unjournal_{pv.id}",
                created_at=pv.created_at,
                action_url=f"/finance/payment-vouchers/{pv.id}/",
                meta={
                    "voucher_number": pv.voucher_number,
                    "pay_to": pv.pay_to,
                    "amount": str(pv.amount),
                },
            )

        # =====================================================================
        # 2. TAB: JOURNAL ENTRIES
        # =====================================================================
        journal_entries = JournalEntry.objects.annotate(
            line_count=Count("lines"),
            debit_sum=Coalesce(Sum("lines__debit"), Value(0), output_field=DecimalField()),
            credit_sum=Coalesce(Sum("lines__credit"), Value(0), output_field=DecimalField()),
        )

        for je in journal_entries:
            if je.line_count == 0:
                add_item(
                    tab_key="journal_entries",
                    work_type="journal_entry_no_lines",
                    work_type_label="Journal Entry Without Lines",
                    title=f"Journal #{je.id} ({je.type_number or je.type or 'Entry'}) - No Lines",
                    description="Journal entry has zero debit/credit lines.",
                    urgency="high",
                    record_id=je.id,
                    item_id=f"fin_je_nolines_{je.id}",
                    created_at=je.created_at,
                    action_url=f"/finance/journal-entry/{je.id}/",
                    meta={"journal_id": je.id, "type": je.type, "type_number": je.type_number},
                )
            elif round(je.debit_sum, 2) != round(je.credit_sum, 2):
                add_item(
                    tab_key="journal_entries",
                    work_type="journal_entry_unbalanced",
                    work_type_label="Unbalanced Journal Entry",
                    title=f"Journal #{je.id} ({je.type_number or je.type or 'Entry'}) - Unbalanced",
                    description=f"Debit ₹{je.debit_sum} != Credit ₹{je.credit_sum}.",
                    urgency="high",
                    record_id=je.id,
                    item_id=f"fin_je_unbal_{je.id}",
                    created_at=je.created_at,
                    action_url=f"/finance/journal-entry/{je.id}/",
                    meta={
                        "journal_id": je.id,
                        "type": je.type,
                        "type_number": je.type_number,
                        "debit_sum": str(je.debit_sum),
                        "credit_sum": str(je.credit_sum),
                    },
                )
            elif je.type == "journal_voucher" and not (je.narration or "").strip():
                add_item(
                    tab_key="journal_entries",
                    work_type="journal_entry_missing_narration",
                    work_type_label="Journal Voucher Missing Narration",
                    title=f"Journal Voucher #{je.id} ({je.type_number or 'N/A'}) - Missing Narration",
                    description="Journal voucher has no narration/remarks.",
                    urgency="low",
                    record_id=je.id,
                    item_id=f"fin_je_nonarr_{je.id}",
                    created_at=je.created_at,
                    action_url=f"/finance/journal-entry/{je.id}/",
                    meta={"journal_id": je.id, "type_number": je.type_number},
                )

        # =====================================================================
        # 3. TAB: TRANSACTIONS (Credit & Debit Notes)
        # =====================================================================
        credit_notes = CreditNote.objects.filter(
            Q(journal_entry__isnull=True) | Q(invoice__isnull=True)
        ).select_related("client")

        for cn in credit_notes:
            client_name = str(cn.client) if cn.client else "Unknown Client"
            if cn.journal_entry_id is None:
                add_item(
                    tab_key="transactions",
                    work_type="credit_note_unposted",
                    work_type_label="Credit Note Not Posted",
                    title=f"{cn.credit_note_number} ({client_name}) - Not Posted to Ledger",
                    description=f"Credit note for ₹{cn.grand_total} has no linked journal entry.",
                    urgency="high",
                    record_id=cn.id,
                    item_id=f"fin_cn_unposted_{cn.id}",
                    created_at=cn.created_at,
                    action_url=f"/finance/credit-notes/{cn.id}/",
                    meta={"credit_note_number": cn.credit_note_number, "grand_total": str(cn.grand_total)},
                )
            if cn.invoice_id is None:
                add_item(
                    tab_key="transactions",
                    work_type="credit_note_unlinked_invoice",
                    work_type_label="Credit Note Unlinked to Invoice",
                    title=f"{cn.credit_note_number} ({client_name}) - No Invoice Linked",
                    description="Credit note is not linked to an original invoice.",
                    urgency="medium",
                    record_id=cn.id,
                    item_id=f"fin_cn_unlinked_{cn.id}",
                    created_at=cn.created_at,
                    action_url=f"/finance/credit-notes/{cn.id}/",
                    meta={"credit_note_number": cn.credit_note_number, "grand_total": str(cn.grand_total)},
                )

        debit_notes = DebitNote.objects.filter(
            Q(journal_entry__isnull=True) | Q(grand_total__lte=0)
        ).select_related("supplier")

        for dn in debit_notes:
            supplier_name = str(dn.supplier) if dn.supplier else "Unknown Supplier"
            if dn.journal_entry_id is None:
                add_item(
                    tab_key="transactions",
                    work_type="debit_note_unposted",
                    work_type_label="Debit Note Not Posted",
                    title=f"{dn.debit_note_number} ({supplier_name}) - Not Posted to Ledger",
                    description=f"Debit note for ₹{dn.grand_total} has no linked journal entry.",
                    urgency="high",
                    record_id=dn.id,
                    item_id=f"fin_dn_unposted_{dn.id}",
                    created_at=dn.created_at,
                    action_url=f"/finance/debit-notes/{dn.id}/",
                    meta={"debit_note_number": dn.debit_note_number, "grand_total": str(dn.grand_total)},
                )
            if (dn.grand_total or Decimal("0")) <= 0:
                add_item(
                    tab_key="transactions",
                    work_type="debit_note_zero_amount",
                    work_type_label="Debit Note Zero Amount",
                    title=f"{dn.debit_note_number} ({supplier_name}) - Zero Amount",
                    description="Debit note has ₹0.00 grand total (no line items).",
                    urgency="medium",
                    record_id=dn.id,
                    item_id=f"fin_dn_zero_{dn.id}",
                    created_at=dn.created_at,
                    action_url=f"/finance/debit-notes/{dn.id}/",
                    meta={"debit_note_number": dn.debit_note_number},
                )

        # =====================================================================
        # 4. TAB: INVOICES & RECEIPTS (Cross-Module from accounts)
        # =====================================================================
        posted_invoice_numbers = set(
            JournalEntry.objects.filter(type="invoice").values_list("type_number", flat=True)
        )
        posted_receipt_numbers = set(
            JournalEntry.objects.filter(type="receipt").values_list("type_number", flat=True)
        )

        invoices = InvoiceModel.objects.filter(invoice_grand_total__gt=0).select_related("client")
        overdue_cutoff = today - timedelta(days=30)

        for inv in invoices:
            if inv.invoice_number not in posted_invoice_numbers:
                add_item(
                    tab_key="invoices_receipts",
                    work_type="invoice_missing_journal",
                    work_type_label="Invoice Missing Journal Entry",
                    title=f"{inv.invoice_number} - Missing Ledger Journal",
                    description=f"Invoice ({inv.invoice_type}) for ₹{inv.invoice_grand_total} has no journal entry.",
                    urgency="high",
                    record_id=inv.id,
                    item_id=f"fin_inv_noje_{inv.id}",
                    created_at=inv.created_at,
                    action_url=f"/accounts/invoice/{inv.id}/",
                    meta={
                        "invoice_number": inv.invoice_number,
                        "invoice_type": inv.invoice_type,
                        "grand_total": str(inv.invoice_grand_total),
                    },
                )

            if inv.invoice_type == "client" and not inv.is_receipted and inv.invoice_date and inv.invoice_date < overdue_cutoff:
                days_overdue = (today - inv.invoice_date).days
                add_item(
                    tab_key="invoices_receipts",
                    work_type="invoice_overdue_receivable",
                    work_type_label="Overdue Receivable (>30 Days)",
                    title=f"{inv.invoice_number} - Overdue Receivable ({days_overdue}d)",
                    description=f"Client invoice dated {inv.invoice_date.strftime('%d-%b-%Y')} for ₹{inv.invoice_grand_total} is unreceipted.",
                    urgency="high",
                    record_id=inv.id,
                    item_id=f"fin_inv_overdue_{inv.id}",
                    created_at=inv.created_at,
                    due_date=inv.invoice_date + timedelta(days=30),
                    action_url=f"/accounts/invoice/{inv.id}/",
                    meta={
                        "invoice_number": inv.invoice_number,
                        "grand_total": str(inv.invoice_grand_total),
                        "days_overdue": days_overdue,
                    },
                )

        receipts = ReceiptModel.objects.filter(
            Q(cheque_amount__gt=0) | Q(total_amount__gt=0)
        )
        for rec in receipts:
            if rec.receipt_number not in posted_receipt_numbers:
                amt = rec.total_amount or rec.cheque_amount or Decimal("0")
                add_item(
                    tab_key="invoices_receipts",
                    work_type="receipt_missing_journal",
                    work_type_label="Receipt Missing Journal Entry",
                    title=f"{rec.receipt_number} - Missing Ledger Journal",
                    description=f"Receipt ({rec.receipt_type}) for ₹{amt} has no journal entry.",
                    urgency="high",
                    record_id=rec.id,
                    item_id=f"fin_rec_noje_{rec.id}",
                    created_at=rec.created_at,
                    action_url=f"/accounts/receipt/{rec.id}/",
                    meta={"receipt_number": rec.receipt_number, "amount": str(amt)},
                )

        approved_returns = SalesReturnModel.objects.filter(status="approved").select_related("client")
        for sr in approved_returns:
            add_item(
                tab_key="invoices_receipts",
                work_type="sales_return_pending_settlement",
                work_type_label="Sales Return Pending Settlement",
                title=f"{sr.return_number} - Approved Return Awaiting Settlement",
                description=f"Approved sales return for ₹{sr.grand_total} is awaiting financial settlement.",
                urgency="high",
                record_id=sr.id,
                item_id=f"fin_sr_settle_{sr.id}",
                created_at=sr.created_at,
                action_url=f"/accounts/sales-returns/{sr.id}/",
                meta={"return_number": sr.return_number, "grand_total": str(sr.grand_total)},
            )

        # =====================================================================
        # 5. TAB: ACCOUNTS ADMISSIONS & FEES (Cross-Module from internship/accounts)
        # =====================================================================
        unpaid_installments = StudentInstallmentItem.objects.filter(
            course_payments__isnull=True
        ).select_related("enrollment", "enrollment__student", "enrollment__student__profile", "enrollment__student__profile__user", "enrollment__course")

        for inst in unpaid_installments:
            due_dt = inst.enrollment.enrollment_date + timedelta(days=inst.due_days)
            if due_dt < today:
                days_overdue = (today - due_dt).days
                urgency = "high" if days_overdue > 7 else "medium"
                student = inst.enrollment.student
                student_name = student.profile.user.get_full_name() if student and student.profile and student.profile.user else "Student"
                add_item(
                    tab_key="accounts_admissions",
                    work_type="overdue_student_installment",
                    work_type_label="Overdue Student Installment",
                    title=f"{student_name} - Installment #{inst.installment_number} Overdue ({days_overdue}d)",
                    description=f"Installment of ₹{inst.amount} for {inst.enrollment.course.title} was due on {due_dt.strftime('%d-%b-%Y')}.",
                    urgency=urgency,
                    record_id=inst.id,
                    item_id=f"fin_adm_inst_{inst.id}",
                    due_date=due_dt,
                    action_url="/internship/payments/",
                    meta={
                        "installment_id": inst.id,
                        "student_id": student.id,
                        "student_name": student_name,
                        "amount": str(inst.amount),
                        "days_overdue": days_overdue,
                    },
                )

        unreceipted_intern_invoices = InvoiceModel.objects.filter(
            invoice_type="intern",
            is_receipted=False,
        )
        for inv in unreceipted_intern_invoices:
            days_pending = (today - inv.invoice_date).days if inv.invoice_date else 0
            urgency = "high" if days_pending > 7 else "medium"
            add_item(
                tab_key="accounts_admissions",
                work_type="intern_invoice_unreceipted",
                work_type_label="Unreceipted Intern Invoice",
                title=f"{inv.invoice_number} - Intern Invoice Unreceipted",
                description=f"Intern invoice for ₹{inv.invoice_grand_total} has not been receipted.",
                urgency=urgency,
                record_id=inv.id,
                item_id=f"fin_adm_inv_{inv.id}",
                created_at=inv.created_at,
                action_url=f"/accounts/invoice/{inv.id}/",
                meta={"invoice_number": inv.invoice_number, "grand_total": str(inv.invoice_grand_total)},
            )

        unconfirmed_slots = InternshipApplication.objects.filter(
            is_converted=False,
            slot_amount__gt=0,
            slot_payment_date__isnull=True,
        ).select_related("course")
        for app in unconfirmed_slots:
            applicant_name = f"{app.first_name} {app.last_name}".strip()
            add_item(
                tab_key="accounts_admissions",
                work_type="admission_slot_unconfirmed",
                work_type_label="Admission Slot Payment Unconfirmed",
                title=f"{applicant_name} - Slot Payment Unconfirmed (₹{app.slot_amount})",
                description=f"Slot amount ₹{app.slot_amount} for {app.course.title if app.course else 'Course'} is awaiting payment confirmation.",
                urgency="high",
                record_id=app.id,
                item_id=f"fin_adm_slot_{app.id}",
                created_at=app.created_at,
                action_url=f"/internship/applications/{app.id}/slot-confirmation/",
                meta={"application_id": app.id, "applicant_name": applicant_name, "slot_amount": str(app.slot_amount)},
            )

        # =====================================================================
        # 6. TAB: FINANCIAL YEAR & SETUP
        # =====================================================================
        if not FinancialYear.objects.filter(is_current=True, status="open").exists():
            add_item(
                tab_key="financial_year",
                work_type="no_current_financial_year",
                work_type_label="No Current Open Financial Year",
                title="No Active Current Financial Year Configured",
                description="No open Financial Year is marked as current.",
                urgency="high",
                record_id=0,
                item_id="fin_fy_no_current",
                action_url="/finance/financial-years/",
            )

        expired_open_fys = FinancialYear.objects.filter(status="open", end_date__lt=today)
        for fy in expired_open_fys:
            add_item(
                tab_key="financial_year",
                work_type="expired_open_financial_year",
                work_type_label="Expired Open Financial Year",
                title=f"Financial Year '{fy.name}' - Past End Date",
                description=f"Ended on {fy.end_date.strftime('%d-%b-%Y')} but is still open.",
                urgency="high",
                record_id=fy.id,
                item_id=f"fin_fy_expired_{fy.id}",
                due_date=fy.end_date,
                action_url=f"/finance/financial-years/{fy.id}/",
                meta={"financial_year_id": fy.id, "name": fy.name, "end_date": fy.end_date.isoformat()},
            )

        mapped_account_ids = set(
            CashflowCategoryMapping.objects.values_list("accounts__id", flat=True)
        )
        unmapped_accounts = Account.objects.filter(is_posting=True, status="active").exclude(id__in=mapped_account_ids)
        for acc in unmapped_accounts:
            add_item(
                tab_key="financial_year",
                work_type="unmapped_cashflow_account",
                work_type_label="Unmapped Cashflow Account",
                title=f"{acc.account_number} {acc.name} - Not Mapped to Cashflow",
                description="Active posting account is not mapped to any Cashflow Category.",
                urgency="low",
                record_id=acc.id,
                item_id=f"fin_acc_unmapped_{acc.id}",
                created_at=acc.created_at,
                action_url="/finance/cashflow-mappings/",
                meta={"account_id": acc.id, "account_number": acc.account_number, "name": acc.name},
            )

        if not TaxSettings.objects.filter(is_active=True).exists():
            add_item(
                tab_key="financial_year",
                work_type="no_active_tax_setting",
                work_type_label="No Active Tax Settings",
                title="No Active Tax Settings Found",
                description="At least one active tax setting should be configured.",
                urgency="medium",
                record_id=0,
                item_id="fin_tax_none",
                action_url="/finance/tax-settings/",
            )

        # =====================================================================
        # 7. TAB: PAYROLL DISBURSEMENTS (Cross-Module from payroll)
        # =====================================================================
        current_month_str = today.strftime("%Y-%m")
        draft_payrolls = Payroll.objects.filter(status="Draft").select_related("staff", "staff__user")
        for pr in draft_payrolls:
            staff_name = pr.staff.user.get_full_name() if pr.staff and pr.staff.user else "Staff"
            urgency = "high" if pr.month < current_month_str else "medium"
            add_item(
                tab_key="payroll",
                work_type="payroll_draft_unpaid",
                work_type_label="Unpaid Draft Payroll",
                title=f"{staff_name} ({pr.month}) - Payroll Draft (₹{pr.net_salary})",
                description=f"Payroll for {pr.month} (net ₹{pr.net_salary}) is still in Draft status.",
                urgency=urgency,
                record_id=pr.id,
                item_id=f"fin_pr_draft_{pr.id}",
                created_at=pr.created_at,
                action_url="/payroll/",
                meta={
                    "payroll_id": pr.id,
                    "staff_name": staff_name,
                    "month": pr.month,
                    "net_salary": str(pr.net_salary),
                },
            )

        # =====================================================================
        # BUILD TAB METADATA & FILTERING
        # =====================================================================
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
            for k in [t["key"] for t in self.TAB_DEFINITIONS]:
                combined_items.extend(tab_items[k])

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

        return Response(
            {
                "module": "finance",
                "module_label": "Finance",
                "total_pending_count": total_pending_count,
                "tab_counts": tab_counts,
                "tabs": tabs_data,
                "active_tab": active_tab,
                "items_count": len(combined_items),
                "items": combined_items,
            },
            status=status.HTTP_200_OK,
        )
