from datetime import datetime
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from activity_logs.base_view import BaseAPIView
from ..models.dm_contracts import (
    DMPlatform,
    DMWorkType,
    DMContract,
    DMContractPlatform,
    DMContractWork,
    DMContractLink,
    DMContractAttachment,
    DMContractExtension,
)
from ..serializers.dm_contracts import (
    DMPlatformSerializer,
    DMWorkTypeSerializer,
    DMContractListSerializer,
    DMContractDetailSerializer,
    DMContractCreateUpdateSerializer,
    DMContractExtensionSerializer,
    DMContractCreateExtensionSerializer,
    DMContractAttachmentSerializer,
)
from .pagination import ReportPagination, Pagination


DEFAULT_PLATFORMS = [
    "Instagram",
    "Facebook",
    "Google",
    "Snapchat",
    "YouTube",
    "LinkedIn",
    "Twitter",
    "Pinterest",
    "Threads",
    "WhatsApp",
]

DEFAULT_WORK_TYPES = [
    "Poster",
    "Reel",
    "Campaign",
    "Video",
    "SEO",
    "Blog Writing",
    "Website Management",
    "Ads Management",
    "Thumbnail",
]


def seed_default_masters():
    """Seeds default DM platforms and work types if tables are empty."""
    if not DMPlatform.objects.exists():
        DMPlatform.objects.bulk_create([
            DMPlatform(name=p) for p in DEFAULT_PLATFORMS
        ], ignore_conflicts=True)

    if not DMWorkType.objects.exists():
        DMWorkType.objects.bulk_create([
            DMWorkType(name=w) for w in DEFAULT_WORK_TYPES
        ], ignore_conflicts=True)


# =============================================================================
# 1. DM CONTRACT LIST & CREATE VIEW
# =============================================================================

