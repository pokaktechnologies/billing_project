from rest_framework import serializers
from .models import *
from django.utils import timezone
from django.db import transaction
from .utils import generate_next_number

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

from rest_framework import serializers
from .models import JournalEntry, JournalLine

class JournalLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalLine
        fields = ['id', 'account', 'debit', 'credit', 'description']

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

        lines = [
            JournalLine(journal=journal_entry, **line_data)
            for line_data in lines_data
        ]
        JournalLine.objects.bulk_create(lines)

        return journal_entry

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)

        # Update only changed fields
        for attr, value in validated_data.items():
            if getattr(instance, attr) != value:
                setattr(instance, attr, value)
        instance.save()

        # Update lines only if new data is provided
        if lines_data is not None:
            instance.lines.all().delete()
            lines = [
                JournalLine(journal=instance, **line_data)
                for line_data in lines_data
            ]
            JournalLine.objects.bulk_create(lines)

        return instance


class PaymentDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['created_at', 'journal_entry']

from rest_framework import serializers
from django.db import transaction
from .models import Payment, Supplier, Account, JournalEntry, JournalLine
from .utils import generate_next_number

class PaymentCreateSerializer(serializers.ModelSerializer):
    paid_to = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    paid_from_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    paid_to_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['created_at', 'journal_entry']

    def create(self, validated_data):
        user = self.context['request'].user

        with transaction.atomic():
            validated_data['user'] = user
            if not validated_data.get('payment_number'):
                validated_data['payment_number'] = generate_next_number(Payment, 'payment_number', 'PAY', 6)

            # Create the Payment instance
            payment = Payment.objects.create(**validated_data)

            # Create related JournalEntry
            journal_entry = JournalEntry.objects.create(
                journal_number=generate_next_number(JournalEntry, 'journal_number', 'JE', 6),
                user=user,
                date=payment.date,
                description=f"Payment to {payment.paid_to.supplier_number if payment.paid_to else 'Unknown'}",
                reference=payment.payment_number,
            )

            # Create journal lines
            self._create_journal_lines(payment, journal_entry)

            # Link journal entry to payment
            payment.journal_entry = journal_entry
            payment.save()

            return payment

    def update(self, instance, validated_data):
        with transaction.atomic():
            # Update only changed fields
            for attr, value in validated_data.items():
                if getattr(instance, attr) != value:
                    setattr(instance, attr, value)
            instance.save()

            # Update linked journal entry if exists
            journal_entry = instance.journal_entry
            if journal_entry:
                journal_entry.date = instance.date
                journal_entry.description = f"Payment to {instance.paid_to.supplier_number if instance.paid_to else 'Unknown'}"
                journal_entry.reference = instance.payment_number
                journal_entry.save()

                # Delete old lines only if exist
                if journal_entry.lines.exists():
                    journal_entry.lines.all().delete()

                # Recreate journal lines
                self._create_journal_lines(instance, journal_entry)

            return instance

    def _create_journal_lines(self, payment, journal_entry):
        lines = [
            JournalLine(
                journal=journal_entry,
                account=payment.paid_to_account,
                debit=payment.amount,
                credit=0,
                description=f"Payment for {payment.remark or payment.paid_to_account.name}"
            ),
            JournalLine(
                journal=journal_entry,
                account=payment.paid_from_account,
                debit=0,
                credit=payment.amount,
                description=f"Paid via {payment.payment_method.upper()} from {payment.paid_from_account.name}"
            )
        ]

        # Optimized batch DB write
        JournalLine.objects.bulk_create(lines)

