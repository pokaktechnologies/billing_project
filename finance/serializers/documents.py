from rest_framework import serializers
from ..models import CreditNote, CreditNoteItem, DebitNote, DebitNoteItem

class CreditNoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = CreditNoteItem
        fields = [
            "id", "product", "quantity", "unit_price",
            "cgst_rate", "sgst_rate", "total", "cgst_amount", "sgst_amount", "sub_total", "product_name"
        ]
        read_only_fields = ["total", "cgst_amount", "sgst_amount", "sub_total"]

class CreditNoteSerializer(serializers.ModelSerializer):
    items = CreditNoteItemSerializer(many=True)
    client_name = serializers.SerializerMethodField(read_only=True)
    salesperson_name = serializers.SerializerMethodField(read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = CreditNote
        fields = [
            "id", "user", "client", "invoice", "credit_note_number", "salesperson",
            "date","due_date" ,"remarks", "document", "total_amount", "cgst_total",
            "sgst_total", "grand_total", "items", "journal_entry","client_name", "salesperson_name", "invoice_number"
        ]
        read_only_fields = ["total_amount", "cgst_total", "sgst_total", "grand_total", "journal_entry","client_name"]

    def create(self, validated_data):
        from ..services.documents import process_credit_note_creation
        user = self.context['request'].user
        return process_credit_note_creation(validated_data, user)

    def update(self, instance, validated_data):
        from ..services.documents import process_credit_note_update
        return process_credit_note_update(instance, validated_data)

    def get_salesperson_name(self, obj):
        sp = obj.salesperson
        if sp:
            return f"{sp.first_name} {sp.last_name or ''}".strip()
        return None

    def get_client_name(self, obj):
        client = obj.client
        if client:
            return f"{client.first_name} {client.last_name or ''}".strip()
        return None

class DebitNoteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebitNoteItem
        fields = [
            "id", "product", "quantity", "unit_price",
            "cgst_rate", "sgst_rate", "total",
            "cgst_amount", "sgst_amount", "sub_total"
        ]
        read_only_fields = ["total", "cgst_amount", "sgst_amount", "sub_total"]

class DebitNoteSerializer(serializers.ModelSerializer):
    items = DebitNoteItemSerializer(many=True)
    supplier_name = serializers.SerializerMethodField(read_only=True)
    salesperson_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DebitNote
        fields = [
            "id", "user", "supplier", "invoice", "debit_note_number",
            "date", "due_date", "remarks", "document",
            "total_amount", "cgst_total", "sgst_total", "grand_total",
            "items", "journal_entry", "supplier_name" , "salesperson", "salesperson_name"
        ]
        read_only_fields = [
            "total_amount", "cgst_total", "sgst_total", "grand_total", "journal_entry", "supplier_name"
        ]

    def create(self, validated_data):
        from ..services.documents import process_debit_note_creation
        user = self.context['request'].user
        return process_debit_note_creation(validated_data, user)

    def update(self, instance, validated_data):
        from ..services.documents import process_debit_note_update
        return process_debit_note_update(instance, validated_data)

    def get_salesperson_name(self, obj):
        sp = obj.salesperson
        if sp:
            return f"{sp.first_name} {sp.last_name or ''}".strip()
        return None

    def get_supplier_name(self, obj):
        supplier = obj.supplier
        if supplier:
            return getattr(supplier, "name", str(supplier))
        return None
