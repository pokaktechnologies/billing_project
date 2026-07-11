from activity_logs.base_view import BaseGenericAPIView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from ..models import PaymentVoucher
from ..serializers.payment_voucher import PaymentVoucherSerializer

class PaymentVoucherListCreateAPIView(BaseGenericAPIView, generics.ListCreateAPIView):
    queryset = PaymentVoucher.objects.all().order_by("-created_at")
    serializer_class = PaymentVoucherSerializer
    permission_classes = [IsAuthenticated]

class PaymentVoucherRetrieveUpdateDestroyAPIView(BaseGenericAPIView, generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentVoucher.objects.all()
    serializer_class = PaymentVoucherSerializer
    permission_classes = [IsAuthenticated]

