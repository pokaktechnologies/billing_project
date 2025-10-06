from django.urls import path
from .views import *

urlpatterns = [
    path('account/', AccountListCreateAPIView.as_view(), name='account'),
    path('account/<int:pk>/', AccountRetrieveUpdateDestroyAPIView.as_view(), name='account-detail'),

    path('journal-entry/', JournalEntryListCreateView.as_view(), name='journal-entry'),
    path('journal-entry/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-entry-detail'),

    # path('payment/', PaymentAPIView.as_view(), name='payment'),
    # path('payment/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),

    path('generate-number/',FinaceNumberGeneratorView.as_view(), name='serial_number'),
]

