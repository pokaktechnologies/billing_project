from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from ..models import CreditNote, DebitNote
from ..serializers.documents import CreditNoteSerializer, DebitNoteSerializer

class CreditNoteListCreateAPIView(generics.ListCreateAPIView):
    queryset = CreditNote.objects.all().order_by('-created_at')
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]

class CreditNoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CreditNote.objects.all()
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]

class DebitNoteListCreateAPIView(generics.ListCreateAPIView):
    queryset = DebitNote.objects.all().order_by('-created_at')
    serializer_class = DebitNoteSerializer
    permission_classes = [IsAuthenticated]

class DebitNoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DebitNote.objects.all()
    serializer_class = DebitNoteSerializer
    permission_classes = [IsAuthenticated]
