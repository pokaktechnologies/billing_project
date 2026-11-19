from rest_framework.serializers import ModelSerializer
from ..models import Enquiry, ErpEnquiry


class EnquirySerializer(ModelSerializer):
    class Meta:
        model = Enquiry
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class EnquiryStatusUpdateSerializer(ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ['status']


class ErpEnquirySerializer(ModelSerializer):
    class Meta:
        model = ErpEnquiry
        fields = '__all__'
        read_only_fields = ['status', 'created_at', 'updated_at']


class ErpEnquiryStatusUpdateSerializer(ModelSerializer):
    class Meta:
        model = ErpEnquiry
        fields = ['status']

