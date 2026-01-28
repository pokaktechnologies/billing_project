from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import CashflowCategoryMapping, TaxSettings
from ..serializers.settings import CashflowCategoryMappingSerializer, TaxSettingsSerializer
from ..services.numbering import get_next_finance_number

class CashflowCategoryMappingListCreateView(generics.ListCreateAPIView):
    serializer_class = CashflowCategoryMappingSerializer
    def get_queryset(self):
        queryset = CashflowCategoryMapping.objects.all()
        category = self.request.query_params.get('category')
        sub_category = self.request.query_params.get('sub_category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        if sub_category:
            queryset = queryset.filter(sub_category__icontains=sub_category)
        return queryset

class CashflowCategoryMappingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CashflowCategoryMapping.objects.all()
    serializer_class = CashflowCategoryMappingSerializer

class FinaceNumberGeneratorView(APIView):
    def get(self, request):
        model_type = request.query_params.get('type')
        number = get_next_finance_number(model_type)
        if number is None:
            return Response({'status': '0', 'message': 'Invalid order type'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': '1', 'message': 'Success', 'number': number}, status=status.HTTP_200_OK)

class TaxSettingsListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaxSettingsSerializer
    def get_queryset(self):
        queryset = TaxSettings.objects.all()
        name = self.request.query_params.get('name')
        is_active = self.request.query_params.get('is_active')
        rate_min = self.request.query_params.get('rate_min')
        rate_max = self.request.query_params.get('rate_max')
        if name: queryset = queryset.filter(name__icontains=name)
        if is_active is not None: queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if rate_min: queryset = queryset.filter(rate__gte=rate_min)
        if rate_max: queryset = queryset.filter(rate__lte=rate_max)
        return queryset

class TaxSettingsRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TaxSettings.objects.all()
    serializer_class = TaxSettingsSerializer
