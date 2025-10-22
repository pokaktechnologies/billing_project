from django.urls import path
from .views import *

urlpatterns = [
    path('account/', AccountListCreateAPIView.as_view(), name='account'),
    path('account/<int:pk>/', AccountRetrieveUpdateDestroyAPIView.as_view(), name='account-detail'),

    path('journal-entry/', JournalEntryListCreateView.as_view(), name='journal-entry'),
    path('journal-entry/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-entry-detail'),
    path('journal-voucher/', ListJournalVoucherView.as_view(), name='journal-voucher'),

    # path('payment/', PaymentAPIView.as_view(), name='payment'),
    # path('payment/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('journal-lines/', JournalLineListView.as_view(), name='journal-lines-flat'),
    path('journal-lines/<int:id>/', JournalLineDetailView.as_view(), name='journalline-detail'),
    path('generate-number/',FinaceNumberGeneratorView.as_view(), name='serial_number'),

        # Credit Note
    path('credit-notes/', CreditNoteListCreateAPIView.as_view(), name='creditnote-list'),
    path('credit-notes/<int:pk>/', CreditNoteRetrieveUpdateDestroyAPIView.as_view(), name='creditnote-detail'),
    path('debit-notes/', DebitNoteListCreateAPIView.as_view(), name='debitnote-list'),
    path('debit-notes/<int:pk>/', DebitNoteRetrieveUpdateDestroyAPIView.as_view(), name='debitnote-detail'),

    path('profit-and-loss/',ProfitAndLossView.as_view(), name='profit-and-loss')
]

