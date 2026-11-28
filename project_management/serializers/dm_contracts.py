from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import Customer, CustomUser
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


def generate_next_contract_number(prefix="DMC", length=6):
    """
    Generates the next sequential contract number in the project's standard format (e.g., DMC|100001).
    """
    start = 10 ** (length - 1) + 1  # 100001
    latest = DMContract.objects.filter(contract_number__startswith=f"{prefix}|").order_by("-contract_number").first()
    if latest:
        try:
            num_part = latest.contract_number.split("|")[1]
            next_num = int(num_part) + 1
        except (IndexError, ValueError):
            next_num = start
    else:
        next_num = start
    return f"{prefix}|{next_num:0{length}d}"


# =============================================================================
# 1. PLATFORM & WORK TYPE MASTER SERIALIZERS
# =============================================================================

class DMPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMPlatform
        fields = ['id', 'name', 'is_active', 'created_at']

    def validate_name(self, value):
        name = value.strip()
        qs = DMPlatform.objects.filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Platform '{name}' already exists.")
        return name


class DMWorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMWorkType
        fields = ['id', 'name', 'is_active', 'created_at']

    def validate_name(self, value):
        name = value.strip()
        qs = DMWorkType.objects.filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Work type '{name}' already exists.")
        return name


# =============================================================================
# 2. NESTED CHILD SERIALIZERS
# =============================================================================

class DMContractPlatformSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='platform.name', read_only=True)

    class Meta:
        model = DMContractPlatform
        fields = ['id', 'platform', 'platform_name', 'created_at']


class DMContractWorkSerializer(serializers.ModelSerializer):
    work_type_name = serializers.CharField(source='work_type.name', read_only=True)

    class Meta:
        model = DMContractWork
        fields = ['id', 'work_type', 'work_type_name', 'quantity_type', 'quantity', 'created_at']

    def validate(self, attrs):
        quantity_type = attrs.get('quantity_type', getattr(self.instance, 'quantity_type', 'count'))
        quantity = attrs.get('quantity', getattr(self.instance, 'quantity', None))

        if quantity_type == 'count':
            if quantity is None or quantity <= 0:
                raise serializers.ValidationError({'quantity': "Quantity is required and must be greater than 0 when quantity_type is 'count'."})
        elif quantity_type == 'included':
            attrs['quantity'] = None

        return attrs


class DMContractLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMContractLink
        fields = ['id', 'url', 'display_order', 'created_at']


class DMContractAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DMContractAttachment
        fields = ['id', 'file', 'file_name', 'file_size', 'uploaded_at', 'download_url']

    def get_download_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class DMContractExtensionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DMContractExtension
        fields = [
            'id',
            'original_end_date',
            'previous_effective_end_date',
            'extended_until',
            'additional_days',
            'created_by',
            'created_by_name',
            'remarks',
            'created_at',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            first = getattr(obj.created_by, 'first_name', '')
            last = getattr(obj.created_by, 'last_name', '')
            full = f"{first} {last}".strip()
            return full or getattr(obj.created_by, 'email', str(obj.created_by.id))
        return None


class DMContractCreateExtensionSerializer(serializers.Serializer):
    """
    Validates payload for creating a new contract extension.
    Calculates additional_days on the backend strictly against current effective end date.
    """
    extended_until = serializers.DateField(required=True)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            mutable_data = data.copy()
            if 'reason' in mutable_data and 'remarks' not in mutable_data:
                mutable_data['remarks'] = mutable_data.pop('reason')
            return super().to_internal_value(mutable_data)
        return super().to_internal_value(data)

    def validate_extended_until(self, value):
        contract = self.context.get('contract')
        if not contract:
            return value

        current_effective = contract.revised_end_date
        if value <= current_effective:
            raise serializers.ValidationError(
                f"Extended date ({value}) must be strictly later than current effective end date ({current_effective})."
            )
        return value

    def create(self, validated_data):
        contract = self.context['contract']
        user = self.context['request'].user
        extended_until = validated_data['extended_until']
        remarks = validated_data.get('remarks', '')

        current_effective = contract.revised_end_date
        additional_days = (extended_until - current_effective).days

        extension = DMContractExtension.objects.create(
            contract=contract,
            original_end_date=contract.original_end_date,
            previous_effective_end_date=current_effective,
            extended_until=extended_until,
            additional_days=additional_days,
            created_by=user,
            remarks=remarks
        )
        return extension


# =============================================================================
# 3. CONTRACT LIST & DETAIL SERIALIZERS
# =============================================================================

class DMContractListSerializer(serializers.ModelSerializer):
    client_info = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    work_status_display = serializers.CharField(source='get_work_status_display', read_only=True)
    revised_end_date = serializers.DateField(read_only=True)
    total_duration = serializers.IntegerField(read_only=True)
    total_additional_days = serializers.IntegerField(read_only=True)
    platforms = serializers.SerializerMethodField()
    works_count = serializers.SerializerMethodField()
    links_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    extensions_count = serializers.SerializerMethodField()

    class Meta:
        model = DMContract
        fields = [
            'id',
            'contract_number',
            'contract_name',
            'client',
            'client_info',
            'user',
            'user_name',
            'contract_date',
            'work_status',
            'work_status_display',
            'start_date',
            'original_end_date',
            'revised_end_date',
            'duration',
            'total_duration',
            'total_additional_days',
            'platforms',
            'works_count',
            'links_count',
            'attachments_count',
            'extensions_count',
            'created_at',
        ]

    def get_client_info(self, obj):
        c = obj.client
        if not c:
            return None
        return {
            'id': c.id,
            'customer_number': c.customer_number,
            'customer_type': c.customer_type,
            'name': c.get_full_name(),
            'company_name': c.company_name,
            'email': c.email,
            'phone': c.phone or c.mobile,
        }

    def get_user_name(self, obj):
        if obj.user:
            full = f"{getattr(obj.user, 'first_name', '')} {getattr(obj.user, 'last_name', '')}".strip()
            return full or getattr(obj.user, 'email', str(obj.user.id))
        return None

    def get_platforms(self, obj):
        return [cp.platform.name for cp in obj.contract_platforms.all()]

    def get_works_count(self, obj):
        return obj.contract_works.count()

    def get_links_count(self, obj):
        return obj.contract_links.count()

    def get_attachments_count(self, obj):
        return obj.contract_attachments.count()

    def get_extensions_count(self, obj):
        return obj.extensions.count()


class DMContractDetailSerializer(serializers.ModelSerializer):
    client_info = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()
    work_status_display = serializers.CharField(source='get_work_status_display', read_only=True)
    revised_end_date = serializers.DateField(read_only=True)
    total_duration = serializers.IntegerField(read_only=True)
    total_additional_days = serializers.IntegerField(read_only=True)

    platforms = DMContractPlatformSerializer(source='contract_platforms', many=True, read_only=True)
    works = DMContractWorkSerializer(source='contract_works', many=True, read_only=True)
    links = DMContractLinkSerializer(source='contract_links', many=True, read_only=True)
    attachments = DMContractAttachmentSerializer(source='contract_attachments', many=True, read_only=True)
    extensions = DMContractExtensionSerializer(many=True, read_only=True)

    class Meta:
        model = DMContract
        fields = [
            'id',
            'contract_number',
            'contract_name',
            'client',
            'client_info',
            'user',
            'user_info',
            'contract_date',
            'description',
            'work_status',
            'work_status_display',
            'start_date',
            'original_end_date',
            'revised_end_date',
            'duration',
            'total_duration',
            'total_additional_days',
            'remarks',
            'platforms',
            'works',
            'links',
            'attachments',
            'extensions',
            'created_at',
            'updated_at',
        ]

    def get_client_info(self, obj):
        c = obj.client
        if not c:
            return None
        return {
            'id': c.id,
            'customer_number': c.customer_number,
            'customer_type': c.customer_type,
            'name': c.get_full_name(),
            'company_name': c.company_name,
            'first_name': c.first_name,
            'last_name': c.last_name,
            'email': c.email,
            'phone': c.phone,
            'mobile': c.mobile,
            'address': c.address,
            'gst_number': c.gst_number,
        }

    def get_user_info(self, obj):
        u = obj.user
        if not u:
            return None
        full_name = f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
        user_email = getattr(u, 'email', '')
        return {
            'id': u.id,
            'email': user_email,
            'name': full_name or user_email or str(u.id),
        }


# =============================================================================
# 4. NESTED CREATION & UPDATE SERIALIZER
# =============================================================================

class DMContractWorkInputSerializer(serializers.Serializer):
    work_type = serializers.PrimaryKeyRelatedField(queryset=DMWorkType.objects.all())
    quantity_type = serializers.ChoiceField(choices=DMContractWork.QUANTITY_TYPE_CHOICES, default='count')
    quantity = serializers.IntegerField(required=False, allow_null=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            mutable_data = data.copy()
            if 'work_type_id' in mutable_data and 'work_type' not in mutable_data:
                mutable_data['work_type'] = mutable_data.pop('work_type_id')
            return super().to_internal_value(mutable_data)
        return super().to_internal_value(data)

    def validate(self, attrs):
        qtype = attrs.get('quantity_type', 'count')
        qty = attrs.get('quantity')
        if qtype == 'count':
            if qty is None or qty <= 0:
                raise serializers.ValidationError({'quantity': "Quantity must be a positive integer when quantity_type is 'count'."})
        elif qtype == 'included':
            attrs['quantity'] = None
        return attrs


class DMContractLinkInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    url = serializers.URLField(max_length=500)
    display_order = serializers.IntegerField(default=0, required=False)


class DMContractCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Accepts full contract creation and partial update payloads with nested:
      - platforms: [1, 2, 3] or platform_ids: [1, 2, 3]
      - works: [{'work_type': 1, 'quantity_type': 'count', 'quantity': 20}, ...]
      - links: [{'url': 'https://...', 'label': '...', 'display_order': 1}, ...]
      - attachments: file list from request.FILES
    """
    client = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    contract_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    end_date = serializers.DateField(write_only=True, required=False, help_text="Maps to original_end_date on creation")
    original_end_date = serializers.DateField(required=False)

    platforms = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of DMPlatform IDs"
    )
    works = DMContractWorkInputSerializer(many=True, required=False, write_only=True)
    links = DMContractLinkInputSerializer(many=True, required=False, write_only=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            mutable_data = data.copy()
            if 'client_id' in mutable_data and 'client' not in mutable_data:
                mutable_data['client'] = mutable_data.pop('client_id')
            if 'platform_ids' in mutable_data and 'platforms' not in mutable_data:
                mutable_data['platforms'] = mutable_data.pop('platform_ids')
            if 'end_date' in mutable_data and 'original_end_date' not in mutable_data:
                mutable_data['original_end_date'] = mutable_data['end_date']
            return super().to_internal_value(mutable_data)
        return super().to_internal_value(data)

    class Meta:
        model = DMContract
        fields = [
            'id',
            'contract_number',
            'client',
            'contract_name',
            'contract_date',
            'description',
            'work_status',
            'start_date',
            'end_date',
            'original_end_date',
            'remarks',
            'platforms',
            'works',
            'links',
        ]

    def validate_client(self, customer):
        if customer.module_type != 'client':
            raise serializers.ValidationError(
                f"Selected customer '{customer.get_full_name()}' (ID {customer.id}) is a lead. "
                "Only converted clients (module_type='client') are permitted for Digital Marketing Contracts."
            )
        return customer

    def validate(self, attrs):
        start_date = attrs.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = attrs.get('end_date') or attrs.get('original_end_date') or (self.instance.original_end_date if self.instance else None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': "End date cannot be earlier than start date."})

        # Check duplicate platforms in payload
        platforms = attrs.get('platforms')
        if platforms:
            if len(platforms) != len(set(platforms)):
                raise serializers.ValidationError({'platforms': "Duplicate platforms detected in submission."})

        # Check duplicate work_types in payload
        works = attrs.get('works')
        if works:
            wt_ids = [w['work_type'].id for w in works]
            if len(wt_ids) != len(set(wt_ids)):
                raise serializers.ValidationError({'works': "Duplicate work types detected. Each deliverable work type must be unique within a contract."})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        platforms_data = validated_data.pop('platforms', [])
        works_data = validated_data.pop('works', [])
        links_data = validated_data.pop('links', [])

        # Map end_date to original_end_date
        end_date = validated_data.pop('end_date', None)
        if end_date and 'original_end_date' not in validated_data:
            validated_data['original_end_date'] = end_date

        # Auto-generate contract number if not provided
        contract_number = validated_data.get('contract_number')
        if not contract_number or not contract_number.strip():
            validated_data['contract_number'] = generate_next_contract_number()

        # Set user from request
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user

        # Create main contract
        contract = DMContract.objects.create(**validated_data)

        # 1. Create platforms
        if platforms_data:
            platform_objects = DMPlatform.objects.filter(id__in=platforms_data)
            DMContractPlatform.objects.bulk_create([
                DMContractPlatform(contract=contract, platform=p) for p in platform_objects
            ])

        # 2. Create works
        if works_data:
            DMContractWork.objects.bulk_create([
                DMContractWork(
                    contract=contract,
                    work_type=w['work_type'],
                    quantity_type=w.get('quantity_type', 'count'),
                    quantity=w.get('quantity') if w.get('quantity_type', 'count') == 'count' else None
                )
                for w in works_data
            ])

        # 3. Create links
        if links_data:
            DMContractLink.objects.bulk_create([
                DMContractLink(
                    contract=contract,
                    url=l['url'],
                    display_order=l.get('display_order', idx)
                )
                for idx, l in enumerate(links_data, start=1)
            ])

        # 4. Handle attachments from request.FILES
        if request and request.FILES:
            files = request.FILES.getlist('attachments')
            for f in files:
                DMContractAttachment.objects.create(contract=contract, file=f)

        return contract

    @transaction.atomic
    def update(self, instance, validated_data):
        platforms_data = validated_data.pop('platforms', None)
        works_data = validated_data.pop('works', None)
        links_data = validated_data.pop('links', None)

        end_date = validated_data.pop('end_date', None)
        if end_date:
            validated_data['original_end_date'] = end_date

        # Update scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace platforms if explicitly passed
        if platforms_data is not None:
            instance.contract_platforms.all().delete()
            platform_objects = DMPlatform.objects.filter(id__in=platforms_data)
            DMContractPlatform.objects.bulk_create([
                DMContractPlatform(contract=instance, platform=p) for p in platform_objects
            ])

        # Replace works if explicitly passed
        if works_data is not None:
            instance.contract_works.all().delete()
            DMContractWork.objects.bulk_create([
                DMContractWork(
                    contract=instance,
                    work_type=w['work_type'],
                    quantity_type=w.get('quantity_type', 'count'),
                    quantity=w.get('quantity') if w.get('quantity_type', 'count') == 'count' else None
                )
                for w in works_data
            ])

        # Replace links if explicitly passed
        if links_data is not None:
            instance.contract_links.all().delete()
            DMContractLink.objects.bulk_create([
                DMContractLink(
                    contract=instance,
                    url=l['url'],
                    display_order=l.get('display_order', idx)
                )
                for idx, l in enumerate(links_data, start=1)
            ])

        # Attach any new files passed in update
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('attachments')
            for f in files:
                DMContractAttachment.objects.create(contract=instance, file=f)

        return instance