class DMContractListCreateAPIView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, format=None):
        contracts = DMContract.objects.select_related(
            'client', 'user'
        ).prefetch_related(
            'contract_platforms__platform',
            'contract_works__work_type',
            'contract_links',
            'contract_attachments',
            'extensions'
        ).order_by('-created_at')

        # 1. Filter by Client
        client_id = request.query_params.get('client')
        if client_id and client_id.isdigit():
            contracts = contracts.filter(client_id=int(client_id))

        # 2. Filter by Work Status
        work_status = request.query_params.get('work_status')
        if work_status:
            contracts = contracts.filter(work_status=work_status.strip().lower())

        # 3. Filter by Platform
        platform_id = request.query_params.get('platform')
        if platform_id and platform_id.isdigit():
            contracts = contracts.filter(contract_platforms__platform_id=int(platform_id))

        # 4. Filter by Start Date Range
        start_date_from = request.query_params.get('start_date_from')
        start_date_to = request.query_params.get('start_date_to')
        if start_date_from:
            try:
                df = datetime.strptime(start_date_from, "%Y-%m-%d").date()
                contracts = contracts.filter(start_date__gte=df)
            except ValueError:
                pass
        if start_date_to:
            try:
                dt = datetime.strptime(start_date_to, "%Y-%m-%d").date()
                contracts = contracts.filter(start_date__lte=dt)
            except ValueError:
                pass

        # 5. Filter by End Date Range
        end_date_from = request.query_params.get('end_date_from')
        end_date_to = request.query_params.get('end_date_to')
        if end_date_from:
            try:
                df = datetime.strptime(end_date_from, "%Y-%m-%d").date()
                contracts = contracts.filter(original_end_date__gte=df)
            except ValueError:
                pass
        if end_date_to:
            try:
                dt = datetime.strptime(end_date_to, "%Y-%m-%d").date()
                contracts = contracts.filter(original_end_date__lte=dt)
            except ValueError:
                pass

        # 6. Search across Contract Number, Name, Client Name, and Company Name
        search = request.query_params.get('search')
        if search:
            search = search.strip()
            contracts = contracts.filter(
                Q(contract_number__icontains=search) |
                Q(contract_name__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__company_name__icontains=search) |
                Q(client__customer_number__icontains=search)
            )

        contracts = contracts.distinct()

        # Optional pagination
        if request.query_params.get('page') or request.query_params.get('page_size'):
            paginator = ReportPagination()
            page = paginator.paginate_queryset(contracts, request)
            if page is not None:
                serializer = DMContractListSerializer(page, many=True)
                return paginator.get_paginated_response({
                    "status": "1",
                    "message": "success",
                    "data": serializer.data
                })

        serializer = DMContractListSerializer(contracts, many=True)
        return Response(
            {"status": "1", "message": "success", "count": contracts.count(), "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = DMContractCreateUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            contract = serializer.save()
            detail_serializer = DMContractDetailSerializer(contract)
            return Response(
                {
                    "status": "1",
                    "message": "Digital Marketing Contract created successfully",
                    "data": detail_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "status": "0",
                "message": "Contract creation failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


# =============================================================================
# 2. DM CONTRACT DETAIL VIEW (GET, PATCH, DELETE)
# =============================================================================

class DMContractDetailAPIView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_contract(self, pk):
        try:
            return DMContract.objects.select_related(
                'client', 'user'
            ).prefetch_related(
                'contract_platforms__platform',
                'contract_works__work_type',
                'contract_links',
                'contract_attachments',
                'extensions__created_by'
            ).get(pk=pk)
        except DMContract.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        contract = self.get_contract(pk)
        if not contract:
            return Response(
                {"status": "0", "message": "Digital Marketing Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DMContractDetailSerializer(contract)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        contract = self.get_contract(pk)
        if not contract:
            return Response(
                {"status": "0", "message": "Digital Marketing Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DMContractCreateUpdateSerializer(
            contract,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            updated_contract = serializer.save()
            detail_serializer = DMContractDetailSerializer(updated_contract)
            return Response(
                {
                    "status": "1",
                    "message": "Digital Marketing Contract updated successfully",
                    "data": detail_serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "status": "0",
                "message": "Contract update failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        contract = self.get_contract(pk)
        if not contract:
            return Response(
                {"status": "0", "message": "Digital Marketing Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Clean up attachment files from disk
        for attachment in contract.contract_attachments.all():
            if attachment.file:
                attachment.file.delete(save=False)

        contract.delete()
        return Response(
            {"status": "1", "message": "Digital Marketing Contract deleted successfully"},
            status=status.HTTP_200_OK
        )


# =============================================================================
# 3. PLATFORMS MASTER API (LIST & CREATE)
# =============================================================================

class DMPlatformListCreateAPIView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        seed_default_masters()
        is_active = request.query_params.get('is_active')
        queryset = DMPlatform.objects.all().order_by('name')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        serializer = DMPlatformSerializer(queryset, many=True)
        return Response(
            {"status": "1", "message": "success", "count": queryset.count(), "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = DMPlatformSerializer(data=request.data)
        if serializer.is_valid():
            platform = serializer.save()
            return Response(
                {
                    "status": "1",
                    "message": "Platform created successfully",
                    "data": DMPlatformSerializer(platform).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Platform creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# =============================================================================
# 4. WORK TYPES MASTER API (LIST & CREATE)
# =============================================================================

class DMWorkTypeListCreateAPIView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        seed_default_masters()
        is_active = request.query_params.get('is_active')
        queryset = DMWorkType.objects.all().order_by('name')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        serializer = DMWorkTypeSerializer(queryset, many=True)
        return Response(
            {"status": "1", "message": "success", "count": queryset.count(), "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = DMWorkTypeSerializer(data=request.data)
        if serializer.is_valid():
            work_type = serializer.save()
            return Response(
                {
                    "status": "1",
                    "message": "Work type created successfully",
                    "data": DMWorkTypeSerializer(work_type).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Work type creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# =============================================================================
# 5. CONTRACT EXTENSIONS API (LIST & CREATE)
# =============================================================================

class DMContractExtensionListCreateAPIView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_contract(self, pk):
        try:
            return DMContract.objects.get(pk=pk)
        except DMContract.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        contract = self.get_contract(pk)
        if not contract:
            return Response(
                {"status": "0", "message": "Digital Marketing Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        extensions = contract.extensions.select_related('created_by').order_by('-created_at')
        serializer = DMContractExtensionSerializer(extensions, many=True)
        return Response(
            {
                "status": "1",
                "message": "success",
                "contract_number": contract.contract_number,
                "original_end_date": contract.original_end_date,
                "revised_end_date": contract.revised_end_date,
                "total_additional_days": contract.total_additional_days,
                "total_duration": contract.total_duration,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request, pk, format=None):
        contract = self.get_contract(pk)
        if not contract:
            return Response(
                {"status": "0", "message": "Digital Marketing Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DMContractCreateExtensionSerializer(
            data=request.data,
            context={'contract': contract, 'request': request}
        )
        if serializer.is_valid():
            extension = serializer.save()
            ext_data = DMContractExtensionSerializer(extension).data
            return Response(
                {
                    "status": "1",
                    "message": "Contract extension recorded successfully",
                    "data": ext_data,
                    "extension": ext_data,
                    "updated_contract": {
                        "contract_number": contract.contract_number,
                        "original_end_date": contract.original_end_date,
                        "revised_end_date": contract.revised_end_date,
                        "total_additional_days": contract.total_additional_days,
                        "total_duration": contract.total_duration,
                    }
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "status": "0",
                "message": "Contract extension failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


# =============================================================================
# 6. ATTACHMENT UPLOAD & DELETE VIEWS
# =============================================================================

class DMContractAttachmentUploadView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk, format=None):
        try:
            contract = DMContract.objects.get(pk=pk)
        except DMContract.DoesNotExist:
            return Response(
                {"status": "0", "message": "Digital Marketing Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        files = request.FILES.getlist('attachments') or request.FILES.getlist('file')
        if not files:
            return Response(
                {"status": "0", "message": "No files were uploaded. Use key 'attachments' or 'file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_attachments = []
        for f in files:
            att = DMContractAttachment.objects.create(contract=contract, file=f)
            created_attachments.append(att)

        serializer = DMContractAttachmentSerializer(created_attachments, many=True)
        return Response(
            {
                "status": "1",
                "message": f"Successfully uploaded {len(created_attachments)} attachment(s)",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class DMContractAttachmentDeleteView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, format=None):
        try:
            attachment = DMContractAttachment.objects.get(pk=pk)
        except DMContractAttachment.DoesNotExist:
            return Response(
                {"status": "0", "message": "Attachment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()

        return Response(
            {"status": "1", "message": "Attachment deleted successfully"},
            status=status.HTTP_200_OK
        )
