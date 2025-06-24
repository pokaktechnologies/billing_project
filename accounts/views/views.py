from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import get_object_or_404
from ..models import CustomUser, Feature
from django.db.models import Q
from django.db import transaction, IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from ..models import *
from ..serializers.serializers import *
from accounts.permissions import HasModulePermission
from rest_framework.authtoken.models import Token 
from decimal import Decimal
from django.utils.dateparse import parse_date

# from .serializers import CustomUserCreateSerializer, OTPSerializer, GettingStartedSerializer,HelpLinkSerializer,NotificationSerializer, UserSettingSerializer, FeedbackSerializer,QuotationOrderSerializer,InvoiceOrderSerializer,DeliveryOrderSerializer,SupplierPurchaseSerializer,SupplierSerializer,DeliveryChallanSerializer
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
                # Deduct stockt 
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

# class CreateSupplierPurchaseAPI(APIView):
    
#      def post(self, request):
#         data = request.data
#         mandatory_fields = [
#             "supplier_name", "date", "due_date", "amount","quantity"
#         ]
#         for field in mandatory_fields:
#             if not data.get(field):
#                 return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

#         if data['due_date'] < data['date']:
#             return Response({"error": "Due date cannot be earlier than purchase date."}, status=status.HTTP_400_BAD_REQUEST)

#         supplier_number = random.randint(111111, 999999)
#         supplier_purchase = SupplierPurchase.objects.create(
#             supplier_name=data['supplier_name'],
#             purchase_number=f"PUR-{supplier_number}",
#             date=data['date'],
#             amount=data['amount'],
#             terms=data.get('terms', ''),
#             due_date=data['due_date'],
#             purchase_person=data.get('purchase_person', ''),
#             subject=data.get('subject', ''),
#             add_stock=data.get('add_stock', False),
#             attachments=data.get('attachments', ''),
#             quantity=data['quantity']
#         )
        
        
#         # If add_stock is True, create a corresponding Stock record
#         product_id = data.get('product_id')
#         if product_id:
#             # Attempt to retrieve the product using product_id
#             product = Product.objects.get(id=product_id)
#             product.stock += data['quantity']
#             product.save()
#         else:
#             # If 'product_id' is not provided, create a new product
#             product = Product.objects.create(
#                 name=data['product_name'],
#                 stock=data['quantity'],
        
#             )

#         return Response({
#             "message": "Supplier purchase created successfully.",
#             "data": SupplierPurchaseSerializer(supplier_purchase).data
#         }, status=status.HTTP_201_CREATED)

        
# class SupplierPurchaseListAPI(APIView):
#       def get(self, request):
#         from_date = request.query_params.get('from_date')
#         to_date = request.query_params.get('to_date')
#         search = request.query_params.get('search')

#         purchases = SupplierPurchase.objects.all()
#         if from_date and to_date:
#             purchases = purchases.filter(date__range=[from_date, to_date])
        
#         if search:
#             purchases = purchases.filter(
#                 Q(supplier_name__icontains=search) |
#                 Q(purchase_number__icontains=search)
#             )
        
#         purchases = purchases.order_by('-date')
#         data = SupplierPurchaseSerializer(purchases, many=True).data

#         return Response({
#             "Status": "1",
#             "message": "Success",
#             "Data": data
#         }, status=status.HTTP_200_OK)

# class CreateSupplierAPI(APIView):
#     def post(self, request):
#         serializer = SupplierSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class SupplierListAPI(APIView):
#     def get(self, request):
#         suppliers = Supplier.objects.all()
#         serializer = SupplierSerializer(suppliers, many=True)
#         return Response({
#             "Status": "1",
#             "message": "Success",
#             "Data": serializer.data
#         }, status=status.HTTP_200_OK)    
    

