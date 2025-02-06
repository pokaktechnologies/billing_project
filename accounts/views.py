from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser, Feature
from django.db.models import Q
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Quotation,HelpLink, SalesPerson,Notification, UserSetting, Feedback,SalesOrder,QuotationOrderModel,InvoiceOrder,DeliveryOrder, SupplierPurchase,Supplier, DeliveryChallan,Product
from .serializers import QuotationSerializer, FeatureSerializer,ProductSerializer,SalesPersonSerializer
from rest_framework.authtoken.models import Token 
from .serializers import CustomUserCreateSerializer, OTPSerializer, GettingStartedSerializer,HelpLinkSerializer,NotificationSerializer, UserSettingSerializer, FeedbackSerializer,QuotationOrderSerializer,InvoiceOrderSerializer,DeliveryOrderSerializer,SupplierPurchaseSerializer,SupplierSerializer,DeliveryChallanSerializer
from django.core.mail import send_mail
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
            print(request.data.get('email'))
            email = request.data.get('email')
            # For demonstration, print the OTP to the console (replace with actual email sending)
            print(f"OTP for {user.email}: {otp}")  # In production, send OTP via email
           
            send_mail(
            subject="Password Reset OTP",
            message=f"Your OTP for password reset is {otp}. It is valid for 10 minutes.",
            from_email="Pokaktech1@gmail.com",
            recipient_list=[email],
            )
            
            
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
    
class HomePageView(APIView):
    def get(self, request):
        features = Feature.objects.all()
        serializer = FeatureSerializer(features, many=True)
        return Response({
            "user": {
                "name": "Alan",
                "profile_picture": "URL-to-profile-picture",
            },
            "features": serializer.data,
            "actions": {
                "get_started": "/get-started",
                "add_user": "/add-user",
            }
        })
    
# Help and Support
class HelpLinkView(APIView):
    def get(self, request):
        links = HelpLink.objects.all()
        serializer = HelpLinkSerializer(links, many=True)
        return Response(serializer.data)

# Notifications
class NotificationView(APIView):
    def get(self, request):
        notifications = Notification.objects.all()
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

