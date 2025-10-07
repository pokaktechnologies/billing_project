from rest_framework import serializers
from .models import *
from django.utils import timezone
from django.db import transaction
from .utils import generate_next_number

from rest_framework import serializers
from .models import Account

class AccountSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Account
        fields = '__all__'

class JournalLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_type = serializers.CharField(source='account.type', read_only=True)
    class Meta:
        model = JournalLine
        fields = ['id', 'account', 'account_name', 'account_type', 'debit', 'credit', 'created_at']
        read_only_fields = ['id', 'created_at']
    def validate(self, data):
        debit = data.get('debit', 0)
        credit = data.get('credit', 0)
        if debit > 0 and credit > 0:
            raise serializers.ValidationError("A line cannot have both debit and credit.")
        if debit == 0 and credit == 0:
            raise serializers.ValidationError("Either debit or credit must be greater than zero.")
        return data

class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)
    salesperson_full_name = serializers.SerializerMethodField(read_only=True)
    total_debit = serializers.SerializerMethodField(read_only=True)
    total_credit = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            'id',
            'user',
            'salesperson',
            'salesperson_full_name',
            'type_number',
            'type',
            'date',
            'narration',
            'lines',
            'total_debit',
            'total_credit',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_salesperson_full_name(self, obj):
        if obj.salesperson:
            return f"{obj.salesperson.first_name} {obj.salesperson.last_name or ''}".strip()
        return None
    def get_total_debit(self, obj):
        return obj.total_debit()

    def get_total_credit(self, obj):
        return obj.total_credit()
    def validate(self, data):
        lines = data.get('lines', [])
        total_debit = sum([float(l['debit']) for l in lines])
        total_credit = sum([float(l['credit']) for l in lines])
        if round(total_debit, 2) != round(total_credit, 2):
            raise serializers.ValidationError(
                f"Journal entry is not balanced: Debit {total_debit} ≠ Credit {total_credit}"
            )
        return data

    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        user = self.context['request'].user
        validated_data['user'] = user
        journal_entry = JournalEntry.objects.create(**validated_data)
        for line in lines_data:
            JournalLine.objects.create(journal=journal_entry, **line)
        return journal_entry

    # ----- Update Method -----
    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)

        # Update top-level JournalEntry fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If lines are provided, update them
        if lines_data is not None:
            # Remove old lines
            instance.lines.all().delete()

            # Create new ones
            for line_data in lines_data:
                JournalLine.objects.create(journal=instance, **line_data)

        return instance

class JournalLineListSerializer(serializers.ModelSerializer):
    voucher_type = serializers.CharField(source='journal.type', read_only=True)
    date = serializers.CharField(source='journal.date', read_only=True)
    voucher_number = serializers.CharField(source='journal.type_number', read_only=True)
    narration = serializers.CharField(source='journal.narration', read_only=True)
    account = serializers.CharField(source='account.name', read_only=True)
    account_type = serializers.CharField(source='account.type', read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    salesperson_name = serializers.SerializerMethodField()

    class Meta:
        model = JournalLine
        fields = '__all__'

    def get_salesperson_name(self, obj):
        sp = obj.journal.salesperson
        if sp:
            return f"{sp.first_name} {sp.last_name or ''}".strip()
        return None




from rest_framework import serializers
from .models import JournalLine

class JournalLineDetailSerializer(serializers.ModelSerializer):
    voucher_type = serializers.CharField(source='journal.type', read_only=True)
    date = serializers.CharField(source='journal.date', read_only=True)
    voucher_number = serializers.CharField(source='journal.type_number', read_only=True)
    narration = serializers.CharField(source='journal.narration', read_only=True)
    account = serializers.CharField(source='account.name', read_only=True)
    account_type = serializers.CharField(source='account.type', read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    salesperson_name = serializers.SerializerMethodField()
    class Meta:
        model = JournalLine
        fields = "__all__"
    def get_salesperson_name(self, obj):
        sp = obj.journal.salesperson
        if sp:
            return f"{sp.first_name} {sp.last_name or ''}".strip()
        return None