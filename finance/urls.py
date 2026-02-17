from django.urls import path
from .views.accounts import AccountListCreateAPIView, AccountRetrieveUpdateDestroyAPIView, GenerateAccountNumberView, AccountTypeListView
from .views.ledger import (
    JournalEntryListCreateView, JournalEntryDetailView, ListJournalVoucherView, 
    JournalLineListView, JournalLineDetailView, JournalEntryReportView
)
from .views.documents import CreditNoteListCreateAPIView, CreditNoteRetrieveUpdateDestroyAPIView, DebitNoteListCreateAPIView, DebitNoteRetrieveUpdateDestroyAPIView
from .views.settings import FinaceNumberGeneratorView, CashflowCategoryMappingListCreateView, CashflowCategoryMappingDetailView, TaxSettingsListCreateAPIView, TaxSettingsRetrieveUpdateDestroyAPIView
from .views.reports import TrialBalanceView, ProfitAndLossView, BalanceSheetView, CashflowStatementView, AccountBalanceHierarchyView
from .views.FinanceReport import JournalVoucherReportView, AccountReportView, LedgerReportView, TransactionDebitNotReportView, TransactionCreditNotReportView

urlpatterns = [
    path('account/', AccountListCreateAPIView.as_view(), name='account'),
    path('account-types/', AccountTypeListView.as_view(), name='account-types'),
    path('account/<int:pk>/', AccountRetrieveUpdateDestroyAPIView.as_view(), name='account-detail'),
    path('generate-account-number/', GenerateAccountNumberView.as_view(), name='generate-account-number'),

    path('journal-entry/', JournalEntryListCreateView.as_view(), name='journal-entry'),
    path('journal-entry/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-entry-detail'),
    path('journal-voucher/', ListJournalVoucherView.as_view(), name='journal-voucher'),
    path('journal-report/', JournalEntryReportView.as_view(), name='journal-report'),

    path('journal-lines/', JournalLineListView.as_view(), name='journal-lines-flat'),
    path('journal-lines/<int:id>/', JournalLineDetailView.as_view(), name='journalline-detail'),
    path('generate-number/', FinaceNumberGeneratorView.as_view(), name='serial_number'),

    # Credit Note
    path('credit-notes/', CreditNoteListCreateAPIView.as_view(), name='creditnote-list'),
    path('credit-notes/<int:pk>/', CreditNoteRetrieveUpdateDestroyAPIView.as_view(), name='creditnote-detail'),
    path('debit-notes/', DebitNoteListCreateAPIView.as_view(), name='debitnote-list'),
    path('debit-notes/<int:pk>/', DebitNoteRetrieveUpdateDestroyAPIView.as_view(), name='debitnote-detail'),

    path('trial-balance/', TrialBalanceView.as_view(), name='trial-balance'),
    path('profit-and-loss/', ProfitAndLossView.as_view(), name='profit-and-loss'),
    path('balance-sheet/', BalanceSheetView.as_view(), name='balance-sheet'),

    path('cashflow-mappings/', CashflowCategoryMappingListCreateView.as_view(), name='cashflow-mapping-list'),
    path('cashflow-mappings/<int:pk>/', CashflowCategoryMappingDetailView.as_view(), name='cashflow-mapping-detail'),
    path('cashflow-statement/', CashflowStatementView.as_view(), name='cashflow-statement'),
    path('hierarchical-balance/', AccountBalanceHierarchyView.as_view(), name='hierarchical-balance'),

    # Tax Settings
    path('tax-settings/', TaxSettingsListCreateAPIView.as_view(), name='tax-settings'),
    path('tax-settings/<int:pk>/', TaxSettingsRetrieveUpdateDestroyAPIView.as_view(), name='tax-settings-detail'),

    # Finance Report 
    path('reports/journal-voucher/', JournalVoucherReportView.as_view(), name='journal-voucher-report'),
    path('reports/account/', AccountReportView.as_view(), name='account-report'),
    path('reports/ledger/', LedgerReportView.as_view(), name='ledger-report'),
    path('reports/transaction/debit/', TransactionDebitNotReportView.as_view(), name='transaction-report-debit'),
    path('reports/transaction/credit/', TransactionCreditNotReportView.as_view(), name='transaction-report-credit')
]

