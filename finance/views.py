from django.views import View
from django.http import HttpResponse
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import *
from .serializers import *

from .utils import generate_next_number


from rest_framework import generics
from .models import Account
from .serializers import AccountSerializer
from .filters import JournalLineFlatFilter

class AccountListCreateAPIView(generics.ListCreateAPIView):
    queryset = Account.objects.all().order_by('-created_at')
    serializer_class = AccountSerializer

class AccountRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

class JournalEntryListCreateView(generics.ListCreateAPIView):
    queryset = JournalEntry.objects.all().order_by('-created_at')
    serializer_class = JournalEntrySerializer

class JournalEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

class FinaceNumberGeneratorView(APIView):
    def get(self, request):
        model_type = request.query_params.get('type')

        model_map = {
            'ACT': (Account, 'account_number', 'ACT'),
            'JE': (JournalEntry, 'type_number', 'JE'),
        }

        if model_type not in model_map:
            return Response({
                'status': '0',
                'message': 'Invalid order type',
            }, status=status.HTTP_400_BAD_REQUEST)

        model, field_name, prefix = model_map[model_type]
        number = generate_next_number(model, field_name, prefix, 6)

        return Response({
            'status': '1',
            'message': 'Success',
            'number': number
        }, status=status.HTTP_200_OK)


class JournalLineListView(generics.ListAPIView):
    serializer_class = JournalLineListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalLineFlatFilter
    def get_queryset(self):
        # Optimized: fetch related objects in one query
        return (
            JournalLine.objects
            .select_related('journal', 'journal__user', 'journal__salesperson', 'account')
            .order_by('-created_at')
        )


class JournalLineDetailView(generics.RetrieveAPIView):
    queryset = JournalLine.objects.select_related(
        'journal', 'account', 'journal__user'
    )
    serializer_class = JournalLineDetailSerializer
    lookup_field = 'id'