# Settings
class UserSettingView(APIView):  
    def post(self, request):
        serializer = UserSettingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User setting created successfully.", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk=None):
        if pk:
            try:
                user_setting = UserSetting.objects.get(pk=pk)
                serializer = UserSettingSerializer(user_setting)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except UserSetting.DoesNotExist:
                return Response({"error": "User setting not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            user_settings = UserSetting.objects.all()
            serializer = UserSettingSerializer(user_settings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
      # PUT method for updating a user setting (replace the entire object)
    def put(self, request, pk):
        try:
            user_setting = UserSetting.objects.get(pk=pk)
        except UserSetting.DoesNotExist:
            return Response({"error": "User setting not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSettingSerializer(user_setting, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User setting updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # PATCH method for partial updates
    def patch(self, request, pk):
        try:
            user_setting = UserSetting.objects.get(pk=pk)
        except UserSetting.DoesNotExist:
            return Response({"error": "User setting not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSettingSerializer(user_setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User setting partially updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE method for deleting a user setting
    def delete(self, request, pk):
        try:
            user_setting = UserSetting.objects.get(pk=pk)
        except UserSetting.DoesNotExist:
            return Response({"error": "User setting not found."}, status=status.HTTP_404_NOT_FOUND)

        user_setting.delete()
        return Response({"message": "User setting deleted successfully."}, status=status.HTTP_204_NO_CONTENT)    
        

# Rate Us
class FeedbackView(APIView):
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)    
    
class CreateSalesOrderAPI(APIView):
    def post(self, request):
        data = request.data

        # Validate mandatory fields
        mandatory_fields = [
            "customer_name",
            "invoice_date", "due_date", "salesperson", "order_amount","quantity"
        ]
        for field in mandatory_fields:
            if not data.get(field):
                return Response(
                    {"error": f"{field} is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate date range
        if data['due_date'] < data['invoice_date']:
            return Response(
                {"error": "Due date cannot be earlier than invoice date."},
                status=status.HTTP_400_BAD_REQUEST
            )
        order_number = random.randint(111111, 999999)
        invoice_number = random.randint(111111, 999999)
        # Save to database
        sales_order = SalesOrder.objects.create(
            customer_name=data['customer_name'],
            invoice_no= f"INV-{order_number}",
            # order_number=data['order_number'],
            order_number = f"ORD-{invoice_number}",
            invoice_date=data['invoice_date'],
            terms=data.get('terms', ''),
            due_date=data['due_date'],
            salesperson=data['salesperson'],
            subject=data.get('subject', ''),
            attachments=data.get('attachments', ''),
            order_amount=data['order_amount'],
            quantity=data['quantity']
        )

        return Response(
            {
                "message": "Sales order created successfully.",
                "data": {
                    "id": sales_order.id,
                    "customer_name": sales_order.customer_name,
                    "invoice_no": sales_order.invoice_no,
                    "order_number": sales_order.order_number,
                    "invoice_date": sales_order.invoice_date,
                    "terms": sales_order.terms,
                    "due_date": sales_order.due_date,
                    "salesperson": sales_order.salesperson,
                    "subject": sales_order.subject,
                    "attachments": sales_order.attachments,
                    "order_amount": sales_order.order_amount,
                    "quantity": sales_order.quantity
                }
            },
            status=status.HTTP_201_CREATED
        )  

class SalesOrderListAPI(APIView):  

        def get(self, request):
            # Get query parameters
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            search = request.query_params.get('search')

            # Filter sales orders
            orders = SalesOrder.objects.all()
            print("--------------------", orders)
            if from_date and to_date:
                orders = orders.filter(invoice_date__range=[from_date, to_date])
            
            if search:
                orders = orders.filter(
                    Q(customer_name__icontains=search) |
                    Q(order_number__icontains=search) |
                    Q(salesperson__icontains=search)
                )
            
            # Order by the newest order on top
            orders = orders.order_by('-invoice_date')

            # Serialize response
            data = [
                {
                    "id": order.id,
                    "customer_name": order.customer_name,
                    "order_number": order.order_number,
                    "invoice_date": order.invoice_date,
                    "salesperson": order.salesperson,
                    "order_amount": order.order_amount
                }
                for order in orders
            ]

            return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
            }, status=status.HTTP_200_OK)
            

# class CreateQuotationOrderAPI(APIView):
#     def post(self, request):
#         data = request.data

#         # Validate mandatory fields
#         mandatory_fields = [
#             "customer_name",
#             "quotation_date",
#             "due_date",
#             "salesperson",
#             "customer_amount",
#             'quantity',
#         ]
#         for field in mandatory_fields:
#             if not data.get(field):
#                 return Response(
#                     {"error": f"{field} is required."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#         # Validate date range
#         if data['due_date'] < data['quotation_date']:
#             return Response(
#                 {"error": "Due date cannot be earlier than quotation date."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         quotation_number = f"QUO-{random.randint(111111, 999999)}"
        
#         # Save to database
#         quotation_order = QuotationOrder.objects.create(
#             customer_name=data['customer_name'],
#             quotation_number=quotation_number,
#             quotation_date=data['quotation_date'],
#             terms=data.get('terms', ''),
#             due_date=data['due_date'],
#             salesperson=data['salesperson'],
#             subject=data.get('subject', ''),
#             attachments=data.get('attachments', ''),
#             customer_amount=data['customer_amount'],
#             quantity=data['quantity']  
#         )

#         return Response(
#             {
#                 "message": "Quotation order created successfully.",
#                 "data": QuotationOrderSerializer(quotation_order).data
#             },
#             status=status.HTTP_201_CREATED
#         )

# class QuotationOrderListAPI(APIView):

#     def get(self, request):
#         # Get query parameters
#         from_date = request.query_params.get('from_date')
#         to_date = request.query_params.get('to_date')
#         search = request.query_params.get('search')

#         # Filter quotation orders
#         orders = QuotationOrder.objects.all()
#         if from_date and to_date:
#             orders = orders.filter(quotation_date__range=[from_date, to_date])
        
#         if search:
#             orders = orders.filter(
#                 Q(customer_name__icontains=search) |
#                 Q(quotation_number__icontains=search) |
#                 Q(salesperson__icontains=search)
#             )
        
#         # Order by the newest order on top
#         orders = orders.order_by('-quotation_date')

#         # Serialize response
#         data = QuotationOrderSerializer(orders, many=True).data

#         return Response({
#             "Status": "1",
#             "message": "Success",
#             "Data": data
#         }, status=status.HTTP_200_OK)       
    
class CreateQuotationOrderAPI(APIView):
    def post(self, request):
        data = request.data

        # Validate mandatory fields
        mandatory_fields = [
            "customer_name",
            "quotation_date",
            "due_date",
            "salesperson",
            "item_name",
            "description",
            "unit_price",
            "discount",
            "quantity",
            "email_id"
        ]
        for field in mandatory_fields:
            if not data.get(field):
                return Response(
                    {"error": f"{field} is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate date range
        if data['due_date'] < data['quotation_date']:
            return Response(
                {"error": "Due date cannot be earlier than quotation date."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a unique quotation number
        quotation_number = f"QUO-{random.randint(111111, 999999)}"
        
        # Fetch salesperson instance
        try:
            salesperson = SalesPerson.objects.get(id=data['salesperson'])
        except SalesPerson.DoesNotExist:
            return Response({"error": "Invalid salesperson ID."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate total amount
        total_amount = (float(data['unit_price']) - float(data['discount'])) * float(data['quantity'])
        
        # Save to database
        quotation_order = QuotationOrderModel.objects.create(
            customer_name=data['customer_name'],
            quotation_number=quotation_number,
            quotation_date=data['quotation_date'],
            terms=data.get('terms', ''),
            due_date=data['due_date'],
            salesperson=salesperson,
            subject=data.get('subject', ''),
            attachments=request.FILES.get('attachments', None),
            item_name=data['item_name'],
            description=data['description'],
            unit_price=data['unit_price'],
            discount=data['discount'],
            quantity=data['quantity'],
            total_amount=total_amount,
            email_id=data['email_id']
        )

        return Response(
            {
                "message": "Quotation order created successfully.",
                "data": QuotationOrderSerializer(quotation_order).data
            },
            status=status.HTTP_201_CREATED
        )

class QuotationOrderListAPI(APIView):
    def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        search = request.query_params.get('search')

        # Filter quotation orders
        orders = QuotationOrderModel.objects.all()
        if from_date and to_date:
            orders = orders.filter(quotation_date__range=[from_date, to_date])
        
        if search:
            orders = orders.filter(
                Q(customer_name__icontains=search) |
                Q(quotation_number__icontains=search) |
                Q(salesperson__icontains=search)
            )
        
        orders = orders.order_by('-quotation_date')
        
        data = QuotationOrderSerializer(orders, many=True).data
        
        return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
        }, status=status.HTTP_200_OK)

class QuotationOrderUpdateAPI(APIView):
    """API for updating an existing Quotation Order"""
    def put(self, request, pk):
        try:
            quotation_order = QuotationOrderModel.objects.get(pk=pk)
        except QuotationOrderModel.DoesNotExist:
            return Response({"error": "Quotation order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = QuotationOrderSerializer(quotation_order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Quotation order updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class QuotationOrderDeleteAPI(APIView):
    """API for deleting an existing Quotation Order"""
    def delete(self, request, pk):
        try:
            quotation_order = QuotationOrderModel.objects.get(pk=pk)
            quotation_order.delete()
            return Response({"message": "Quotation order deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except QuotationOrderModel.DoesNotExist:
            return Response({"error": "Quotation order not found."}, status=status.HTTP_404_NOT_FOUND)    
    
class CreateInvoiceOrderAPI(APIView):
    def post(self, request):
        data = request.data
        mandatory_fields = ["customer_name", "invoice_date", "due_date", "salesperson", "invoice_amount","quantity"]
        for field in mandatory_fields:
            if not data.get(field):
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        if data['due_date'] < data['invoice_date']:
            return Response({"error": "Due date cannot be earlier than invoice date."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=data['product_id'])
            if product.stock < data['quantity']:
                return Response({"error": "Insufficient stock for the product."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Deduct stock
                product.stock -= int(data['quantity'])
                product.save()

                # Create invoice
                invoice_number = random.randint(111111, 999999)
                invoice_order = InvoiceOrder.objects.create(
                    customer_name=data['customer_name'],
                    invoice_number=f"INV-{invoice_number}",
                    invoice_date=data['invoice_date'],
                    terms=data.get('terms', ''),
                    due_date=data['due_date'],
                    salesperson=data['salesperson'],
                    subject=data.get('subject', ''),
                    attachments=data.get('attachments', ''),
                    invoice_amount=data['invoice_amount'],
                    quantity=data['quantity'],
                    product=product
                )

                return Response({
                    "message": "Invoice order created successfully.",
                    "data": InvoiceOrderSerializer(invoice_order).data
                }, status=status.HTTP_201_CREATED)

        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
class InvoiceOrderListAPI(APIView):
    def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        search = request.query_params.get('search')

        orders = InvoiceOrder.objects.all()
        if from_date and to_date:
            orders = orders.filter(invoice_date__range=[from_date, to_date])
        
        if search:
            orders = orders.filter(
                Q(customer_name__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(salesperson__icontains=search)
            )
        
        orders = orders.order_by('-invoice_date')
        data = InvoiceOrderSerializer(orders, many=True).data

        return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
        }, status=status.HTTP_200_OK)

class CreateDeliveryOrderAPI(APIView):
    def post(self, request):
        data = request.data
        mandatory_fields = [
            "customer_name", "delivery_date", "due_date", 
            "salesperson", "delivery_amount", "delivery_location", "received_location", "quantity"
        ]
        for field in mandatory_fields:
            if not data.get(field):
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        if data['due_date'] < data['delivery_date']:
            return Response({"error": "Due date cannot be earlier than delivery date."}, status=status.HTTP_400_BAD_REQUEST)

        delivery_number = random.randint(111111, 999999)
        delivery_order = DeliveryOrder.objects.create(
            customer_name=data['customer_name'],
            delivery_number=f"DEL-{delivery_number}",
            delivery_date=data['delivery_date'],
            delivery_amount=data['delivery_amount'],
            delivery_location=data['delivery_location'],
            received_location=data['received_location'],
            salesperson=data['salesperson'],
            terms=data.get('terms', ''),
            due_date=data['due_date'],
            subject=data.get('subject', ''),
            attachments=data.get('attachments', ''),
            quantity=data['quantity']   # Assuming quantity is an integer in the request data. If it's a string, convert it to integer.
        )

        return Response({
            "message": "Delivery order created successfully.",
            "data": DeliveryOrderSerializer(delivery_order).data
        }, status=status.HTTP_201_CREATED)
        
        
class DeliveryOrderListAPI(APIView):
    def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        search = request.query_params.get('search')

        orders = DeliveryOrder.objects.all()
        if from_date and to_date:
            orders = orders.filter(delivery_date__range=[from_date, to_date])
        
        if search:
            orders = orders.filter(
                Q(customer_name__icontains=search) |
                Q(delivery_number__icontains=search) |
                Q(salesperson__icontains=search)
            )
        
        orders = orders.order_by('-delivery_date')
        data = DeliveryOrderSerializer(orders, many=True).data

        return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
        }, status=status.HTTP_200_OK)

class CreateSupplierPurchaseAPI(APIView):
    
     def post(self, request):
        data = request.data
        mandatory_fields = [
            "supplier_name", "date", "due_date", "amount","quantity"
        ]
        for field in mandatory_fields:
            if not data.get(field):
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        if data['due_date'] < data['date']:
            return Response({"error": "Due date cannot be earlier than purchase date."}, status=status.HTTP_400_BAD_REQUEST)

        supplier_number = random.randint(111111, 999999)
        supplier_purchase = SupplierPurchase.objects.create(
            supplier_name=data['supplier_name'],
            purchase_number=f"PUR-{supplier_number}",
            date=data['date'],
            amount=data['amount'],
            terms=data.get('terms', ''),
            due_date=data['due_date'],
            purchase_person=data.get('purchase_person', ''),
            subject=data.get('subject', ''),
            add_stock=data.get('add_stock', False),
            attachments=data.get('attachments', ''),
            quantity=data['quantity']
        )
        
        
        # If add_stock is True, create a corresponding Stock record
        product_id = data.get('product_id')
        if product_id:
            # Attempt to retrieve the product using product_id
            product = Product.objects.get(id=product_id)
            product.stock += data['quantity']
            product.save()
        else:
            # If 'product_id' is not provided, create a new product
            product = Product.objects.create(
                name=data['product_name'],
                stock=data['quantity'],
        
            )

        return Response({
            "message": "Supplier purchase created successfully.",
            "data": SupplierPurchaseSerializer(supplier_purchase).data
        }, status=status.HTTP_201_CREATED)

        
class SupplierPurchaseListAPI(APIView):
      def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        search = request.query_params.get('search')

        purchases = SupplierPurchase.objects.all()
        if from_date and to_date:
            purchases = purchases.filter(date__range=[from_date, to_date])
        
        if search:
            purchases = purchases.filter(
                Q(supplier_name__icontains=search) |
                Q(purchase_number__icontains=search)
            )
        
        purchases = purchases.order_by('-date')
        data = SupplierPurchaseSerializer(purchases, many=True).data

        return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
        }, status=status.HTTP_200_OK)

class CreateSupplierAPI(APIView):
    def post(self, request):
        serializer = SupplierSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SupplierListAPI(APIView):
    def get(self, request):
        suppliers = Supplier.objects.all()
        serializer = SupplierSerializer(suppliers, many=True)
        return Response({
            "Status": "1",
            "message": "Success",
            "Data": serializer.data
        }, status=status.HTTP_200_OK)       
    

class CreateDeliveryChallanAPI(APIView):
    def post(self, request):
        data = request.data
        delivery_challan = DeliveryChallan.objects.create(
            customer_name=data['customer_name'],
            delivery_challan_number=data['delivery_challan_number'],
            customer_note=data.get('customer_note', '')
        )
        return Response({
            "message": "Delivery challan created successfully.",
            "data": DeliveryChallanSerializer(delivery_challan).data
        }, status=status.HTTP_201_CREATED)

class DeliveryChallanListAPI(APIView):
    def get(self, request):
        delivery_challans = DeliveryChallan.objects.all()
        serializer = DeliveryChallanSerializer(delivery_challans, many=True)
        
        # Return the serialized data in the desired response format
        return Response({
            "Status": "1",
            "message": "Success",
            "Data": serializer.data
        })
    
class UpdateDeliveryChallanAPI(APIView):
    def patch(self, request, pk):
        try:
            delivery_challan = DeliveryChallan.objects.get(pk=pk)
        except DeliveryChallan.DoesNotExist:
            return Response({"error": "Delivery challan not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeliveryChallanSerializer(delivery_challan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Delivery challan updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    
    
class ProductListCreateAPIView(APIView):
    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response({
            "Status": "1",
            "message": "Success",
            "Data": serializer.data
        })

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductUpdateDeleteAPIView(APIView):
    def put(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        product.delete()
        return Response({"message": "Product deleted successfully."}, status=status.HTTP_204_NO_CONTENT)    

class SalesPersonListCreateAPIView(APIView):
    def get(self, request):
        salespersons = SalesPerson.objects.all()
        serializer = SalesPersonSerializer(salespersons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SalesPersonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)