from rest_framework import serializers
from .models import *


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ['user']

class JournalEntryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ['id', 'user', 'journal_number', 'date', 'description', 'reference']

class JournalLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalLine
        fields = ['id','account', 'debit', 'credit', 'description']
    
class JournalLineDisplaySerializer(serializers.ModelSerializer):
    account = AccountSerializer()
    class Meta:
        model = JournalLine
        fields = ['id','account', 'debit', 'credit', 'description']

class JournalEntryDisplaySerializer(serializers.ModelSerializer):
    lines = JournalLineDisplaySerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = [
            'id',
            'journal_number',
            'date',
            'description',
            'reference',
            'created_at',
            'user',
            'lines',
        ]

class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ['journal_number', 'date', 'description', 'reference', 'lines']

    def validate(self, data):
        lines = data.get('lines', [])
        if len(lines) < 2:
            raise serializers.ValidationError("At least two lines (one debit and one credit) are required.")

        total_debit = total_credit = 0
        has_debit = has_credit = False

        for line in lines:
            debit = float(line.get('debit', 0))
            credit = float(line.get('credit', 0))

            if debit > 0 and credit > 0:
                raise serializers.ValidationError("Each line can have either debit or credit, not both.")
            if debit == 0 and credit == 0:
                raise serializers.ValidationError("Each line must have a debit or credit amount.")

            total_debit += debit
            total_credit += credit
            has_debit |= debit > 0
            has_credit |= credit > 0

        if not has_debit or not has_credit:
            raise serializers.ValidationError("At least one debit and one credit line are required.")
        if round(total_debit, 2) != round(total_credit, 2):
            raise serializers.ValidationError(f"Journal not balanced: Debit ₹{total_debit} ≠ Credit ₹{total_credit}")

        return data

    def create(self, validated_data):
        request = self.context['request']
        lines_data = validated_data.pop('lines')

        journal_entry = JournalEntry.objects.create(
            user=request.user,
            **validated_data
        )

        for line_data in lines_data:
            JournalLine.objects.create(journal=journal_entry, **line_data)

        return journal_entry
    
    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)

        # Update journal entry fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If lines provided, delete old and create new
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                JournalLine.objects.create(journal=instance, **line_data)

        return instance