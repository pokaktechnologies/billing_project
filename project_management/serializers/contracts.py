from rest_framework import serializers
from ..models import ClientContract


class ClientContractSerializer(serializers.ModelSerializer):
    client_first_name = serializers.CharField(source='client.first_name', read_only=True)
    client_last_name = serializers.CharField(source='client.last_name', read_only=True)

    class Meta:
        model = ClientContract
        fields = [
            'id',
            'client',
            'client_first_name',
            'client_last_name',
            'contract_number',
            'contract_type',
            'contract_name',
            'description',
            'contract_date',
            'start_date',
            'end_date',
            'duration',         # duration in days
            'created_at',
            'updated_at',
        ]
