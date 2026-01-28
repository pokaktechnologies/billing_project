from rest_framework import generics
from ..models import Account
from ..serializers.accounts import AccountSerializer

class AccountListCreateAPIView(generics.ListCreateAPIView):
    queryset = Account.objects.all().order_by('-created_at')
    # Use serializer from the new modular path
    serializer_class = AccountSerializer

class AccountRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
