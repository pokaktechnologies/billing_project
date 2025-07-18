from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone

from .models import Enquiry
from .serializers import EnquirySerializer, EnquiryStatusUpdateSerializer


class EnquiryCreateView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        elif self.request.method == 'POST':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get(self, request):
        enquiries = Enquiry.objects.all()
        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def post(self, request):
        serializer = EnquirySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EnquiryDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get_object(self, pk):
        try:
            return Enquiry.objects.get(pk=pk)
        except Enquiry.DoesNotExist:
            return None

    def get(self, request, pk):
        enquiry = self.get_object(pk)
        if enquiry is None:
            return Response({'error': 'Enquiry not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EnquirySerializer(enquiry)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EnquiryStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            return Enquiry.objects.get(pk=pk)
        except Enquiry.DoesNotExist:
            return None

    def patch(self, request, pk):
        enquiry = self.get_object(pk)
        if enquiry is None:
            return Response({'error': 'Enquiry not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EnquiryStatusUpdateSerializer(enquiry, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class EnquiryStatisticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        total_enquiries_today = Enquiry.objects.filter(created_at__date=today).count()
        # percntage total enquiries from yesterday
        yesterday = today - timezone.timedelta(days=1)
        total_enquiries_yesterday = Enquiry.objects.filter(created_at__date=yesterday).count()
        if total_enquiries_yesterday > 0:
            percentage_change = ((total_enquiries_today - total_enquiries_yesterday) / total_enquiries_yesterday) * 100
        else:
            percentage_change = 0
        unread_enquiries = Enquiry.objects.filter(status='new').count()
        reviewed_enquiries = Enquiry.objects.filter(status='reviewed').count()
        responsed_enquiries = Enquiry.objects.filter(status='responded').count()

        statistics = {
            'total_enquiries': {
                'today': total_enquiries_today,
                'yesterday': total_enquiries_yesterday,
                'percentage_change': percentage_change
            }
            ,
            'unread_enquiries': unread_enquiries,
            'reviewed_enquiries': reviewed_enquiries,
            'responsed_enquiries': responsed_enquiries
        }

        return Response(statistics, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status as drf_status
from django.db.models import Q

from .models import Enquiry
from .serializers import EnquirySerializer


class SearchEnquiryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client_name = request.query_params.get('client_name', '')
        email = request.query_params.get('email', '')
        phone = request.query_params.get('phone', '')
        status_filter = request.query_params.get('status', '')
        sort = request.query_params.get('sort', '-created_at')  # default: latest first

        # Start building the query
        query = Q()

        if client_name:
            query &= Q(first_name__icontains=client_name) | Q(last_name__icontains=client_name)
        if email:
            query &= Q(email__icontains=email)
        if phone:
            query &= Q(phone__icontains=phone)
        if status_filter:
            query &= Q(status__iexact=status_filter)

        # Apply filtering and sorting
        enquiries = Enquiry.objects.filter(query).order_by(sort)

        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data, status=drf_status.HTTP_200_OK)


