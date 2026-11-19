from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import HasModulePermission
from ..models import HRPolicy, HRPolicySection, HRPolicySubtitle, HRPolicyPoint
from ..serializers import (
    HRPolicyListSerializer,
    HRPolicyDetailSerializer,
    HRPolicyCreateSerializer,
    HRPolicyPatchSerializer,
    HRPolicySectionSerializer,
    HRPolicySubtitleSerializer,
    HRPolicySectionWriteSerializer,
    HRPolicySubtitleWriteSerializer,
    HRPolicyPointWriteSerializer,
)


PERMISSIONS = [IsAuthenticated, HasModulePermission]


def _policy_tree_queryset():
    return HRPolicy.objects.select_related('created_by').annotate(
        sections_count=Count('sections', distinct=True)
    ).prefetch_related(
        Prefetch('sections', queryset=HRPolicySection.objects.order_by('id')),
        Prefetch('sections__direct_points', queryset=HRPolicyPoint.objects.order_by('id')),
        Prefetch('sections__subtitles', queryset=HRPolicySubtitle.objects.order_by('id')),
        Prefetch('sections__subtitles__points', queryset=HRPolicyPoint.objects.order_by('id')),
    )


class HRPolicyViewSet(viewsets.ModelViewSet):
    """
    /hr/policies/          GET list, POST create (optionally with full nested sections)
    /hr/policies/{id}/     GET full tree, PATCH/PUT update, DELETE
    """
    permission_classes = PERMISSIONS
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['title', 'policy_code', 'description']
    ordering_fields = ['created_at', 'updated_at', 'effective_date', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.action == 'list':
            return HRPolicy.objects.select_related('created_by').annotate(
                sections_count=Count('sections', distinct=True)
            )
        return _policy_tree_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return HRPolicyListSerializer
        if self.action == 'create':
            return HRPolicyCreateSerializer
        if self.action in ('update', 'partial_update'):
            return HRPolicyPatchSerializer
        return HRPolicyDetailSerializer

    def _detail_response(self, policy_id, http_status):
        policy = _policy_tree_queryset().get(pk=policy_id)
        return Response(
            HRPolicyDetailSerializer(policy, context=self.get_serializer_context()).data,
            status=http_status,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()
        return self._detail_response(policy.pk, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self._detail_response(instance.pk, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Granular sub-resource endpoints
# ---------------------------------------------------------------------------

class HRPolicySectionCreateView(generics.CreateAPIView):
    """POST /hr/policies/{policy_id}/sections/  -> add a section to a policy."""
    permission_classes = PERMISSIONS
    serializer_class = HRPolicySectionWriteSerializer

    def perform_create(self, serializer):
        policy = get_object_or_404(HRPolicy, pk=self.kwargs['policy_id'])
        serializer.save(policy=policy)


class HRPolicySectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /hr/policies/sections/{pk}/"""
    permission_classes = PERMISSIONS
    queryset = HRPolicySection.objects.prefetch_related('direct_points', 'subtitles__points')
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return HRPolicySectionSerializer
        return HRPolicySectionWriteSerializer


class HRPolicySubtitleCreateView(generics.CreateAPIView):
    """POST /hr/policies/sections/{section_id}/subtitles/"""
    permission_classes = PERMISSIONS
    serializer_class = HRPolicySubtitleWriteSerializer

    def perform_create(self, serializer):
        section = get_object_or_404(HRPolicySection, pk=self.kwargs['section_id'])
        serializer.save(section=section)


class HRPolicySubtitleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /hr/policies/subtitles/{pk}/"""
    permission_classes = PERMISSIONS
    queryset = HRPolicySubtitle.objects.prefetch_related('points')
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return HRPolicySubtitleSerializer
        return HRPolicySubtitleWriteSerializer


class HRPolicySectionPointCreateView(generics.CreateAPIView):
    """POST /hr/policies/sections/{section_id}/points/  -> direct point (no subtitle)."""
    permission_classes = PERMISSIONS
    serializer_class = HRPolicyPointWriteSerializer

    def perform_create(self, serializer):
        section = get_object_or_404(HRPolicySection, pk=self.kwargs['section_id'])
        serializer.save(section=section, subtitle=None)


class HRPolicySubtitlePointCreateView(generics.CreateAPIView):
    """POST /hr/policies/subtitles/{subtitle_id}/points/"""
    permission_classes = PERMISSIONS
    serializer_class = HRPolicyPointWriteSerializer

    def perform_create(self, serializer):
        subtitle = get_object_or_404(HRPolicySubtitle, pk=self.kwargs['subtitle_id'])
        serializer.save(subtitle=subtitle, section=None)


class HRPolicyPointDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /hr/policies/points/{pk}/"""
    permission_classes = PERMISSIONS
    queryset = HRPolicyPoint.objects.all()
    serializer_class = HRPolicyPointWriteSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
