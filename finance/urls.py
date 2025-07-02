from django.urls import path
from .views import *

urlpatterns = [
    path('account/', AccountView.as_view(), name='account'),
    path('account/<int:pk>/', AccountDetailView.as_view(), name='account-detail'),

    path('journal-entry/', JournalEntryView.as_view(), name='journal-entry'),
    path('journal-entry/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-entry-detail'),

    path('payment/', PaymentAPIView.as_view(), name='payment'),
    path('payment/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),

    path('generate-number/',FinaceNumberGeneratorView.as_view(), name='serial_number'),
]

