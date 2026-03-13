from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from activity_logs.base_view import BaseModelViewSet
from ..models import Holiday
from ..serializers import HolidaySerializer

class HolidayViewSet(BaseModelViewSet):
    queryset = Holiday.objects.all().order_by('-date')
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]
