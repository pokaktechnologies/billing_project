from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ..models import JournalEntry, JournalLine
from ..serializers.ledger import JournalEntrySerializer, JournalLineListSerializer, JournalLineDetailSerializer
from ..filters import JournalLineFlatFilter, JournalEntryFilter
from django.db.models import Sum
from django.db import models
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from collections import OrderedDict

class JournalEntryListCreateView(generics.ListCreateAPIView):
    queryset = JournalEntry.objects.all().order_by('-created_at')
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

class JournalEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

class ListJournalVoucherView(generics.ListAPIView):
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JournalEntry.objects.filter(type='journal_voucher').order_by('-created_at')

class JournalLineListView(generics.ListAPIView):
    serializer_class = JournalLineListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalLineFlatFilter

    def get_queryset(self):
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

class JournalReportPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class JournalEntryReportView(generics.ListAPIView):
    queryset = JournalEntry.objects.all().prefetch_related('lines', 'lines__account').order_by('-date', '-id')
    serializer_class = JournalEntrySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalEntryFilter
    pagination_class = JournalReportPagination
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Calculate summary for the entire filtered queryset
        summary_data = queryset.aggregate(
            total_debit=Sum('lines__debit'),
            total_credit=Sum('lines__credit')
        )
        summary = {
            'total_debit': summary_data['total_debit'] or 0,
            'total_credit': summary_data['total_credit'] or 0
        }

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            
            # Reconstruct response data to put summary at the top
            new_data = OrderedDict()
            new_data['summary'] = summary
            new_data['count'] = response.data['count']
            new_data['next'] = response.data['next']
            new_data['previous'] = response.data['previous']
            new_data['results'] = response.data['results']
            
            response.data = new_data
            return response

        # Non-paginated
        serializer = self.get_serializer(queryset, many=True)
        return Response(OrderedDict([
            ('summary', summary),
            ('results', serializer.data)
        ]))

