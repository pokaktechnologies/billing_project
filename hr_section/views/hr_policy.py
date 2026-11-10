from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import HasModulePermission
from ..models import HRPolicy
from ..serializers import HRPolicySerializer


class HRPolicyViewSet(viewsets.ModelViewSet):
    """
    CRUD API for HR Policies.
    Supports filtering by category and status, searching by title and policy_code,
    and sorting.
    """
    queryset = HRPolicy.objects.select_related('created_by').all()
    serializer_class = HRPolicySerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category']
    search_fields = ['title', 'policy_code', 'description', 'content']
    ordering_fields = ['created_at', 'updated_at', 'effective_date', 'title']
    ordering = ['-created_at']

