from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from activity_logs.base_view import BaseGenericAPIView
from ..models import CreditNote, DebitNote
from ..serializers.documents import CreditNoteSerializer, DebitNoteSerializer

class CreditNoteListCreateAPIView(BaseGenericAPIView, generics.ListCreateAPIView):
    queryset = CreditNote.objects.all().order_by('-created_at')
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]

class CreditNoteRetrieveUpdateDestroyAPIView(BaseGenericAPIView, generics.RetrieveUpdateDestroyAPIView):
    queryset = CreditNote.objects.all()
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]

class DebitNoteListCreateAPIView(BaseGenericAPIView, generics.ListCreateAPIView):
    queryset = DebitNote.objects.all().order_by('-created_at')
    serializer_class = DebitNoteSerializer
    permission_classes = [IsAuthenticated]

class DebitNoteRetrieveUpdateDestroyAPIView(BaseGenericAPIView, generics.RetrieveUpdateDestroyAPIView):
    queryset = DebitNote.objects.all()
    serializer_class = DebitNoteSerializer
    permission_classes = [IsAuthenticated]
