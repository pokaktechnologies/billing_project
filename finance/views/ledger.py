from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ..models import JournalEntry, JournalLine
from ..serializers.ledger import JournalEntrySerializer, JournalLineListSerializer, JournalLineDetailSerializer
from ..filters import JournalLineFlatFilter

class JournalEntryListCreateView(generics.ListCreateAPIView):
    queryset = JournalEntry.objects.all().order_by('-created_at')
    serializer_class = JournalEntrySerializer
    # Complex creation logic is currently in Serializer.create() (as placeholder for further refactoring if desired)

class JournalEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

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
