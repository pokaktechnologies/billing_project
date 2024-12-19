from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Quotation
from .serializers import QuotationSerializer
from .serializers import CustomUserCreateSerializer, OTPSerializer, GettingStartedSerializer
import random

class SignupView(APIView):
    """
    API view for user signup with first_name, last_name, and email. An OTP will be sent to the email.
    """
    def post(self, request):
        serializer = CustomUserCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()

            # Generate a 6-digit OTP
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.save()

            # For demonstration, print the OTP to the console (replace with actual email sending)
            print(f"OTP for {user.email}: {otp}")  # In production, send OTP via email

            return Response({'message': 'User created successfully. OTP sent to email.'}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPVerificationView(APIView):
    """
    API view for OTP verification. After OTP is verified, user can proceed with further steps.
    """
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            # Find user by email
            user = CustomUser.objects.filter(email=email).first()

            if user and user.otp == otp:
                user.is_otp_verified = True
                user.save()
                return Response({'message': 'OTP verified successfully! Proceed to next step.'}, status=status.HTTP_200_OK)
            
            return Response({'error': 'Invalid OTP or email.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GettingStartedView(APIView):
    """
    API view for capturing organization details after OTP verification.
    """
    permission_classes = [AllowAny]  # This allows unrestricted access to this view.
  # Require JWT authentication

    def post(self, request):
        print('first request')
        # Validate and deserialize the input data
        # serializer = GettingStartedSerializer(data=request.data)
        email = request.data.get('email', None)
        organization_name= request.data.get('organization_name', None)
        business_location= request.data.get('business_location', None)
        state_province= request.data.get('business_location', None)
        print('validating seri')

        
        print("bachi")
                # Get the email from the validated data
                # Find the user by email who has verified OTP        
        # Find the user by email who has verified OTP
        user = CustomUser.objects.filter(email=email, is_otp_verified=True).first()
        print("fgfgft",user)
        if user:
                print("sugamano")
                # Update the user with organization details
                user.organization_name= organization_name
                user.business_location = business_location
                user.state_province = state_province
                user.save()

                return Response(
                    {'message': 'Organization details saved successfully!'},
                    status=status.HTTP_200_OK
                )
            
        return Response(
                {'error': 'User not found or OTP not verified.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # If serializer is invalid, return error responses
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class QuotationViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing, creating, and managing quotations.
    """
    queryset = Quotation.objects.all()
    serializer_class = QuotationSerializer

    # Add filtering and searching
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer_name', 'salesperson', 'invoice_date']
    search_fields = ['customer_name', 'invoice_number', 'order_number']
    ordering_fields = ['invoice_date', 'due_date']
    ordering = ['invoice_date']  # Default ordering

    def create(self, request, *args, **kwargs):
        """
        Override create to handle custom logic if needed.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """
        Custom action to mark a quotation as paid.
        """
        quotation = self.get_object()
        quotation.status = "Paid"  # Assuming 'status' is a field in the model
        quotation.save()
        return Response({"message": "Quotation marked as Paid!"}, status=status.HTTP_200_OK)