class SupplierAPIView(APIView):
    def get(self, request,pk=None):
        if pk:
            supplier = get_object_or_404(Supplier, pk=pk)
            serializer = SupplierDetailSerializer(supplier)
            return Response({"Status": "1", "message": "Success", "Data": [serializer.data]}, status=status.HTTP_200_OK)
        else:
            suppliers = Supplier.objects.all().order_by('-created_at')
            serializer = SupplierSerializer(suppliers, many=True)
            return Response({"Status": "1", "message": "Success", "Data": serializer.data}, status=status.HTTP_200_OK)
        
    def post(self, request):
        serializer = SupplierSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "Status": "1",
                    "message": "Supplier created successfully.",
                    "id": serializer.data['id'],
                    "supplier_number": serializer.data['supplier_number']
                }
                , status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        serializer = SupplierSerializer(supplier, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "Status": "1",
                    "message": "Supplier updated successfully.",
                    "id": serializer.data['id'],
                    "supplier_number": serializer.data['supplier_number']
                }
                , status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.delete()
        return Response({"Status": "1", "message": "Supplier deleted successfully."}, status=status.HTTP_200_OK)

           
    

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
        data = ProductSerializer(products, many=True).data
        return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Status": "1",
                "message": "Product created successfully.",
                "Data": [serializer.data]
            }, status=status.HTTP_201_CREATED)
        return Response({
            "Status": "0",
            "message": "Validation failed.",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

# Retrieve, Update, and Delete a Product
class ProductDetailAPI(APIView):
    def get_object(self, product_id):
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None

    def get(self, request, product_id):
        product = self.get_object(product_id)
        if not product:
            return Response({
                "Status": "0",
                "message": "Product not found."
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = [ProductSerializer(product).data]
        return Response({
            "Status": "1",
            "message": "Success",
            "Data": data
        }, status=status.HTTP_200_OK)

    def put(self, request, product_id):
        product = self.get_object(product_id)
        if not product:
            return Response({
                "Status": "0",
                "message": "Product not found."
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Status": "1",
                "message": "Product updated successfully.",
                "Data": [serializer.data]
            }, status=status.HTTP_200_OK)

        return Response({
            "Status": "0",
            "message": "Validation failed.",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, product_id):
        product = self.get_object(product_id)
        if not product:
            return Response({
                "Status": "0",
                "message": "Product not found."
            }, status=status.HTTP_404_NOT_FOUND)

        product.delete()
        return Response({
            "Status": "1",
            "message": "Product deleted successfully."
        }, status=status.HTTP_200_OK)


class SalesPersonListCreateAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            salesperson = get_object_or_404(SalesPerson, pk=pk)
            serializer = SalesPersonSerializer(salesperson)
            return Response(
                {"Status": "1", "message": "Success", "Data": [serializer.data]},
                status=status.HTTP_200_OK
            )
        else:
            salespersons = SalesPerson.objects.all()
            serializer = SalesPersonSerializer(salespersons, many=True)
            return Response(
                {"Status": "1", "message": "Success", "Data": serializer.data},
                status=status.HTTP_200_OK
            )

    def post(self, request):
        serializer = SalesPersonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Status": "1", "message": "Salesperson created successfully.", "Data": [serializer.data]},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"Status": "0", "message": "Validation failed.", "Data": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    def patch(self, request, pk):
        salesperson = get_object_or_404(SalesPerson, pk=pk)
        serializer = SalesPersonSerializer(salesperson, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "Status": "1",
                    "message": "Salesperson updated successfully.",
                    "salesperson_id": salesperson.id,
                    "updated_data": [serializer.data],
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {"Status": "0", "message": "Validation failed.", "Data": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    # DELETE - Delete Salesperson
    def delete(self, request, pk):
        salesperson = get_object_or_404(SalesPerson, pk=pk)
        salesperson.delete()
        return Response(
            {
                "Status": "1",
                "message": "Salesperson deleted successfully.",
                "deleted_salesperson_id": pk
            },
            status=status.HTTP_200_OK
        )
class QuotationOrderAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, qid=None, pid=None):
        if qid:
            quotation = get_object_or_404(QuotationOrderModel, id=qid)

            # Return specific quotation item if product ID is provided
            if pid:
                quotation_item = get_object_or_404(QuotationItem, quotation=quotation, product_id=pid)
                serializer = QuotationItemSerializer(quotation_item)
                return Response({
                    "status": "1",
                    "message": "Quotation item retrieved successfully.",
                    "data": [serializer.data]
                })

            # Terms and Conditions
            terms_data = []
            if quotation.termsandconditions:
                terms_points = TermsAndConditionsPoint.objects.filter(
                    terms_and_conditions=quotation.termsandconditions
                )
                terms_data = TermsAndConditionsPointSerializer(terms_points, many=True).data

            # Contract and Sections
            contract_data = {}
            if quotation.contract:
                contract_data = ContractSerializer(quotation.contract).data
                sections = ContractSection.objects.filter(contract=quotation.contract)
                contract_data['sections'] = []

                for section in sections:
                    points = ContractPoint.objects.filter(section=section)
                    section_data = ContractSectionSerializer(section).data
                    section_data['points'] = ContractPointSerializer(points, many=True).data
                    contract_data['sections'].append(section_data)

            # Quotation Items
            item_list = []
            for item in quotation.items.all():
                item_list.append({
                    "id": item.id,
                    "name": item.product.name,
                    "product_id": item.product.pk,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price or item.product.unit_price,
                    "total": item.total,
                    "sgst": item.sgst,
                    "cgst": item.cgst,
                    "sgst_percentage": item.sgst_percentage,
                    "cgst_percentage": item.cgst_percentage,
                    "sub_total": item.sub_total,
                })

            # Full Quotation Response
            return Response({
                "status": "1",
                "message": "success",
                "quotation": [{
                    "id": quotation.id,
                    "client_name": f"{quotation.client.first_name} {quotation.client.last_name}" if quotation.client else "",
                    "client_id": quotation.client.id if quotation.client else None,
                    "address": quotation.delivery_address,
                    "delivery_location": quotation.delivery_location,
                    "quotation_number": quotation.quotation_number,
                    "project_name": quotation.project_name,
                    "termsandconditions_id": quotation.termsandconditions.id if quotation.termsandconditions else None,
                    "termsandconditions": terms_data,
                    "termsandcondtions_title": quotation.termsandconditions.title if quotation.termsandconditions else "",
                    "quotation_date": str(quotation.quotation_date),
                    "grand_total": quotation.grand_total,
                    "selesperson": quotation.client.salesperson.id if quotation.client and quotation.client.salesperson else "",
                    "salesperson_name": f"{quotation.client.salesperson.first_name} {quotation.client.salesperson.last_name}" if quotation.client and quotation.client.salesperson else "",
                    "contract_id": quotation.contract.id if quotation.contract else None,
                    "contract_title": quotation.contract.title if quotation.contract else "",
                    "contract": contract_data,
                    "items": item_list,
                }]
            }, status=status.HTTP_200_OK)

        # Handle list of quotations with optional filters
        quotations = QuotationOrderModel.objects.all().order_by('-id')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        search = request.query_params.get('search')

        if from_date and to_date:
            quotations = quotations.filter(quotation_date__range=[from_date, to_date])
        if search:
            quotations = quotations.filter(customer_name__icontains=search)

        serializer = QuotationOrderSerializer(quotations, many=True)
        return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)


        
    def post(self, request, qid=None, pid=None):
        data = request.data
        try:
            if qid:
                quotation = get_object_or_404(QuotationOrderModel, id=qid)
                pid = request.data.get("product", None)
                if pid:
                    product = get_object_or_404(Product, id=pid)
                    sgst_percentage = request.data.get("sgst_percentage", 0)
                    cgst_percentage = request.data.get("cgst_percentage", 0)
                    quantity = request.data.get("quantity", 1)
                    unit_price = request.data.get("unit_price", 0)
                    
                    # QuotationItem.objects.get_or_create(quotation=quotation, product=product, cgst_percentage=cgst_percentage, sgst_percentage=sgst_percentage, unit_price=unit_price, quantity=quantity)
                    new_item, is_created = QuotationItem.objects.get_or_create(quotation=quotation, product=product)
                    new_item.cgst_percentage=cgst_percentage
                    new_item.sgst_percentage=sgst_percentage
                    new_item.unit_price= unit_price
                    new_item.quantity=quantity
                    new_item.save() 
                    return Response({"status": "1", "message": "success"})
                else:
                    return Response({"status": "0", "message": "You must provide product id"})
            
            with transaction.atomic():
                terms_id = data.get("termsandconditions")
                print("terms_id", terms_id)
                if terms_id and not TermsAndConditions.objects.filter(id=terms_id).exists():
                    return Response({"error": "Invalid terms and conditions ID"}, status=status.HTTP_400_BAD_REQUEST)
                
                # contract = data.get("contract")
                # if contract and not Contract.objects.filter(id=contract).exists():
                #     return Response({"error": "Invalid contract ID"}, status=status.HTTP_400_BAD_REQUEST)
                
                contract_data = data.get("contract", [])
                if not contract_data:
                    return Response({"error": "Quotation must have a contract."}, status=status.HTTP_400_BAD_REQUEST)
                
            # if not request.user.is_authenticated:
            #     return Response({"error": "User is not authenticated."}, status=401)
                
                quotation = QuotationOrderModel.objects.create(
                    user=CustomUser.objects.get(id=request.user.id),
                    client=Customer.objects.get(id=data.get("client")),
                    project_name=data.get("project_name"),
                    delivery_address=data.get("delivery_address"),
                    quotation_number=data.get('quotation_number'),
                    quotation_date=data.get("quotation_date"),
                    # contract=Contract.objects.get(id=contract) if contract else None,
                    # remark=data.get("remark", ""),
                    
                    # attachments=data.get("attachments", None),
                    #grand_total=0  ,
                    delivery_location=data.get("delivery_location", ""),  # New Field
                    # bank_account_id= bank_account_id,
                    termsandconditions_id=terms_id  # Add terms and condition
                )
                contract = Contract.objects.create(title=contract_data['title'])
                for section_data in contract_data.get('sections', []):
                    section = ContractSection.objects.create(contract=contract, title=section_data.get('title', ''))
                    
                    for point_data in section_data.get('points', []):
                        ContractPoint.objects.create(section=section, points=point_data['points'])

                # return contract
                quotation.contract = contract

                # Create Quotation Items
                items = data.get("items", [])
                if not items:
                    return Response({"error": "Quotation must have at least one item."}, status=status.HTTP_400_BAD_REQUEST)
                
                total_amount = Decimal(0) 

                tot_grand = []
                for item in items:
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)

                    product = Product.objects.get(id=product_id)
                    quantity = Decimal(str(item.get("quantity", 1)))
                    
                    unit_price = Decimal(str(item.get("unit_price", 0)))
                    sgst_percentage = Decimal(str(item.get("sgst_percentage", 0)))
                    cgst_percentage = Decimal(str(item.get("cgst_percentage", 0)))

                    
                    

                    
                    if unit_price == 0:
                        
                        unit_price = product.unit_price
                    item_total = quantity * unit_price
                    quotation_item = QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=quantity, 
                        sgst_percentage=sgst_percentage,
                        cgst_percentage=cgst_percentage,
                        unit_price= unit_price
                   
                    )
                    tot_grand.append(quotation_item.sub_total)

                

                total_amount += item_total

                quotation.grand_total = sum(tot_grand)
              
                quotation.save()

                

                return Response({
                    "status": "1",
                    "message": "Quotation created successfully.",
                    "quotation_id": quotation.id,
                    "quotation_number": quotation.quotation_number,
                    "grand_total": str(quotation.grand_total)
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, qid=None, pid=None):
        try:
            if qid:
                quotation = get_object_or_404(QuotationOrderModel, id=qid)
                serializer = QuotationOrderSerializer(quotation, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


                contract_data = request.data.get("contract")
                if contract_data:
                    # if contract already exists, update it
                    if quotation.contract:
                        contract = quotation.contract
                        contract.title = contract_data.get("title", contract.title)
                        contract.save()

                        # Delete old sections and points
                        contract.sections.all().delete()
                    else:
                        contract = Contract.objects.create(title=contract_data["title"])
                        quotation.contract = contract

                    # Create new sections and points
                    for section_data in contract_data.get("sections", []):
                        section = ContractSection.objects.create(
                            contract=contract,
                            title=section_data.get("title", "")
                        )
                        for point_data in section_data.get("points", []):
                            ContractPoint.objects.create(
                                section=section,
                                points=point_data["points"]
                            )
                    quotation.save()
                
                # check if product payload have duplicate
                product_ids = [item.get("product") for item in request.data.get("items", [])]
                if len(product_ids) != len(set(product_ids)):
                    return Response({"error": "Duplicate product id found in payload."}, status=status.HTTP_400_BAD_REQUEST)

                for item_data in request.data.get("items", []):
                    
                    product_id = item_data.get("product")
                    product = get_object_or_404(Product, id=product_id)

                    existing_item = QuotationItem.objects.filter(quotation=quotation, product=product).first()
                    if existing_item:
                        existing_item.quantity = item_data.get("quantity", existing_item.quantity)
                        existing_item.unit_price = item_data.get("unit_price", existing_item.unit_price)
                        existing_item.sgst_percentage = item_data.get("sgst_percentage", existing_item.sgst_percentage)
                        existing_item.cgst_percentage = item_data.get("cgst_percentage", existing_item.cgst_percentage)
                        existing_item.save()
                    else:
                        QuotationItem.objects.create(
                            quotation=quotation,
                            product=product,
                            quantity=item_data.get("quantity", 1),
                            unit_price=item_data.get("unit_price", 0),
                            sgst_percentage=item_data.get("sgst_percentage", 0),
                            cgst_percentage=item_data.get("cgst_percentage", 0),
                        )

                quotation.update_grand_total()

                return Response({"message": "Quotation updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)      
        
    def delete(self, request, qid=None, pid=None):
        if not qid:
            return Response({"error": "Quotation ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                quotation = get_object_or_404(QuotationOrderModel, id=qid)

                if pid:
                    quotation_item = get_object_or_404(QuotationItem, quotation=quotation, id=pid)
                    quotation_item.delete()
                    return Response({
                        "status": "1",
                        "message": "Quotation Item deleted successfully."
                    }, status=status.HTTP_200_OK)
                else:
                    quotation.items.all().delete()
                    quotation.delete()
                    return Response({
                        "status": "1",
                        "message": "Quotation deleted successfully."
                    }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

   
#   class QuotationItemUpdateView(APIView):
#     """
#     API view to update a specific quotation item's quantity and price.
#     """
#     # permission_classes = [IsAuthenticated]

#     def patch(self, request, qid, pid):
#         """
#         Update specific fields of a QuotationItem for the given quotation_id and product_id
#         """
#         # First, get the quotation or return 404
#         quotation = get_object_or_404(QuotationOrderModel, id=qid)
        
#         # Then, get the specific item from this quotation that matches the product_id
#         item = get_object_or_404(QuotationItem, quotation=quotation, product_id=pid)
        
#         # Use a serializer to validate the data
#         serializer = QuotationItemUpdateSerializer(item, data=request.data, partial=True)
        
#         if serializer.is_valid():
#             # Save the updated item (which will trigger the save method in QuotationItem)
#             serializer.save()
            
#             # Return the updated item data
#             return Response(serializer.data, status=status.HTTP_200_OK)
        
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
# class  PrintQuotationAPI(APIView):

#     def get(self, request, qid=None):
#         # Fetch specific quotation by ID
#         quotation = get_object_or_404(QuotationOrderModel, id=qid)
        
#         print(f"Quotation Address: {quotation.address}")  # This will print the address in your console/logs
        
#         salesperson_address = quotation.salesperson.address if quotation.salesperson else None
#         termsandconditions_points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=quotation.termsandconditions)
      
#         salesperson_name = (
#             f"{quotation.salesperson.first_name} {quotation.salesperson.last_name}"
#             if quotation.salesperson else None
#         )
        
#         if quotation.contract:
#             contract = Contract.objects.get(id=quotation.contract.id)
#             contract_sections = ContractSection.objects.filter(contract=quotation.contract.id)

#             contract_data = {
#                 **ContractSerializer(contract).data,
#                 'sections': []
#             }

#             for section in contract_sections:
#                 section_serialized = ContractSectionSerializer(section).data
#                 points = ContractPoint.objects.filter(section=section.id)
#                 points_serialized = ContractPointSerializer(points, many=True).data

#                     # Add points directly into the section
#                 section_serialized['points'] = points_serialized

#                 contract_data['sections'].append(section_serialized)

#         else:
#             contract_data = {}        


            
#         # if quotation.bank_account:
#         #     bank_account_serializer = BankAccountSerializer(quotation.bank_account)
#         #     bank_account_data = [bank_account_serializer.data]  # wrap in list
#         # else:
#         #     bank_account_data = []  # empty array if no account
#         # Get quotation items
#         quotation_items = QuotationItem.objects.filter(quotation=quotation)
#         item_list = []

#         # Prepare item details for the print view
#         for item in quotation_items:
#             item_data = {
#                 "item_name": item.product.name,  # Assuming 'product' is a ForeignKey to a Product model
#                 "description": item.product.product_description,  # Assuming 'description' exists in the Product model
#                 "quantity": item.quantity,
#                 "rate": item.product.unit_price,
#                 "cgst": item.cgst,
#                 "sgst": item.sgst,
#                 "tax": item.sgst + item.cgst,  # Assuming tax is stored as SGST and CGST in QuotationItem
#                 "amount": item.total,  # Total amount for the item (rate * quantity + tax)
#                 # "total": item.total,  # Total amount for the item (rate * quantity + tax)

#             }
#             item_list.append(item_data)
         

#         # Prepare the response data
#         quotation_data = {
#             "quotation_id": quotation.id,
#             "": quotation.customer_name,
#             "address": quotation.address if quotation.address else None,
#             "salesperson_name": salesperson_name,
#             "salesperson_address": salesperson_address,
#             "quotation_number": quotation.quotation_number,
#             "quotation_date": str(quotation.quotation_date),
#             # "bank_account": bank_account_data,
#             # "email_id": quotation.email_id,
#             "termsandconditions_title": quotation.termsandconditions.title if quotation.termsandconditions else None, 
#             "termsandconditions": PrintTermsAndConditionsSerializer(termsandconditions_points, many=True).data,
#             "subtotal": sum(item['amount'] - item['tax'] for item in item_list),
#             "total": sum(item['amount'] for item in item_list),
#             "items": item_list,
#             "contract_id": quotation.contract.id if quotation.contract else None,
#             "contract_title": quotation.contract.title if quotation.contract else "",
#             "contract": contract_data,

#         }

#         # Return the quotation data wrapped in an array (as requested)
#         return Response({
#             "status": "1",
#             "message": "success",
#             "data": [quotation_data]  # Wrap the response data in a list (array of objects)
#         }, status=status.HTTP_200_OK)

class  PrintQuotationAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, qid=None):
        qoutation = get_object_or_404(QuotationOrderModel, id=qid)
        serializer = PrintQuotationOrderSerializer(qoutation)
        qoutation_data = serializer.data
        return Response({
            "status": "1",
            "message": "success",
            "data": [qoutation_data]
        }, status=status.HTTP_200_OK)


class SalesOrderAPI(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            with transaction.atomic():
                # print("\n--- DEBUGGING SALES ORDER POST ---")
                # print(f"Received Data: {data}")

                # sales_order_id = f"SO-{random.randint(111111, 999999)}"

                customer_id = data.get("customer")
                customer = get_object_or_404(Customer, id=customer_id)

                bank_account = None
                bank_account_id = data.get("bank_account")
                terms_and_conditions = data.get("termsandconditions")

                # if not terms_and_conditions:
                #     return Response({"error": "Terms and conditions not provided."}, status=status.HTTP_400_BAD_REQUEST)

                # This will raise 404 if the object doesn't exist
                if terms_and_conditions:
                    terms_and_conditions_obj = get_object_or_404(TermsAndConditions, id=terms_and_conditions)

                    
                if bank_account_id:
                    bank_account = get_object_or_404(BankAccount, id=bank_account_id)

                sales_order = SalesOrderModel.objects.create(
                    customer=customer,
                    user=request.user,
                    sales_order_number=data.get("sales_order_number"),
                    sales_date=data.get("sales_date"),
                    purchase_order_number=data.get("purchase_order_number"),
                    remark=data.get("remark", ""),
                    termsandconditions=terms_and_conditions_obj or None,
                    delivery_location=data.get("delivery_location", ""),
                    delivery_address=data.get("delivery_address", ""),
                    bank_account=bank_account,
                    is_delivered=data.get("is_delivered", False)
                )

                items = data.get("items", [])
                if not items:
                    return Response({"error": "Sales order must have at least one item."}, status=status.HTTP_400_BAD_REQUEST)

                for item in items:
                    product = get_object_or_404(Product, id=item.get("product"))
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=product,
                        quantity=item.get("quantity", 1),
                        pending_quantity=item.get("quantity", 1),
                        unit_price=item.get("unit_price", 0),
                        sgst_percentage=item.get("sgst_percentage", 0),
                        cgst_percentage=item.get("cgst_percentage", 0),
                        is_item_delivered=item.get("is_item_delivered", False)
                    )

                sales_order.update_grand_total()

                return Response({
                    "message": "Sales Order created successfully",
                    "sales_order_number": sales_order.sales_order_number,
                    "sales_order_id": sales_order.id,
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, sid=None):
        if sid:
            sales_order = get_object_or_404(SalesOrderModel, id=sid)
            serializer = NewsalesOrderSerializer(sales_order)
            items = SalesOrderItem.objects.filter(sales_order=sales_order)
            termsandconditions_points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=sales_order.termsandconditions)

            item_list = []
            for item in items:
                product_data = ProductSerializer(item.product).data
                product_data.update({
                    "id": item.id,
                    "product_id": item.product.id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": item.total,
                    "sgst": item.sgst,
                    "cgst": item.cgst,
                    "sgst_percentage": item.sgst_percentage,
                    "cgst_percentage": item.cgst_percentage,
                    "is_item_delivered": item.is_item_delivered,
                    "sub_total": item.sub_total,
                })
                item_list.append(product_data)

            return Response({
                'status': '1',
                'message': 'success',
                'data': [
                    {
                        **serializer.data,
                        'termsandconditions_points': PrintTermsAndConditionsSerializer(termsandconditions_points, many=True).data,
                        'items': item_list
                    }
                ]
            })

        else:
            sales_orders = SalesOrderModel.objects.filter(user=request.user).order_by('-id')
            serializer = NewsalesOrderSerializer(sales_orders, many=True)
            return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)

    def patch(self, request, sid=None, pid=None):
        try:
            if sid and pid:
                sales_order = get_object_or_404(SalesOrderModel, id=sid)
                item = get_object_or_404(SalesOrderItem, sales_order=sales_order, id=pid)
                serializer = SalesOrderItemSerializer(item, data=request.data, partial=True)

                # new_product_id = request.data.get("product")
                # if new_product_id and new_product_id != item.product.id:
                #     if SalesOrderItem.objects.filter(sales_order=sales_order, product_id=new_product_id).exists():
                #         return Response({"error": "This product already exists in the sales order."}, status=status.HTTP_400_BAD_REQUEST)

                if serializer.is_valid():
                    serializer.save()
                    sales_order.update_grand_total()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            elif sid:
                sales_order = get_object_or_404(SalesOrderModel, id=sid)
                serializer = NewsalesOrderSerializer(sales_order, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                # check if product payload have duplicate
                product_ids = [item.get("product") for item in request.data.get("items", [])]
                if len(product_ids) != len(set(product_ids)):
                    return Response({"error": "Duplicate product id found in payload."}, status=status.HTTP_400_BAD_REQUEST)

                for item_data in request.data.get("items", []):
                    
                    product_id = item_data.get("product")
                    product = get_object_or_404(Product, id=product_id)

                    existing_item = SalesOrderItem.objects.filter(sales_order=sales_order, product=product).first()
                    if existing_item:
                        # Get delivery state before update
                        old_qty     = existing_item.quantity
                        old_pending = existing_item.pending_quantity
                        delivered   = old_qty - old_pending
                        # update quantity & compute new pending
                        new_qty = Decimal(item_data.get("quantity", 0))
                        existing_item.quantity = new_qty
                        existing_item.pending_quantity = max(new_qty - delivered, Decimal(0))
                        existing_item.unit_price = item_data.get("unit_price", existing_item.unit_price)
                        existing_item.sgst_percentage = item_data.get("sgst_percentage", existing_item.sgst_percentage)
                        existing_item.cgst_percentage = item_data.get("cgst_percentage", existing_item.cgst_percentage)
                        existing_item.save()
                    else:
                        SalesOrderItem.objects.create(
                            sales_order=sales_order,
                            product=product,
                            quantity=item_data.get("quantity", 1),
                            pending_quantity=item_data.get("quantity", 1),
                            unit_price=item_data.get("unit_price", 0),
                            sgst_percentage=item_data.get("sgst_percentage", 0),
                            cgst_percentage=item_data.get("cgst_percentage", 0),
                        )

                sales_order.update_grand_total()

                return Response({"message": "Sales Order updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def delete(self, request, sid=None, pid=None):
        if not sid:
            return Response({"error": "Sales Order ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                sales_order = get_object_or_404(SalesOrderModel, id=sid)
                if pid:
                    sales_order_item = get_object_or_404(SalesOrderItem, sales_order=sales_order, id=pid)
                    sales_order_item.delete()
                    return Response({
                        "status": "1",
                        "message": "Sales Order Item deleted successfully."
                    }, status=status.HTTP_200_OK)
                else:
                    sales_order.items.all().delete()
                    sales_order.delete()
                    return Response({
                        "status": "1",
                        "message": "Sales Order deleted successfully."
                    }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)            



class  PrintSalesOrderAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, sid=None):
        sales_order = get_object_or_404(SalesOrderModel, id=sid)
        serializer = PrintSalesOrderSerializer(sales_order)
        sales_order_data = serializer.data
        return Response({
            "status": "1",
            "message": "success",
            "data": [sales_order_data]
        }, status=status.HTTP_200_OK)

class SalesOrderItemsList(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, sid=None):
        sales_order = get_object_or_404(SalesOrderModel, id=sid)
        items = SalesOrderItem.objects.filter(sales_order=sales_order,is_item_delivered=False)
        serializer = SalesOrderItemOnlySerializer(items, many=True)
        return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)

class SalesOrderByNotDelivered(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request,customer_id=None):
        sales_orders = SalesOrderModel.objects.filter(is_delivered=False,customer=customer_id)

        if not sales_orders.exists():
            return Response({"status": "0", "message": "No sales orders found.", "data": []}, status=status.HTTP_200_OK)

        # Create a list to hold the sales order data
        data = []
        for order in sales_orders:
            data.append({
                "id": order.id,
                "sales_order_number": order.sales_order_number,
                "client_first_name": order.customer.first_name,
                "client_last_name": order.customer.last_name,
                
            })

        # Return the response with the data
        return Response({"status": "1", "data": data}, status=status.HTTP_200_OK)

class SalesOrderByInvoiced(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id=None):
        # Fetch deliveries where is_invoiced is False
        deliveries = DeliveryFormModel.objects.filter(sales_order__customer=customer_id, is_invoiced=False)

        # Create a set to store unique sales order ids (to avoid duplicates)
        sales_order_ids = set(delivery.sales_order.id for delivery in deliveries)

        # Fetch the sales orders that have deliveries with is_invoiced=False
        sales_orders = SalesOrderModel.objects.filter(id__in=sales_order_ids)

        # Create a list to hold the sales order data
        data = []
        for order in sales_orders:
            data.append({
                "id": order.id,
                "sales_order_number": order.sales_order_number,
                "client_first_name": order.customer.first_name,
                "client_last_name": order.customer.last_name,
            })

        # Return the response with the data
        return Response({"status": "1", "data": data}, status=status.HTTP_200_OK)



class DeliveryFormAPI(APIView): 
    def get(self, request, did=None):
        if did:
            delivery = get_object_or_404(DeliveryFormModel, id=did)
            delivery_serializer = NewDeliverySerializer(delivery)
            
            delivery_items = DeliveryItem.objects.filter(delivery_form=delivery)
            delivery_item_serializer = DeliveryItemsSerializer(delivery_items, many=True)
            termsandconditions_points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=delivery.termsandconditions)
            termsandconditions_point_serializer = TermsAndConditionsPointSerializer(termsandconditions_points, many=True)
            return Response({
                'status': '1',
                'message': 'success',
                'data':[{
                    **delivery_serializer.data,
                    'termsandconditions_points': termsandconditions_point_serializer.data,
                    'items': delivery_item_serializer.data
                }]
            })
        else:
            deliveries = DeliveryFormModel.objects.all().order_by('-id')
            serializer = NewDeliverySerializer(deliveries, many=True)
            return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            with transaction.atomic():

                # delivery_id = f"DN-{random.randint(111111, 999999)}"

                customer_id = data.get("customer")
                customer = get_object_or_404(Customer, id=customer_id)

                bank_account = None
                bank_account_id = data.get("bank_account")
                terms_and_conditions = data.get("termsandconditions")
                sales_order = data.get("sales_order")

                if not terms_and_conditions:
                    return Response({"error": "Terms and conditions not provided."}, status=status.HTTP_400_BAD_REQUEST)

                if not sales_order:
                    return Response({"error": "Sales order not provided."}, status=status.HTTP_400_BAD_REQUEST)
                
                # check the sales order belongs to the customer
                sales_order_obj = get_object_or_404(SalesOrderModel, id=sales_order)
                if sales_order_obj.customer.id != customer_id:
                    return Response({"error": "Sales order does not belong to the customer."}, status=status.HTTP_400_BAD_REQUEST)

                # This will raise 404 if the object doesn't exist
                terms_and_conditions_obj = get_object_or_404(TermsAndConditions, id=terms_and_conditions)
                sales_order_obj = get_object_or_404(SalesOrderModel, id=sales_order)

                # Create the DeliveryFormModel object
                delivery_form = DeliveryFormModel.objects.create(
                    customer=customer,
                    delivery_number=data.get("delivery_number"),
                    user=request.user,
                    sales_order=sales_order_obj,
                    delivery_date=data.get("delivery_date"),
                    time=data.get("time"),  # Add time here
                    termsandconditions=terms_and_conditions_obj,
                    delivery_location=data.get("delivery_location", ""),
                    delivery_address=data.get("delivery_address", ""),
                )

                items = data.get("items", [])
                if not items:
                    return Response({"error": "Delivery must have at least one item."}, status=status.HTTP_400_BAD_REQUEST)

                for item in items:
                    product = get_object_or_404(Product, id=item.get("product"))
                    delivered_qty = Decimal(item.get("delivered_quantity", 0))
                    delivery_item = DeliveryItem.objects.create(
                        delivery_form=delivery_form,
                        product=product,
                        delivered_quantity=delivered_qty,
                        unit_price=item.get("unit_price", 0),
                        sgst_percentage=item.get("sgst_percentage", 0),
                        cgst_percentage=item.get("cgst_percentage", 0),
                    )

                    # Update the pending quantity in sales order items
                    sales_order_items = SalesOrderItem.objects.filter(sales_order=sales_order_obj, product=product)
                    for sales_order_item in sales_order_items:

                        if delivered_qty > sales_order_item.pending_quantity:
                            raise ValueError(f"Delivered quantity ({delivered_qty}) exceeds pending quantity ({sales_order_item.pending_quantity}) for product {product.name}")

                        if sales_order_item.pending_quantity >= delivered_qty:
                            sales_order_item.pending_quantity -= delivered_qty
                            if sales_order_item.pending_quantity == 0:
                                sales_order_item.is_item_delivered = True
                        else:
                            sales_order_item.pending_quantity = Decimal(0)
                        sales_order_item.save(update_fields=["pending_quantity", "is_item_delivered"])

                    # Update grand total of the delivery form
                    delivery_form.update_grand_total()

                # After updating the items, check if all items are delivered by querying the model
                all_items_delivered = not SalesOrderItem.objects.filter(sales_order=sales_order_obj, is_item_delivered=False).exists()

                if all_items_delivered:
                    sales_order_obj.is_delivered = True
                    sales_order_obj.save(update_fields=["is_delivered"])

                return Response({
                    "message": "Delivery Form created successfully",
                    "delivery_number": delivery_form.delivery_number,
                    "delivery_id": delivery_form.id
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def patch(self, request, did=None):
        if not did:
            return Response({"error": "Delivery ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1) Load and update the DeliveryForm itself
                delivery_form = get_object_or_404(DeliveryFormModel, id=did)
                delivery_form.delivery_date     = request.data.get("delivery_date", delivery_form.delivery_date)
                delivery_form.time              = request.data.get("time", delivery_form.time)
                delivery_form.delivery_location = request.data.get("delivery_location", delivery_form.delivery_location)
                delivery_form.delivery_address  = request.data.get("delivery_address", delivery_form.delivery_address)
                delivery_form.save()

                # 2) Build a lookup of SalesOrderItems by product_id
                sales_order = delivery_form.sales_order
                soi_map = {
                    soi.product_id: soi
                    for soi in SalesOrderItem.objects.filter(sales_order=sales_order)
                }

                # 3) Process each item in the payload
                items = request.data.get("items", [])
                if not items:
                    return Response({"error": "At least one item is required."}, status=status.HTTP_400_BAD_REQUEST)

                for item_data in items:
                    product_id = item_data.get("product")
                    if not product_id:
                        return Response({"error": "Each item must include a product ID."},
                                        status=status.HTTP_400_BAD_REQUEST)

                    # Lookup the existing DeliveryItem by product
                    di = get_object_or_404(
                        DeliveryItem,
                        delivery_form=delivery_form,
                        product_id=product_id
                    )

                    # Compute how much the delivered quantity has changed
                    old_qty = di.delivered_quantity
                    new_qty = Decimal(item_data.get("delivered_quantity", old_qty))
                    delta   = new_qty - old_qty

                    # check the new quantity is not more than the pending quantity + the old quantity
                    if new_qty > (soi_map.get(product_id).pending_quantity + old_qty):
                        raise ValueError(f"New quantity ({new_qty}) exceeds pending quantity ({soi_map.get(product_id).pending_quantity}) + old quantity ({old_qty}) for product {product_id} = {soi_map.get(product_id).pending_quantity + old_qty}")

                    # Update the DeliveryItem fields
                    di.delivered_quantity = new_qty
                    di.unit_price         = item_data.get("unit_price", di.unit_price)
                    di.sgst_percentage    = item_data.get("sgst_percentage", di.sgst_percentage)
                    di.cgst_percentage    = item_data.get("cgst_percentage", di.cgst_percentage)
                    di.save()

                    # 4) Apply delta to the corresponding SalesOrderItem
                    soi = soi_map.get(product_id)
                    if not soi:
                        raise ValueError(f"No SalesOrderItem for product ID {product_id}")

                    soi.pending_quantity -= delta
                    # check the delivery quantity is less than or equal to zero

                    if soi.pending_quantity <= 0:
                        soi.pending_quantity   = Decimal(0)
                        soi.is_item_delivered = True
                    else:
                        soi.is_item_delivered = False
                    soi.save(update_fields=["pending_quantity", "is_item_delivered"])

                # 5) Recalculate totals
                delivery_form.update_grand_total()

                
                # After updating the items, check if all items are delivered by querying the model
                all_items_delivered = not SalesOrderItem.objects.filter(sales_order=sales_order, is_item_delivered=False).exists()
                print(all_items_delivered)
                if all_items_delivered:
                    sales_order.is_delivered = True
                    sales_order.save(update_fields=["is_delivered"])
                else:
                    sales_order.is_delivered = False
                    sales_order.save(update_fields=["is_delivered"])

                return Response({
                    "status": "1",
                    "message": "Delivery updated successfully."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, did=None):
        if not did:
            return Response({"error": "Delivery ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1) Load the delivery form
                delivery_form = get_object_or_404(DeliveryFormModel, id=did)
                sales_order = delivery_form.sales_order

                # 2) For each delivery‐item, revert its effect on the SalesOrderItem
                for di in DeliveryItem.objects.filter(delivery_form=delivery_form):
                    # Find matching order line
                    soi = SalesOrderItem.objects.filter(
                        sales_order=sales_order,
                        product=di.product
                    ).first()

                    if soi:
                        # "Give back" the delivered quantity
                        soi.pending_quantity += di.delivered_quantity
                        # If after reverting there's still pending, mark it undelivered
                        soi.is_item_delivered = False
                        soi.save(update_fields=["pending_quantity", "is_item_delivered"])

                # 3) Now delete all the delivery’s items and the form itself
                delivery_form.items.all().delete()
                delivery_form.delete()

                # 4) Re‐evaluate the parent sales order’s delivery flag
                still_pending = SalesOrderItem.objects.filter(
                    sales_order=sales_order,
                    is_item_delivered=False
                ).exists()
                sales_order.is_delivered = not still_pending
                sales_order.save(update_fields=["is_delivered"])

                return Response({
                    "status": "1",
                    "message": "Delivery deleted and order quantities reverted successfully."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PrintDeliveryOrderAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, did=None):
        delivery = get_object_or_404(DeliveryFormModel, id=did)
        serializer = PrintDeliverySerializer(delivery)
        
        return Response({
            "status": "1",
            "message": "success",
            "data": [serializer.data]
        }, status=status.HTTP_200_OK)

class DeliveryOrderIsInvoiced(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request,sid=None):
        sales_order = get_object_or_404(SalesOrderModel, id=sid)
        deliveries = DeliveryFormModel.objects.filter(sales_order=sales_order, is_invoiced=False)

        # Get delivery forms linked to the sales order

        if not deliveries.exists():
            return Response({"status": "0", "message": "No deliveries found.", "data": []}, status=status.HTTP_200_OK)

        # Create a list to hold the sales order data
        data = []
        for deli in deliveries:
            data.append({
                "id": deli.id,
                "delivery_order_id": deli.delivery_number,
                "client_first_name": deli.customer.first_name,
                "client_last_name": deli.customer.last_name,
            })

        # Return the response with the data
        return Response({"status": "1", "data": data}, status=status.HTTP_200_OK)



from django.shortcuts import get_list_or_404

class DelivaryOrderItemsList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ids = request.query_params.get('ids')
        
        if not ids:
            return Response(
                {"status": "0", "message": "No delivery IDs provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            delivery_ids = [int(id.strip()) for id in ids.split(',')]
        except ValueError:
            return Response(
                {"status": "0", "message": "Invalid delivery ID format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        deliveries = DeliveryFormModel.objects.filter(id__in=delivery_ids)
        if not deliveries.exists():
            return Response(
                {"status": "0", "message": "No deliveries found."},
                status=status.HTTP_404_NOT_FOUND
            )

        result = []

        for delivery in deliveries:
            items = DeliveryItem.objects.filter(delivery_form=delivery)
            serialized_items = DeliveryItemsSerializer(items, many=True).data

            result.append({
                "delivery_id": delivery.id,
                "delivery_number": delivery.delivery_number,
                "grand_total": float(delivery.grand_total),
                "items": serialized_items
            })

        return Response({"status": "1", "data": result}, status=status.HTTP_200_OK)



class InvoiceOrderAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, ioid=None):
        if ioid:
            invoice = get_object_or_404(InvoiceModel, id=ioid)
            invoice_items = InvoiceItem.objects.filter(invoice=invoice)
            termsandconditions_points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=invoice.termsandconditions)
            termsandconditions_point_serializer = TermsAndConditionsPointSerializer(termsandconditions_points, many=True)

            # Get delivery forms linked to the invoice
            delivery_forms = DeliveryFormModel.objects.filter(
                id__in=invoice_items.values_list('delivary__id', flat=True)
            ).distinct()

            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).distinct()

            # Serialize invoice
            invoice_serializer = InvoiceModelSerializer(invoice)

            # Build the deliveries list with grouped items
            deliveries_data = []
            # mega_grand_total = Decimal("0.00")

            for delivery in delivery_forms:
                items = delivery_items.filter(delivery_form=delivery)
                item_serializer = DeliveryItemsSerializer(items, many=True)

                grand_total = delivery.grand_total or Decimal("0.00")
                # mega_grand_total += grand_total

                deliveries_data.append({
                    "delivery_id": delivery.id,
                    "delivery_number": delivery.delivery_number,
                    "grand_total": float(grand_total),
                    "items": item_serializer.data
                })

            return Response({
                "status": "1",
                "data": [{
                    **invoice_serializer.data,
                    # "mega_grand_total": float(mega_grand_total),
                    "termsandconditions_points": termsandconditions_point_serializer.data,
                    "deliveries": deliveries_data
                }]
            }, status=status.HTTP_200_OK)


        else:
            invoices = InvoiceModel.objects.filter(user=request.user).order_by("-created_at")
            serializer = InvoiceModelSerializer(invoices, many=True)
            return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)



    def post(self, request):
        data = request.data
        try:
            # Generate a random invoice ID
            # invoice_id = f"INV-{random.randint(111111, 999999)}"

            with transaction.atomic():
                # Required field extraction
                customer_id = data.get("client")
                terms_id = data.get("termsandconditions")
                sales_order_id = data.get("sales_order")
                invoice_date = data.get("invoice_date")
                delivery_ids = data.get("deliveries", [])  # Expecting a list

                if not customer_id:
                    return Response({"error": "Customer not provided."}, status=status.HTTP_400_BAD_REQUEST)
                if not terms_id:
                    return Response({"error": "Terms and conditions not provided."}, status=status.HTTP_400_BAD_REQUEST)
                if not sales_order_id:
                    return Response({"error": "Sales order not provided."}, status=status.HTTP_400_BAD_REQUEST)
                if not delivery_ids or not isinstance(delivery_ids, list):
                    return Response({"error": "Deliveries must be a list of IDs."}, status=status.HTTP_400_BAD_REQUEST)

                # check deliveries belong to same customer and sales order
                for delivery_id in delivery_ids:
                    delivery = get_object_or_404(DeliveryFormModel, id=delivery_id)
                    if delivery.customer.id != customer_id:
                        return Response({"error": f"Delivery {delivery.id} does not belong to the provided customer."}, status=status.HTTP_400_BAD_REQUEST)
                    if delivery.sales_order.id != sales_order_id:
                        return Response({"error": f"Delivery {delivery.id} does not belong to the provided sales order."}, status=status.HTTP_400_BAD_REQUEST)

                    # check the delivary is already invoiced or not
                deliveries = DeliveryFormModel.objects.filter(id__in=delivery_ids)
                if deliveries.count() != len(delivery_ids):
                    return Response({"error": "Some delivery IDs are invalid."}, status=status.HTTP_400_BAD_REQUEST)

                for delivery in deliveries:
                    if delivery.is_invoiced:
                        return Response({"error": f"Delivery {delivery.id} is already invoiced."}, status=status.HTTP_400_BAD_REQUEST)

                    # Fetch related models
                customer = get_object_or_404(Customer, id=customer_id)
                terms = get_object_or_404(TermsAndConditions, id=terms_id)
                sales_order = get_object_or_404(SalesOrderModel, id=sales_order_id)
                deliveries = DeliveryFormModel.objects.filter(id__in=delivery_ids)

                if deliveries.count() != len(delivery_ids):
                    return Response({"error": "Some delivery IDs are invalid."}, status=status.HTTP_400_BAD_REQUEST)
                
                invoice_grand_total_amount = Decimal("0.00")
                for delivery in deliveries:
                    invoice_grand_total_amount += delivery.grand_total

                # Create the invoice
                invoice_form = InvoiceModel.objects.create(
                    client=customer,
                    invoice_number=data.get("invoice_number"),
                    user=request.user,
                    sales_order=sales_order,
                    invoice_date=invoice_date,
                    invoice_grand_total=invoice_grand_total_amount,
                    termsandconditions=terms,
                    remark=data.get("remark", "")
                )

                # Create InvoiceItems and assign deliveries (M2M)
                for delivery in deliveries:
                    invoice_item = InvoiceItem.objects.create(invoice=invoice_form)
                    invoice_item.delivary.add(delivery)  # M2M assignment
                
                #updated is_invoiced field in DeliveryFormModel
                for delivery in deliveries:
                    delivery.is_invoiced = True
                    delivery.save()


                return Response({
                    "message": "Invoice created successfully",
                    "invoice_number": invoice_form.invoice_number,
                    "invoice_id": invoice_form.id
                }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def patch(self, request, ioid=None):
        if not ioid:
            return Response({"error": "Invoice ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        invoice = get_object_or_404(InvoiceModel, id=ioid)

        data = request.data
        new_client_id      = data.get("client",       invoice.client_id)
        new_sales_order_id = data.get("sales_order",  invoice.sales_order_id)
        new_delivery_ids   = data.get("deliveries",   None)  # only validate if present

        # 1) Validate client
        if "client" in data and not Customer.objects.filter(id=new_client_id).exists():
            return Response({"error": "Invalid client ID."}, status=status.HTTP_400_BAD_REQUEST)

        # 2) Validate sales_order
        if "sales_order" in data:
            if not SalesOrderModel.objects.filter(id=new_sales_order_id).exists():
                return Response({"error": "Invalid sales order ID."}, status=status.HTTP_400_BAD_REQUEST)
            # ensure the invoice.client matches the sales_order.customer
            so = SalesOrderModel.objects.get(id=new_sales_order_id)
            if so.customer_id != new_client_id:
                return Response({"error": "Sales order does not belong to the client."},
                                status=status.HTTP_400_BAD_REQUEST)

        # 3) Validate deliveries list if provided
        if new_delivery_ids is not None:
            if not isinstance(new_delivery_ids, list) or not new_delivery_ids:
                return Response({"error": "Deliveries must be a non-empty list of IDs."},
                                status=status.HTTP_400_BAD_REQUEST)

            # ensure each delivery exists, belongs to the client & sales_order, and is not already invoiced by another invoice
            for did in new_delivery_ids:
                delivery = DeliveryFormModel.objects.filter(id=did).first()
                if not delivery:
                    return Response({"error": f"Delivery {did} does not exist."},
                                    status=status.HTTP_400_BAD_REQUEST)
                if delivery.customer_id != new_client_id or delivery.sales_order_id != new_sales_order_id:
                    # print(delivery.customer_id, new_client_id, delivery.sales_order_id, new_sales_order_id)
                    return Response({"error": f"Delivery {did} mismatch client/sales order."},
                                    status=status.HTTP_400_BAD_REQUEST)
                # if it's already linked to THIS invoice, that's fine; if linked to another invoice, reject
                if delivery.is_invoiced and not invoice.items.filter(delivary=delivery).exists():
                    return Response({"error": f"Delivery {did} is already invoiced."},
                                    status=status.HTTP_400_BAD_REQUEST)




        # 4) Now perform the update
        serializer = InvoiceModelSerializer(invoice, data=data, partial=True)
        # update the invoice grand total
        # print(new_delivery_ids)

        if not serializer.is_valid():
            return Response({"status": "0", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()

        # 5) If deliveries were provided, replace M2M links
        if new_delivery_ids is not None:
            with transaction.atomic():
                # un‐invoice old deliveries we’re unlinking
                old_dids = invoice.items.values_list('delivary__id', flat=True)
                for old in old_dids:
                    if old not in new_delivery_ids:
                        d = DeliveryFormModel.objects.get(id=old)
                        d.is_invoiced = False
                        d.save(update_fields=["is_invoiced"])

                # drop existing join‐rows
                invoice.items.all().delete()

                # link new set and mark them invoiced
                for did in new_delivery_ids:
                    delivery = DeliveryFormModel.objects.get(id=did)
                    inv_item = InvoiceItem.objects.create(invoice=invoice)
                    inv_item.delivary.add(delivery)
                    delivery.is_invoiced = True
                    delivery.save(update_fields=["is_invoiced"])
        
        # 6) Recompute the invoice’s grand total
        total = Decimal("0.00")
        for inv_item in invoice.items.all():
            # each InvoiceItem has exactly one delivery in your design
            delivery = inv_item.delivary.first()
            if delivery and delivery.grand_total:
                total += delivery.grand_total

        invoice.invoice_grand_total = total
        invoice.save(update_fields=["invoice_grand_total"])

        # 7) Return updated invoice
        updated = InvoiceModelSerializer(invoice)
        return Response({"status": "1", "message": "Invoice updated successfully.",}, status=status.HTTP_200_OK)

    def delete(self, request, ioid=None):
        if not ioid:
            return Response({"error": "Invoice ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                invoice = get_object_or_404(InvoiceModel, id=ioid)

                # 1) Collect all linked deliveries
                linked_delivery_ids = invoice.items.values_list('delivary__id', flat=True)

                # 2) Revert their is_invoiced flags
                for did in linked_delivery_ids:
                    delivery = DeliveryFormModel.objects.get(id=did)
                    delivery.is_invoiced = False
                    delivery.save(update_fields=["is_invoiced"])

                # 3) Delete all InvoiceItem rows for this invoice
                invoice.items.all().delete()

                # 4) Finally delete the invoice itself
                invoice.delete()

                return Response({
                    "status": "1",
                    "message": "Invoice deleted and linked deliveries marked uninvoiced."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PrintInvoiceView(APIView):
    def get(self, request, ioid=None):
        invoice = get_object_or_404(InvoiceModel, id=ioid)
        invoice_items = InvoiceItem.objects.filter(invoice=invoice)

        # Get delivery forms linked to the invoice
        delivery_forms = DeliveryFormModel.objects.filter(
            id__in=invoice_items.values_list('delivary__id', flat=True)
        ).distinct()

        # Get all delivery items related to the delivery forms
        delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).distinct()

        # Initialize total
        # mega_grand_total = Decimal("0.00")
        items_data = []

        for delivery in delivery_forms:
            grand_total = delivery.grand_total or Decimal("0.00")
            # mega_grand_total += grand_total

        for item in delivery_items:
            item_data = PrintDeliveryItemsSerializer(item).data
            item_data.update({
                "delivary_number": item.delivery_form.delivery_number,
                "delivary_id": item.delivery_form.id,
            })
            items_data.append(item_data)

        invoice_serializer = PrintInvoiceSerializer(invoice)

        return Response({
            "status": "1",
            "data": [{
                **invoice_serializer.data,
                "items": items_data,
                # "mega_grand_total": float(mega_grand_total),
            }]
        }, status=status.HTTP_200_OK)



class InvoiceOrderIsReceipted(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, client_id=None):
        if not client_id:
            return Response(
                {"status": "0", "message": "Client ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        client = get_object_or_404(Customer, id=client_id)
        
        invoices = InvoiceModel.objects.filter(client=client, is_receipted=False).order_by('-created_at')

        if not invoices.exists():
            return Response(
                {"status": "0", "message": "No invoices found for this client.", "data": []},
                status=status.HTTP_200_OK
            )
        
        serialized_data = InvoiceModelSerializer(invoices, many=True).data

        return Response(
            {"status": "1", "data": serialized_data},
            status=status.HTTP_200_OK
        )

class ReceiptView(APIView):
    def get(self, request, rec_id=None):
        if rec_id:
            receipt = get_object_or_404(ReceiptModel, id=rec_id)
            termsandconditions_points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=receipt.termsandconditions_id)
            invoice_items = InvoiceItem.objects.filter(invoice=receipt.invoice_id)
            items = DeliveryItem.objects.filter(delivery_form__in=invoice_items.values_list('delivary__id', flat=True)).distinct()

            serializer = ReceiptSerializer(receipt)
            return Response({
                'Status': '1',
                'Message': 'Success',
                'Data': [{
                    **serializer.data,
                    'termsandconditions_points': TermsAndConditionsPointSerializer(termsandconditions_points, many=True).data,
                    'items': DeliveryItemsSerializer(items, many=True).data
                }]
            })
        else:
            receipts = ReceiptModel.objects.filter(user=request.user).order_by('-created_at')
            serializer = ReceiptSerializer(receipts, many=True)
        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': serializer.data
        })
    
    def post(self, request):
        serializer = ReceiptSerializer(data=request.data)
        if serializer.is_valid():
            invoice = get_object_or_404(InvoiceModel, id=request.data['invoice'])
            invoice.is_receipted = True
            invoice.save(update_fields=['is_receipted'])
            serializer.save(user=request.user)
            return Response(
                {
                    "status": "1",
                    "message": "Receipt created successfully.",
                    "receipt_number": serializer.data['receipt_number'],
                    "receipt_id": serializer.data['id'],

                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, rec_id=None):
        receipt = get_object_or_404(ReceiptModel, id=rec_id)
        old_invoice = receipt.invoice

        serializer = ReceiptSerializer(receipt, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_invoice_id = request.data.get('invoice')
        if new_invoice_id and new_invoice_id != old_invoice.id:
            # 3) If user is reassigning the receipt to a different invoice:
            #    a) Un-mark the old invoice
            old_invoice.is_receipted = False
            old_invoice.save(update_fields=['is_receipted'])
            #    b) Mark the new invoice
            new_invoice = get_object_or_404(InvoiceModel, id=new_invoice_id)
            new_invoice.is_receipted = True
            new_invoice.save(update_fields=['is_receipted'])

        else:
            # 4) If invoice stayed the same (or wasn't provided), ensure it's marked
            old_invoice.is_receipted = True
            old_invoice.save(update_fields=['is_receipted'])

        # 5) Save the updated receipt
        serializer.save()
        return Response({
            "status": "1",
            "message": "Receipt updated successfully."
        }, status=status.HTTP_200_OK)

    def delete(self, request, rec_id=None):
        if not rec_id:
            return Response({"error": "Receipt ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                receipt = get_object_or_404(ReceiptModel, id=rec_id)
                invoice = receipt.invoice

                # 1) Delete the receipt
                receipt.delete()

                # 2) Mark the invoice as not receipted
                invoice.is_receipted = False
                invoice.save(update_fields=["is_receipted"])

                return Response({
                    "status": "1",
                    "message": "Receipt deleted and invoice marked un-receipted."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class PrintReceiptView(APIView):
    def get(self, request, rec_id=None):
        receipt = get_object_or_404(ReceiptModel, id=rec_id)
        invoice_items = InvoiceItem.objects.filter(invoice=receipt.invoice_id)
        items = DeliveryItem.objects.filter(delivery_form__in=invoice_items.values_list('delivary__id', flat=True)).distinct()
        # Initialize total
        items_data = []        

        for item in items:
            item_data = PrintDeliveryItemsSerializer(item).data
            item_data.update({
                "delivary_number": item.delivery_form.delivery_number,
                "delivary_id": item.delivery_form.id,
            })
            items_data.append(item_data)

        serializer = PrintReceiptSerializer(receipt)
        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': [{
                **serializer.data,
                'items': items_data,
            }]
        })


class OrderNumberGeneratorView(APIView):
    def generate_next_number(self, model, field_name: str, prefix: str, length: int) -> str:
        start = 10**(length - 1) + 1  # e.g., for length 6 -> 100001

        # Filter by prefix and order descending to get the latest number
        latest_order = model.objects.filter(**{f"{field_name}__startswith": f"{prefix}|"}).order_by(f"-{field_name}").first()

        if latest_order:
            latest_number_str = getattr(latest_order, field_name).split('|')[1]
            next_number = int(latest_number_str) + 1
        else:
            next_number = start  # Start from e.g., 100001

        return f"{prefix}|{next_number:0{length}d}"

    def get(self, request):
        order_type = request.query_params.get('type')

        if order_type == "QU":
            order_number = self.generate_next_number(QuotationOrderModel, "quotation_number", "QU", 6)
        elif order_type == "SO":
            order_number = self.generate_next_number(SalesOrderModel, "sales_order_number", "SO", 6)
        elif order_type == "DO":
            order_number = self.generate_next_number(DeliveryFormModel, "delivery_number", "DO", 6)
        elif order_type == "INV":
            order_number = self.generate_next_number(InvoiceModel, "invoice_number", "INV", 6)
        elif order_type == "RP":
            order_number = self.generate_next_number(ReceiptModel, "receipt_number", "RP", 6)
        elif order_type == "SU":
            order_number = self.generate_next_number(Supplier, "supplier_number", "SU", 6)
        elif order_type == "PO":
            order_number = self.generate_next_number(PurchaseOrder, "purchase_order_number", "PO", 6)
        elif order_type == "MR":
            order_number = self.generate_next_number(MaterialReceive, "material_receive_number", "MR", 6)
        else:
            return Response({
                'status': '0',
                'message': 'Invalid order type.',
                'order_number': None
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': '1',
            'message': 'Success',
            'order_number': order_number
        }, status=status.HTTP_200_OK)






 # Report Views

 # Sales Report by Client (Invoice)



class SalesReportByClientView(APIView):

    def get(self, request):
        client_id = request.GET.get('client')
        from_date = parse_date(request.GET.get('from_date'))
        to_date = parse_date(request.GET.get('to_date'))
        sales_by_type = request.GET.get('type')

        # check the dates are valid 
        error_response = self._validate_inputs(client_id, from_date, to_date, sales_by_type)
        if error_response:
            return error_response

        if sales_by_type == 'INV':
            return self._get_invoice_data(client_id, from_date, to_date)

        elif sales_by_type == 'DO':
            return self._get_delivery_data(client_id, from_date, to_date)

        return Response({
            'Status': '0',
            'Message': 'Invalid sales type.',
            'Data': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _validate_inputs(self, client_id, from_date, to_date, sales_by_type):
        if not from_date or not to_date:
            return Response({
                'Status': '0',
                'Message': 'Both from_date and to_date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range. from_date must be before or equal to to_date.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if sales_by_type not in ['INV', 'DO']:
            return Response({
                'Status': '0',
                'Message': 'Invalid sales type. Use "INV" for invoices or "DO" for deliveries.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if client_id != 'all' and not Customer.objects.filter(id=client_id).exists():
            return Response({
                'Status': '0',
                'Message': 'Invalid client ID.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return None



    def _get_invoice_data(self, client_id, from_date, to_date):
        invoices = InvoiceModel.objects.filter(invoice_date__range=[from_date, to_date])
        if client_id != 'all':
            invoices = invoices.filter(client_id=client_id)

        invoices = invoices.select_related('sales_order')

        all_items_data = []

        # Prefetch delivary in InvoiceItem and DeliveryItem in one go
        invoice_items = InvoiceItem.objects.filter(invoice__in=invoices).prefetch_related('delivary')

        # Gather all the delivery IDs
        delivery_ids = invoice_items.values_list('delivary__id', flat=True)

        # Now, filter all delivery items that match the delivery_form IDs in the delivery_ids list
        delivery_items = DeliveryItem.objects.filter(delivery_form_id__in=delivery_ids).select_related('delivery_form')

        # For each invoice, find the related delivery items
        for invoice in invoices:
            # Instead of filtering again, directly iterate over the pre-fetched items
            items = delivery_items.filter(delivery_form__invoiceitem__invoice=invoice)

            for item in items:
                item_data = DeliveryItemsSerializer(item).data
                item_data.update({
                    "delivary_number": item.delivery_form.delivery_number,
                    "delivary_id": item.delivery_form.id,
                    "invoice_number": invoice.invoice_number,
                    "sales_order_number": invoice.sales_order.sales_order_number,
                    "sales_order_id": invoice.sales_order.id,
                    "is_invoiced": item.delivery_form.is_invoiced,
                    "client_id": invoice.client_id,
                    "invoice_date": invoice.invoice_date,
                    "delivery_date": item.delivery_form.delivery_date
                })
                all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })


    def _get_delivery_data(self, client_id, from_date, to_date):
        deliveries = DeliveryFormModel.objects.filter(delivery_date__range=[from_date, to_date])
        if client_id != 'all':
            deliveries = deliveries.filter(customer_id=client_id)

        deliveries = deliveries.select_related('sales_order')

        all_items_data = []

        delivery_items = DeliveryItem.objects.filter(delivery_form__in=deliveries).select_related('delivery_form')

        for item in delivery_items:
            delivery_form = item.delivery_form
            item_data = DeliveryItemsSerializer(item).data
            item_data.update({
                "delivary_number": delivery_form.delivery_number,
                "delivary_date": delivery_form.delivery_date,
                "sales_order_number": delivery_form.sales_order.sales_order_number,
                "sales_order_id": delivery_form.sales_order.id,
                "is_invoiced": delivery_form.is_invoiced,
                "client_id": delivery_form.customer_id,
            })
            all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })



class SalesReportByItemsView(APIView):

    def get(self, request):
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        sales_by_type = request.GET.get('type')
        item = request.GET.get('item')
        client = request.GET.get('client')

        # Validate inputs
        validation_result = self._validate_inputs(from_date_str, to_date_str, sales_by_type, client,item)
        if isinstance(validation_result, Response):
            return validation_result

        from_date, to_date = validation_result

        if sales_by_type == 'INV':
            return self._get_invoice_data(from_date, to_date, item, client)
        elif sales_by_type == 'DO':
            return self._get_delivery_data(from_date, to_date, item, client)

        return Response({
            'Status': '0',
            'Message': 'Invalid sales type.',
            'Data': []
        }, status=status.HTTP_400_BAD_REQUEST)

    def _validate_inputs(self, from_date_str, to_date_str, sales_by_type, client_id,item):
        if not from_date_str or not to_date_str:
            return Response({
                'Status': '0',
                'Message': 'Both from_date and to_date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range. from_date must be before or equal to to_date.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if sales_by_type not in ['INV', 'DO']:
            return Response({
                'Status': '0',
                'Message': 'Invalid sales type. Use "INV" or "DO".'
            }, status=status.HTTP_400_BAD_REQUEST)

        if client_id != 'all' and not Customer.objects.filter(id=client_id).exists():
            return Response({
                'Status': '0',
                'Message': 'Invalid client ID.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if item != 'all' and not Product.objects.filter(id=item).exists():
            return Response({
                'Status': '0',
                'Message': 'Invalid item ID.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return from_date, to_date

    
    def _get_invoice_data(self, from_date, to_date, item, client):
        invoices = InvoiceModel.objects.filter(invoice_date__range=[from_date, to_date])

        if client != 'all':
            invoices = invoices.filter(client_id=client)

        invoice_items = InvoiceItem.objects.filter(invoice__in=invoices).prefetch_related('delivary')

        # Get all related delivery forms
        delivery_forms = set()
        for inv_item in invoice_items:
            delivery_forms.update(inv_item.delivary.all())

        if item != 'all':
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms, product=item).select_related('delivery_form')
        else:
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).select_related('delivery_form')

        all_items_data = []

        for delivery_item in delivery_items:
            delivery_form = delivery_item.delivery_form
            invoice = invoices.filter(sales_order=delivery_form.sales_order).first()

            if invoice:
                item_data = DeliveryItemsSerializer(delivery_item).data
                item_data.update({
                    "delivary_number": delivery_form.delivery_number,
                    "delivary_id": delivery_form.id,
                    "invoice_number": invoice.invoice_number,
                    "sales_order_number": invoice.sales_order.sales_order_number,
                    "sales_order_id": invoice.sales_order.id,
                    "is_invoiced": delivery_form.is_invoiced,
                    "client_id": invoice.client_id,
                    "client_name": invoice.client.first_name + ' ' + invoice.client.last_name,
                    "invoice_date": invoice.invoice_date,
                    "delivery_date": delivery_form.delivery_date
                })
                all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })
    
    def _get_delivery_data(self, from_date, to_date, item, client):
        delivery_forms = DeliveryFormModel.objects.filter(delivery_date__range=[from_date, to_date])

        if client != 'all':
            delivery_forms = delivery_forms.filter(customer_id=client)

        if item != 'all':
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms, product=item).select_related('delivery_form')
        else:
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).select_related('delivery_form')

        all_items_data = []
        for delivery_item in delivery_items:
            delivery_form = delivery_item.delivery_form
            invoice = InvoiceModel.objects.filter(sales_order=delivery_form.sales_order).first()

            item_data = DeliveryItemsSerializer(delivery_item).data
            item_data.update({
                "delivary_number": delivery_form.delivery_number,
                "delivary_id": delivery_form.id,
                "sales_order_number": delivery_form.sales_order.sales_order_number,
                "sales_order_id": delivery_form.sales_order.id,
                "is_invoiced": delivery_form.is_invoiced,
                "client_name": delivery_form.customer.first_name + ' ' + delivery_form.customer.last_name,
                "client_id": delivery_form.customer_id,
                "delivery_date": delivery_form.delivery_date
            })
            all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })
    

class SalesReportBySalespersonView(APIView):
    def get(self, request,):
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        sales_by_type = request.GET.get('type')
        salesperson = request.GET.get('salesperson')
        item = request.GET.get('item')

        # Validate inputs
        validation_result = self._validate_inputs(from_date_str, to_date_str, sales_by_type, salesperson,item)
        if isinstance(validation_result, Response):
            return validation_result

        from_date, to_date = validation_result

        if sales_by_type == 'INV':
            return self._get_invoice_data(from_date, to_date, item, salesperson)
        elif sales_by_type == 'DO':
            return self._get_delivery_data(from_date, to_date, item, salesperson)



        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': []
        })
    
    def _validate_inputs(self, from_date_str, to_date_str, sales_by_type, salesperson,item):
        if not from_date_str or not to_date_str:
            return Response({
                'Status': '0',
                'Message': 'Both from_date and to_date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range. from_date must be before or equal to to_date.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if sales_by_type not in ['INV', 'DO']:
            return Response({
                'Status': '0',
                'Message': 'Invalid sales type. Use "INV" or "DO".'
            }, status=status.HTTP_400_BAD_REQUEST)

        if salesperson != 'all' and not SalesPerson.objects.filter(id=salesperson).exists():
            return Response({
                'Status': '0',
                'Message': 'Invalid salesperson ID.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if item != 'all' and not Product.objects.filter(id=item).exists():
            return Response({
                'Status': '0',
                'Message': 'Invalid item ID.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return from_date, to_date
        
    
    def _get_invoice_data(self, from_date, to_date, item, salesperson):
        invoices = InvoiceModel.objects.filter(invoice_date__range=[from_date, to_date])

        if salesperson != 'all':
            invoices = invoices.filter(client__salesperson=salesperson)
            print(invoices)

        invoice_items = InvoiceItem.objects.filter(invoice__in=invoices).prefetch_related('delivary')

        # Get all related delivery forms
        delivery_forms = set()
        for inv_item in invoice_items:
            delivery_forms.update(inv_item.delivary.all())

        if item != 'all':
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms, product=item).select_related('delivery_form')
        else:
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).select_related('delivery_form')

        all_items_data = []

        for delivery_item in delivery_items:
            delivery_form = delivery_item.delivery_form
            invoice = invoices.filter(sales_order=delivery_form.sales_order).first()

            if invoice:
                item_data = DeliveryItemsSerializer(delivery_item).data
                item_data.update({
                    "delivary_number": delivery_form.delivery_number,
                    "delivary_id": delivery_form.id,
                    "invoice_number": invoice.invoice_number,
                    "sales_order_number": invoice.sales_order.sales_order_number,
                    "sales_order_id": invoice.sales_order.id,
                    "is_invoiced": delivery_form.is_invoiced,
                    "client_id": invoice.client_id,
                    "client_name": invoice.client.first_name + ' ' + invoice.client.last_name,
                    "salesperson": invoice.client.salesperson.id,
                    "salesperson_name": invoice.client.salesperson.first_name + ' ' + invoice.client.salesperson.last_name,
                    "invoice_date": invoice.invoice_date,
                    "delivery_date": delivery_form.delivery_date
                })
                all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })
    
    def _get_delivery_data(self, from_date, to_date, item, salesperson):
        delivery_forms = DeliveryFormModel.objects.filter(delivery_date__range=[from_date, to_date])

        if salesperson != 'all':
            delivery_forms = delivery_forms.filter(client__salesperson=salesperson)
        if item != 'all':
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms, product=item).select_related('delivery_form')
        else:
            delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).select_related('delivery_form')

        all_items_data = []
        for delivery_item in delivery_items:
            delivery_form = delivery_item.delivery_form
            invoice = InvoiceModel.objects.filter(sales_order=delivery_form.sales_order).first()

            item_data = DeliveryItemsSerializer(delivery_item).data
            item_data.update({
                "delivary_number": delivery_form.delivery_number,
                "delivary_id": delivery_form.id,
                "sales_order_number": delivery_form.sales_order.sales_order_number,
                "sales_order_id": delivery_form.sales_order.id,
                "is_invoiced": delivery_form.is_invoiced,
                "client_name": delivery_form.customer.first_name + ' ' + delivery_form.customer.last_name,
                "client_id": delivery_form.customer_id,
                "delivery_date": delivery_form.delivery_date
            })
            all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })
    

class SalesReportByCategoryView(APIView):
    def get(self, request):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        sales_by_type = request.GET.get('type')
        category = request.GET.get('category')
        item = request.GET.get('item')

        # Validate inputs
        validation_result = self._validate_inputs(from_date, to_date, sales_by_type, category, item)
        if isinstance(validation_result, Response):
            return validation_result

        from_date, to_date = validation_result

        if sales_by_type == 'INV':
            return self._get_invoice_data(from_date, to_date, category, item)
        elif sales_by_type == 'DO':
            return self._get_delivery_data(from_date, to_date, category, item)
        
        return Response({
            'Status': '0',
            'Message': 'Invalid sales type.',
            'Data': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _validate_inputs(self, from_date_str, to_date_str, sales_by_type, category, item):
        if not from_date_str or not to_date_str:
            return Response({
                'Status': '0',
                'Message': 'Both from_date and to_date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range. from_date must be before or equal to to_date.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if sales_by_type not in ['INV', 'DO']:
            return Response({
                'Status': '0',
                'Message': 'Invalid sales type. Use "INV" or "DO".'
            }, status=status.HTTP_400_BAD_REQUEST)

        if item != 'all' and not Product.objects.filter(id=item).exists():
            return Response({
                'Status': '0',
                'Message': 'Invalid item ID.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if category != 'all' and (not category.isdigit() or not Category.objects.filter(id=category).exists()):
            return Response({
                'Status': '0',
                'Message': 'Invalid category ID.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the product belongs to the selected category
        if item != 'all' and category != 'all':
            product = Product.objects.get(id=item)
            if product.category_id != int(category):
                return Response({
                    'Status': '0',
                    'Message': 'The product does not belong to the specified category.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        return from_date, to_date    

    def _get_invoice_data(self, from_date, to_date, category, item):
        invoices = InvoiceModel.objects.filter(invoice_date__range=[from_date, to_date])

        invoice_items = InvoiceItem.objects.filter(invoice__in=invoices).prefetch_related('delivary')

        # Gather all delivery forms linked to invoice items
        delivery_forms = set()
        for inv_item in invoice_items:
            delivery_forms.update(inv_item.delivary.all())

        # Build base delivery item queryset
        delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms).prefetch_related('delivery_form__sales_order')

        if item != 'all':
            delivery_items = delivery_items.filter(product_id=item)

        if category != 'all':
            delivery_items = delivery_items.filter(product__category_id=category)

        all_items_data = []

        for delivery_item in delivery_items:
            delivery_form = delivery_item.delivery_form
            invoice = invoices.filter(sales_order=delivery_form.sales_order).first()

            if invoice:
                item_data = DeliveryItemsSerializer(delivery_item).data
                item_data.update({
                    "delivary_number": delivery_form.delivery_number,
                    "delivary_id": delivery_form.id,
                    "invoice_number": invoice.invoice_number,
                    "sales_order_number": invoice.sales_order.sales_order_number,
                    "sales_order_id": invoice.sales_order.id,
                    "is_invoiced": delivery_form.is_invoiced,
                    "invoice_date": invoice.invoice_date,
                    "delivery_date": delivery_form.delivery_date,
                    "catagry": delivery_item.product.category.name,
                    "catagry_id": delivery_item.product.category.id
                })
                all_items_data.append(item_data)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': all_items_data
        })
    
    def _get_delivery_data(self, from_date, to_date, category, item):
            delivery_forms = DeliveryFormModel.objects.filter(delivery_date__range=[from_date, to_date])

            # Clean item check - make sure to convert to int properly
            if item not in [None, '', 'all']:
                try:
                    item_id = int(item)
                    delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms, product_id=item_id)
                except (ValueError, TypeError):
                    delivery_items = DeliveryItem.objects.none()
            else:
                delivery_items = DeliveryItem.objects.filter(delivery_form__in=delivery_forms)

            # Apply category filter correctly
            if category not in [None, '', 'all']:
                delivery_items = delivery_items.filter(product__category=category)

            all_items_data = []
            for delivery_item in delivery_items:
                delivery_form = delivery_item.delivery_form
                invoice = InvoiceModel.objects.filter(sales_order=delivery_form.sales_order).first()

                item_data = DeliveryItemsSerializer(delivery_item).data
                item_data.update({
                    "delivary_number": delivery_form.delivery_number,
                    "delivary_id": delivery_form.id,
                    "sales_order_number": delivery_form.sales_order.sales_order_number,
                    "sales_order_id": delivery_form.sales_order.id,
                    "is_invoiced": delivery_form.is_invoiced,
                    "client_name": f"{delivery_form.customer.first_name} {delivery_form.customer.last_name}",
                    "client_id": delivery_form.customer_id,
                    "delivery_date": delivery_form.delivery_date,
                    "catagry": delivery_item.product.category.name,
                    "catagry_id": delivery_item.product.category.id
                })
                all_items_data.append(item_data)

            return Response({
                'Status': '1',
                'Message': 'Success',
                'Data': all_items_data
            })

    




class CountryView(APIView):
    def get(self, request):
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': serializer.data
        })


class StateView(APIView):
    def get(self, request):
        country_name = request.GET.get('country')
        country = get_object_or_404(Country, name__iexact=country_name)
        states = State.objects.filter(country=country)
        serializer = CountrySerializer(states, many=True)
        return Response({
            'Status': '1',
            'Message': 'Success',
            'Data': serializer.data
        })
            
class CustomerListCreateAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            customer = get_object_or_404(Customer, pk=pk)
            serializer = CustomerSerializer(customer)
            response_data = {
                "Status": "1",
                "message": "Success",
                "Data": [serializer.data]  # Returning data inside an array
            }
        else:
            customers = Customer.objects.all()
            serializer = CustomerSerializer(customers, many=True)
            response_data = {
                "Status": "1",
                "message": "Success",
                "Data": serializer.data  # Returning list of customers
            }
        
        return Response(response_data, status=status.HTTP_200_OK)

    # POST - Create a new customer
    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = {
                "Status": "1",
                "message": "Customer created successfully.",
                "Data": [serializer.data]
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response({"Status": "0", "message": "Error", "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # PATCH - Update customer (Partial Update)
    def patch(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        serializer = CustomerSerializer(customer, data=request.data, partial=True)  # Partial update
        if serializer.is_valid():
            serializer.save()
            response_data = {
                "Status": "1",
                "message": "Customer updated successfully.",
                "Data": [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response({"Status": "0", "message": "Error", "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # DELETE - Delete a customer
    def delete(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        customer.delete()
        return Response({"Status": "1", "message": "Customer deleted successfully."},status=status.HTTP_200_OK)


class CategoryListCreateAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(Category, pk=pk)
            serializer = CategorySerializer(category)
            response_data = {
                "Status": "1",
                "message": "Success",
                "Data": [serializer.data]  # Returning data inside an array
            }
        else:
            categories = Category.objects.all()
            serializer = CategorySerializer(categories, many=True)
            response_data = {
                "Status": "1",
                "message": "Success",
                "Data": serializer.data  # Returning list of categories
            }
        
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = {
                "Status": "1",
                "message": "Category created successfully.",
                "Data": [serializer.data]
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response({"Status": "0", "message": "Error", "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)  # Partial update
        if serializer.is_valid():
            serializer.save()
            response_data = {
                "Status": "1",
                "message": "Category updated successfully.",
                "Data": [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response({"Status": "0", "message": "Error", "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return Response({"Status": "1", "message": "Category deleted successfully."}, status=status.HTTP_200_OK)
    

class UnitAPIView(APIView):
    # GET - Retrieve all units or a specific unit by ID
    def get(self, request, pk=None):
        if pk:
            unit = get_object_or_404(Unit, pk=pk)
            serializer = UnitSerializer(unit)
            response_data = {
                "Status": "1",
                "message": "Success",
                "Data": [serializer.data]
            }
        else:
            units = Unit.objects.all()
            serializer = UnitSerializer(units, many=True)
            response_data = {
                "Status": "1",
                "message": "Units fetched successfully.",
                "Data": serializer.data
            }
        return Response(response_data, status=status.HTTP_200_OK)

    # POST - Create a new unit
    def post(self, request):
        serializer = UnitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = {
                "Status": "1",
                "message": "Unit created successfully.",
                "Data": [serializer.data]
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response({"Status": "0", "message": "Error", "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # PATCH - Update a unit (partial update)
    def patch(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        serializer = UnitSerializer(unit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"Status": "1", "message": "Unit updated successfully.", "Data": [serializer.data]})
        return Response({"Status": "0", "message": "Error", "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # DELETE - Delete a unit
    def delete(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        unit.delete()
        return Response({"Status": "1", "message": "Unit deleted successfully."}, status=status.HTTP_200_OK)
    

class BankAccountAPI(APIView):

    def get(self, request, account_id=None):
        """Fetch a single or all bank accounts."""
        if account_id:
            bank_account = get_object_or_404(BankAccount, id=account_id)
            serializer = BankAccountSerializer(bank_account)
            return Response({"status": "1", "message": "success", "data": [serializer.data]}, status=status.HTTP_200_OK)
        
        bank_accounts = BankAccount.objects.all()
        serializer = BankAccountSerializer(bank_accounts, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new bank account."""
        serializer = BankAccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Bank account added successfully", "data": [serializer.data]}, status=status.HTTP_201_CREATED)
        return Response({"status": "0", "message": "Validation error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, account_id):
        """Update a bank account."""
        bank_account = get_object_or_404(BankAccount, id=account_id)
        serializer = BankAccountSerializer(bank_account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Bank account updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"status": "0", "message": "Validation error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, account_id):
        """Delete a bank account."""
        bank_account = get_object_or_404(BankAccount, id=account_id)
        bank_account.delete()
        return Response({"status": "1", "message": "Bank account deleted successfully"}, status=status.HTTP_200_OK)    


class TermsAndConditionsAPI(APIView):
    def get(self, request, pk=None):
        if pk:
            term = get_object_or_404(TermsAndConditions, pk=pk)
            serializer = TermsAndConditionsSerializer(term)
            return Response({"status": "1", "data": [serializer.data]})
        else:
            terms = TermsAndConditions.objects.all()
            serializer = TermsAndConditionsSerializer(terms, many=True)
            return Response({"status": "1", "data": serializer.data})

    def post(self, request):
        serializer = TermsAndConditionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Term created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"status": "0", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        term = get_object_or_404(TermsAndConditions, pk=pk)
        serializer = TermsAndConditionsSerializer(term, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Term updated successfully", "data": serializer.data})
        return Response({"status": "0", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        term = get_object_or_404(TermsAndConditions, pk=pk)
        term.delete()
        return Response({"status": "1", "message": "Term deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class TermsAndConditionsPointAPI(APIView):
    def get(self, request, pk=None):
        if pk:
            point = get_object_or_404( TermsAndConditionsPoint, pk=pk)
            serializer = TermsAndConditionsPointSerializer(point)
            return Response({"status": "1", "data": [serializer.data]})
        else:
            points = TermsAndConditionsPoint.objects.all()
            serializer = TermsAndConditionsPointSerializer(points, many=True)
            return Response({"status": "1", "data": serializer.data})

    def post(self, request):
        serializer = TermsAndConditionsPointSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Point created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"status": "0", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        point = get_object_or_404(TermsAndConditionsPoint, pk=pk)
        serializer = TermsAndConditionsPointSerializer(point, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Point updated successfully", "data": serializer.data})
        return Response({"status": "0", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        point = get_object_or_404(TermsAndConditionsPoint, pk=pk)
        point.delete()
        return Response({"status": "1", "message": "Point deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class ListTermsandConditionsPointsAPI(APIView):
    def get(self, request, term_id=None):
        if term_id is None:
            return Response({"status": "0", "message": "Invalid Term ID"}, status=status.HTTP_400_BAD_REQUEST)

        if not TermsAndConditions.objects.filter(pk=term_id).exists():
            return Response({"status": "0", "message": "Term ID not found"}, status=status.HTTP_404_NOT_FOUND)

        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions_id=term_id)
        serializer = TermsAndConditionsPointSerializer(points, many=True)
        
        return Response({"status": "1", "data": serializer.data})




# class PurchaseOrderAPIView(APIView):
#     def get(self, request, purchase_order_id=None):
#         if purchase_order_id:
#             purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
#             serializer = PurchaseOrderSerializer(purchase_order)
#             return Response({"status": "1", "data": [serializer.data]})
#         purchase_orders = PurchaseOrder.objects.all()
#         serializer = PurchaseOrderSerializer(purchase_orders, many=True)
#         return Response({"status": "1", "data": serializer.data})
    
#     def post(self, request):
#         serializer = PurchaseOrderSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"status": "1", "message": "Purchase order created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
#         return Response({"status": "0", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk=None, format=None):
        if pk:
            try:
                purchase_order = PurchaseOrder.objects.get(pk=pk)
                serializer = PurchaseOrderSerializer(purchase_order)
                return Response({"status": "1", "message": "success", "data": [serializer.data]})
            except PurchaseOrder.DoesNotExist:
                return Response(
                    {"error": "Purchase order not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            purchase_orders = PurchaseOrder.objects.all().order_by('-id')

            supplier = request.query_params.get('supplier')
            if supplier:
                purchase_orders = purchase_orders.filter(supplier_id=supplier)

            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date and end_date:
                purchase_orders = purchase_orders.filter(
                    purchase_order_date__gte=start_date,
                    purchase_order_date__lte=end_date
                )

            serializer = PurchaseOrderListSerializer(purchase_orders, many=True)
            return Response({"status": "1", "message": "success", "data": serializer.data})

    def post(self, request, format=None):
        serializer = PurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, format=None):
        try:
            purchase_order = PurchaseOrder.objects.get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PurchaseOrderSerializer(
            purchase_order, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        try:
            purchase_order = PurchaseOrder.objects.get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        purchase_order.delete()
        return Response(
            {"message": "Purchase order deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )




class MaterialReceiveAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk=None, format=None):
        if pk:
            try:
                material_receive = MaterialReceive.objects.get(pk=pk)
                serializer = MaterialReceiveSerializer(material_receive)
                return Response({"status": "1", "message": "success", "data": [serializer.data]})
            except MaterialReceive.DoesNotExist:
                return Response(
                    {"error": "Material Receive order not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            material_receives = MaterialReceive.objects.all().order_by('-id')

            supplier = request.query_params.get('supplier')
            if supplier:
                material_receives = material_receives.filter(supplier_id=supplier)

            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date and end_date:
                material_receives = material_receives.filter(
                    material_receive_date__gte=start_date,
                    material_receive_date__lte=end_date
                )

            serializer = MaterialReceiveListSerializer(material_receives, many=True)
            return Response({"status": "1", "message": "success", "data": serializer.data})

    def post(self, request, format=None):
        serializer = MaterialReceiveSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, format=None):
        try:
            material_receive = MaterialReceive.objects.get(pk=pk)
        except MaterialReceive.DoesNotExist:
            return Response(
                {"error": "Material Receive order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MaterialReceiveSerializer(
            material_receive, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        try:
            material_receive = MaterialReceive.objects.get(pk=pk)
        except MaterialReceive.DoesNotExist:
            return Response(
                {"error": "Material Receive order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        material_receive.delete()
        return Response(
            {"message": "Material Receive order deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )





class ContractListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'contracts'
    def get(self, request, contract_id=None):
        if contract_id:
            contract = get_object_or_404(Contract, id=contract_id, is_template=True)
            serializer = ContractSerializer(contract)
            return Response({"status": "1", "message": "success", "data": [serializer.data]})
        contracts = Contract.objects.filter(is_template=True)
        serializer = ContractSerializer(contracts, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def post(self, request, contract_id=None):
        serializer = ContractSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(is_template=True)
            return Response({"status": "1", "message": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
    def patch(self, request, contract_id):
        contract = get_object_or_404(Contract, id=contract_id, is_template=True)
        serializer = ContractSerializer(contract, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": [serializer.data]})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, contract_id):
        contract = get_object_or_404(Contract, id=contract_id, is_template=True)
        contract.delete()
        return Response({"status": "1", "message": "Contract Deleted Succesfully"}, status=status.HTTP_204_NO_CONTENT)


class ContractDetailViewApiView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contract_id):
        contract = get_object_or_404(Contract, id=contract_id, is_template=True)
        serializer = ContractDetailSerializer(contract)
        return Response({"status": "1", "message": "success", "data": [serializer.data]})
    


# Section
class ContractSectionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, contract_id, section_id=None):
        if section_id:
            section = get_object_or_404(ContractSection, contract_id=contract_id, id=section_id)
            serializer = ContractSectionSerializer(section)
            return Response({"status": "1", "message": "success", "data": [serializer.data]})
        sections = ContractSection.objects.filter(contract_id=contract_id)
        serializer = ContractSectionSerializer(sections, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def post(self, request, contract_id, section_id=None):
        data = request.data.copy()
        data['contract'] = contract_id
        serializer = ContractSectionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": [serializer.data]}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def patch(self, request, contract_id, section_id):
        section = get_object_or_404(ContractSection, contract_id=contract_id, id=section_id)
        serializer = ContractSectionSerializer(section, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": [serializer.data]})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, contract_id, section_id):
        section = get_object_or_404(ContractSection, contract_id=contract_id, id=section_id)
        section.delete()
        return Response({"status": "1", "message": "Section Deleted Succesfully"}, status=status.HTTP_204_NO_CONTENT)


# Point
class ContractPointListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, contract_id, section_id, point_id=None):
        if point_id:
            point = get_object_or_404(
            ContractPoint,
            id=point_id,
            section_id=section_id,
            section__contract_id=contract_id
        )
            serializer = ContractPointSerializer(point)
            return Response({"status": "1", "message": "success", "data": [serializer.data]})
        points = ContractPoint.objects.filter(section_id=section_id, section__contract_id=contract_id)
        serializer = ContractPointSerializer(points, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def post(self, request, contract_id, section_id, point_id=None):
        data = request.data.copy()
        data['section'] = section_id
        serializer = ContractPointSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": [serializer.data]}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def patch(self, request, contract_id, section_id, point_id):
        point = get_object_or_404(
            ContractPoint,
            id=point_id,
            section_id=section_id,
            section__contract_id=contract_id
        )
        serializer = ContractPointSerializer(point, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "success", "data": [serializer.data]})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, contract_id, section_id, point_id):
        point = get_object_or_404(
            ContractPoint,
            id=point_id,
            section_id=section_id,
            section__contract_id=contract_id
        )
        point.delete()
        return Response({"status": "1", "message": "Point Deleted Succesfully"}, status=status.HTTP_204_NO_CONTENT)


