from rest_framework.serializers import ModelSerializer
from .models import Enquiry

class EnquirySerializer(ModelSerializer):
    class Meta:
        model = Enquiry
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
        


class EnquiryStatusUpdateSerializer(ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ['status']
