from rest_framework import generics
from ..models import PayrollPeriod
from ..serializers.payroll_period import PayrollPeriodSerializer

class PayrollPeriodListView(generics.ListCreateAPIView):
    queryset = PayrollPeriod.objects.all().order_by('-month')
    serializer_class = PayrollPeriodSerializer

class PayrollPeriodDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PayrollPeriod.objects.all()
    serializer_class = PayrollPeriodSerializer
