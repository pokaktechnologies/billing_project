from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import get_object_or_404
from .models import CustomUser, Feature
from django.db.models import Q
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from .models import *
from .serializers import *
from rest_framework.authtoken.models import Token 
from decimal import Decimal

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
            

    
    
# class CreateQuotationOrderAPI(APIView):
#     def post(self, request):
#         data = request.data

#         # Validate mandatory fields
#         mandatory_fields = [
#             "customer_name",
#             "quotation_date",
#             "due_date",
#             "salesperson",
#             "item_name",
#             "description",
#             "unit_price",
#             "discount",
#             "quantity",
#             "email_id"
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

#         # Generate a unique quotation number
#         quotation_number = f"QUO-{random.randint(111111, 999999)}"
        
#         # Fetch salesperson instance
#         try:
#             salesperson = SalesPerson.objects.get(id=data['salesperson'])
#         except SalesPerson.DoesNotExist:
#             return Response({"error": "Invalid salesperson ID."}, status=status.HTTP_400_BAD_REQUEST)
        
#         # Calculate total amount
#         total_amount = (float(data['unit_price']) - float(data['discount'])) * float(data['quantity'])
        
#         # Save to database
#         quotation_order = QuotationOrderModel.objects.create(
#             customer_name=data['customer_name'],
#             quotation_number=quotation_number,
#             quotation_date=data['quotation_date'],
#             terms=data.get('terms', ''),
#             due_date=data['due_date'],
#             salesperson=salesperson,
#             subject=data.get('subject', ''),
#             attachments=request.FILES.get('attachments', None),
#             item_name=data['item_name'],
#             description=data['description'],
#             unit_price=data['unit_price'],
#             discount=data['discount'],
#             quantity=data['quantity'],
#             total_amount=total_amount,
#             email_id=data['email_id']
#         )

#         return Response(
#             {
#                 "Status": "1",
#                 "message": "Quotation order created successfully.",
#                 "Data": [QuotationOrderSerializer(quotation_order).data]
#             },
#             status=status.HTTP_201_CREATED
#         )


# class QuotationOrderListAPI(APIView):
#     def get(self, request):
#         from_date = request.query_params.get('from_date')
#         to_date = request.query_params.get('to_date')
#         search = request.query_params.get('search')

#         # Filter quotation orders
#         orders = QuotationOrderModel.objects.all()
#         if from_date and to_date:
#             orders = orders.filter(quotation_date__range=[from_date, to_date])
        
#         if search:
#             orders = orders.filter(
#                 Q(customer_name__icontains=search) |
#                 Q(quotation_number__icontains=search) |
#                 Q(salesperson__icontains=search)
#             )
        
#         orders = orders.order_by('-quotation_date')
        
#         data = QuotationOrderSerializer(orders, many=True).data
        
#         return Response({
#             "Status": "1",
#             "message": "Success",
#             "Data": data
#         }, status=status.HTTP_200_OK)

# class QuotationOrderUpdateAPI(APIView):
#     """API for updating an existing Quotation Order"""
#     def put(self, request, pk):
#         try:
#             quotation_order = QuotationOrderModel.objects.get(pk=pk)
#         except QuotationOrderModel.DoesNotExist:
#             return Response({"error": "Quotation order not found."}, status=status.HTTP_404_NOT_FOUND)

#         serializer = QuotationOrderSerializer(quotation_order, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(
#                 {"message": "Quotation order updated successfully.", "Data": [serializer.data]},
#                 status=status.HTTP_200_OK
#             )
#         return Response({"Status": "0", "message": serializer.errors, "Data": []}, status=status.HTTP_400_BAD_REQUEST)

# class QuotationOrderDeleteAPI(APIView):
#     """API for deleting an existing Quotation Order"""
#     def delete(self, request, pk):
#         try:
#             quotation_order = QuotationOrderModel.objects.get(pk=pk)
#             quotation_order.delete()
#             return Response({"Status": "1", "message": "Quotation order deleted successfully.", "Data": []}, status=status.HTTP_204_NO_CONTENT)
#         except QuotationOrderModel.DoesNotExist:
#             return Response({"Status": "0", "message": "Quotation order not found.", "Data": []}, status=status.HTTP_404_NOT_FOUND)    
    
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
    
    def get(self, request, qid=None):
        if qid:
            quotation = get_object_or_404(QuotationOrderModel, id=qid)
            quotation_serializer = NewQuotationOrderSerializer(quotation)
            
            if quotation.bank_account:
                        bank_account_serializer = BankAccountSerializer(quotation.bank_account)
                        bank_account_data = bank_account_serializer.data
            else:
                bank_account_data = None
            # Get quotation items
            quotation_items = QuotationItem.objects.filter(quotation=quotation)
            item_list = []

            # Log debugging info
            print("\n--- DEBUGGING ---")
            print(f"Quotation ID: {quotation.id}, Customer: {quotation.customer_name}")

            for item in quotation_items:
                item_data = {
                    "id": item.id,
                    "name": item.product.name,  # Product name   
                
                    "quantity": item.quantity,
                    "unit_price": item.product.unit_price,  # Added unit price
                    "total": item.total,
                    "sgst": item.sgst,
                    "cgst": item.cgst,
                    "sub_total": item.sub_total,
                }
                item_list.append(item_data)

            print("--- END DEBUGGING ---\n")

            # Return in the required format
            return Response({
                'status': '1',
                'message': 'success',
                'quotation': [
                    {
                        "id": quotation.id,
                        "customer_name": quotation.customer_name,
                        "address":quotation.address,
                        "delivery_location": quotation.delivery_location,
                        "quotation_number": quotation.quotation_number,
                        "bank_account": bank_account_data,
                        "quotation_date": str(quotation.quotation_date),
                        "remark": quotation.remark,
                        "email_id": quotation.email_id,
                        "grand_total": quotation.grand_total,
                        "salesperson": f"{quotation.salesperson.first_name} {quotation.salesperson.last_name}".strip() if quotation.salesperson else None,
                        "salesperson_address": quotation.salesperson.address,
                        # "customer_address": quotation.Customer.address,
                 # New Field

                        "items": item_list,
                    }
                ]
            }, status=status.HTTP_200_OK)

        else:
            # Logic for listing all quotations with filters (from_date, to_date, and search)
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            search = request.query_params.get('search')
            
            quotations = QuotationOrderModel.objects.all()
            
            if from_date and to_date:
                quotations = quotations.filter(quotation_date__range=[from_date, to_date])
            if search:
                quotations = quotations.filter(customer_name__icontains=search)
            
            serializer = QuotationOrderSerializer(quotations, many=True)
            return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)

        

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            with transaction.atomic():
                # Validate and create Quotation Order
                print("\n--- DEBUGGING POST ---")
                print(f"Received Data: {data}")
                salesperson_id = data.get("salesperson")
                if not SalesPerson.objects.filter(id=salesperson_id).exists():
                    return Response({"error": "Invalid salesperson ID"}, status=status.HTTP_400_BAD_REQUEST)
                bank_account_id = data.get("bank_account")
                if not BankAccount.objects.filter(id=bank_account_id).exists():
                    return Response({"error": "Invalid bank account ID"}, status=status.HTTP_400_BAD_REQUEST)
                quotation_number = f"QUO-{random.randint(111111, 999999)}"
                quotation = QuotationOrderModel.objects.create(
                    customer_name=data.get("customer_name"),
                    address=data.get("address"),
                    quotation_number=quotation_number,
                    quotation_date=data.get("quotation_date"),
                    # due_date=data.get("due_date"),
                    salesperson_id=salesperson_id,
                    email_id=data.get("email_id"),
                    # subject=data.get("subject", ""),
                    remark=data.get("remark", ""),
                    
                    # attachments=data.get("attachments", None),
                    grand_total=0  ,
                    delivery_location=data.get("delivery_location", ""),  # New Field
                    bank_account_id= bank_account_id


                )

                # Create Quotation Items
                items = data.get("items", [])
                if not items:
                    return Response({"error": "Quotation must have at least one item."}, status=status.HTTP_400_BAD_REQUEST)
                
                total_amount = 0  


                for item in items:
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)

                    product = Product.objects.get(id=product_id)
                    quantity = float(item.get("quantity", 1))
                    unit_price = float(item.get("unit_price", product.unit_price))

                    print(f"Adding Item: Product ID: {product_id}, Quantity: {quantity}, Unit Price: {unit_price}")

                    item_total = quantity * unit_price
                    total_amount += item_total  
            
                    QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=item.get("quantity", 1),
                        
                        # unit_price=item.get("unit_price", 0),
                        # discount=item.get("discount", 0)
                    )
                print("Total amount: fefe")
                # Update Grand Total
                # quotation.update_grand_total()
                quotation.grand_total = total_amount
                quotation.save()

                print(f"Final Grand Total Saved: {quotation.grand_total}")
                print("--- END DEBUGGING ---\n")

                return Response({
                    "status": "1",
                    "message": "Quotation created successfully.",
                    "quotation_id": quotation.id,
                    "grand_total": quotation.grand_total
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
   
    def patch(self, request, qid=None):
        if not qid:
            return Response({"error": "Quotation ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        
        try:
            with transaction.atomic():
                quotation = get_object_or_404(QuotationOrderModel, id=qid)

                print("\n--- DEBUGGING PATCH ---")
                print(f"Updating Quotation ID: {quotation.id} with data: {data}")

                # Update fields if provided
                quotation.customer_name = data.get("customer_name", quotation.customer_name)
                quotation.quotation_date = data.get("quotation_date", quotation.quotation_date)
                # quotation.due_date = data.get("due_date", quotation.due_date)
                quotation.salesperson_id = data.get("salesperson", quotation.salesperson_id)
                quotation.email_id = data.get("email_id", quotation.email_id)
                quotation.address = data.get("address", quotation.address)
                quotation.delivery_location = data.get("delivery_location", quotation.delivery_location)
                quotation.bank_account_id = data.get("bank_account", quotation.bank_account)
                # quotation.subject = data.get("subject", quotation.subject)
                # quotation.terms = data.get("terms", quotation.terms)
                # quotation.attachments = data.get("attachments", quotation.attachments)
                quotation.save()

                # Remove old items
                quotation.items.all().delete()  # Ensure `related_name="items"` in `QuotationItem` model

                total_amount = Decimal(0)  # Convert total_amount to Decimal

                # Add new items
                for item in data.get("items", []):
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)

                    product = Product.objects.get(id=product_id)
                    quantity = Decimal(str(item.get("quantity", 1)))  # Convert quantity to Decimal
                    # unit_price = product.unit_price  # unit_price is already Decimal
                    unit_price = Decimal(str(item.get("unit_price", product.unit_price)))  
                    print(f"Updating Item: Product ID: {product_id}, Quantity: {quantity}, Unit Price: {unit_price}")

                    QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price  # ✅ Ensure unit price is set correctly

                    )

                    # Calculate total price using Decimal
                    total_amount += quantity * unit_price

                # Update Grand Total
                quotation.grand_total = total_amount
                quotation.save()

                print(f"Final Grand Total Saved: {quotation.grand_total}")
                print("--- END DEBUGGING ---\n")

                return Response({
                    "status": "1",
                    "message": "Quotation updated successfully.",
                    "quotation_id": quotation.id,
                    "grand_total": str(quotation.grand_total)  # Convert Decimal to string for JSON response
                }, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        
                

    def delete(self, request, qid=None):
        if not qid:
            return Response({"error": "Quotation ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        

        try:
            with transaction.atomic():
                quotation = get_object_or_404(QuotationOrderModel, id=qid)
                
                print("\n--- DEBUGGING DELETE ---")
                print(f"Deleting Quotation ID: {quotation.id}")

                # Delete all associated items first
                quotation.items.all().delete()  # Ensure `related_name="items"` in `QuotationItem` model

                # Delete the quotation
                quotation.delete()

                print(f"Quotation ID {qid} deleted successfully")
                print("--- END DEBUGGING ---\n")

                return Response({
                    "status": "1",
                    "message": "Quotation deleted successfully."
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class PrintQuotationAPI(APIView):

    def get(self, request, qid=None):
        # Fetch specific quotation by ID
        quotation = get_object_or_404(QuotationOrderModel, id=qid)
        
        print(f"Quotation Address: {quotation.address}")  # This will print the address in your console/logs
        
        salesperson_address = quotation.salesperson.address if quotation.salesperson else None
      
        salesperson_name = (
            f"{quotation.salesperson.first_name} {quotation.salesperson.last_name}"
            if quotation.salesperson else None
        )

        # Get quotation items
        quotation_items = QuotationItem.objects.filter(quotation=quotation)
        item_list = []

        # Prepare item details for the print view
        for item in quotation_items:
            item_data = {
                "item_name": item.product.name,  # Assuming 'product' is a ForeignKey to a Product model
                # "description": item.product.description,  # Assuming 'description' exists in the Product model
                "quantity": item.quantity,
                "rate": item.product.unit_price,
                "tax": item.sgst + item.cgst,  # Assuming tax is stored as SGST and CGST in QuotationItem
                "amount": item.total,  # Total amount for the item (rate * quantity + tax)
                # "total": item.total,  # Total amount for the item (rate * quantity + tax)

            }
            item_list.append(item_data)
         

        # Prepare the response data
            quotation_data = {
            "quotation_id": quotation.id,
            "customer_name": quotation.customer_name,
            "address": quotation.address if quotation.address else None,
            "salesperson_name": salesperson_name,
            "salesperson_address": salesperson_address,
            "quotation_number": quotation.quotation_number,
            "quotation_date": str(quotation.quotation_date),
            "email_id": quotation.email_id,
            "remark": quotation.remark,
            "subtotal": sum(item['amount'] - item['tax'] for item in item_list),
            "total": sum(item['amount'] for item in item_list),
            "items": item_list,
        }

        # Return the quotation data wrapped in an array (as requested)
        return Response({
            "status": "1",
            "message": "success",
            "data": [quotation_data]  # Wrap the response data in a list (array of objects)
        }, status=status.HTTP_200_OK)

  
class SalesOrderAPI(APIView):
    
    def get(self, request, sid=None):
        if sid:
            sales_order = get_object_or_404(SalesOrderModel, id=sid)
            sales_order_serializer =  NewsalesOrderSerializer(sales_order)
            
            sales_items = SalesOrderItem.objects.filter(sales_order=sales_order)
            item_list = []

            print("\n--- DEBUGGING ---")
            print(f"Sales Order ID: {sales_order.id}, Customer: {sales_order.customer_name}")

            for item in sales_items:
                product_serializer = ProductSerializer(item.product)
                product_data = product_serializer.data
                
                product_data["quantity"] = item.quantity
                product_data["total"] = item.total
                product_data["sgst"] = item.sgst
                product_data["cgst"] = item.cgst
                product_data["sub_total"] = item.sub_total

                item_list.append(product_data)
            
            return Response({
                'status': '1',
                'message': 'success',
                'sales_order': sales_order_serializer.data,
                'items': item_list
            })
        else:
            sales_orders = SalesOrderModel.objects.all()
            serializer =  NewsalesOrderSerializer(sales_orders, many=True)
            return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            with transaction.atomic():
                salesperson_id = data.get("salesperson")
                if not SalesPerson.objects.filter(id=salesperson_id).exists():
                    return Response({"error": "Invalid salesperson ID"}, status=status.HTTP_400_BAD_REQUEST)
                
                sales_order = SalesOrderModel.objects.create(
                    customer_name=data.get("customer_name"),
                    sales_order_id=f"SO-{random.randint(111111, 999999)}",
                    sales_date=data.get("sales_date"),
                    purchase_order_number=data.get("purchase_order_number", ""),
                    terms=data.get("terms", ""),
                    due_date=data.get("due_date"),
                    salesperson_id=salesperson_id,
                    delivery_location=data.get("delivery_location", ""),
                    delivery_address=data.get("delivery_address", ""),
                    contact_person=data.get("contact_person"),
                    mobile_number=data.get("mobile_number"),
                    grand_total=0,
                )
                
                total_amount = 0
                items = data.get("items", [])
                if not items:
                    return Response({"error": "Sales order must have at least one item."}, status=status.HTTP_400_BAD_REQUEST)
                
                for item in items:
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    product = Product.objects.get(id=product_id)
                    quantity = Decimal(str(item.get("quantity", 1)))
                    
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=product,
                        quantity=quantity
                    )
                
                sales_order.update_grand_total()
                
                return Response({
                    "status": "1",
                    "message": "Sales order created successfully.",
                    "sales_order_id": sales_order.id,
                    "grand_total": sales_order.grand_total
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, sid=None):
        if not sid:
            return Response({"error": "Sales Order ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        try:
            with transaction.atomic():
                sales_order = get_object_or_404(SalesOrderModel, id=sid)
                
                sales_order.customer_name = data.get("customer_name", sales_order.customer_name)
                sales_order.sales_date = data.get("sales_date", sales_order.sales_date)
                sales_order.purchase_order_number = data.get("purchase_order_number", sales_order.purchase_order_number)
                sales_order.terms = data.get("terms", sales_order.terms)
                sales_order.due_date = data.get("due_date", sales_order.due_date)
                sales_order.salesperson_id = data.get("salesperson", sales_order.salesperson_id)
                sales_order.delivery_location = data.get("delivery_location", sales_order.delivery_location)
                sales_order.delivery_address = data.get("delivery_address", sales_order.delivery_address)
                sales_order.contact_person = data.get("contact_person", sales_order.contact_person)
                sales_order.mobile_number = data.get("mobile_number", sales_order.mobile_number)
                sales_order.save()

                sales_order.items.all().delete()
                
                for item in data.get("items", []):
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    product = Product.objects.get(id=product_id)
                    quantity = Decimal(str(item.get("quantity", 1)))
                    
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=product,
                        quantity=quantity
                    )
                
                sales_order.update_grand_total()
                
                return Response({
                    "status": "1",
                    "message": "Sales order updated successfully.",
                    "sales_order_id": sales_order.id,
                    "grand_total": str(sales_order.grand_total)
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, sid=None):
        if not sid:
            return Response({"error": "Sales Order ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                sales_order = get_object_or_404(SalesOrderModel, id=sid)
                sales_order.items.all().delete()
                sales_order.delete()
                return Response({"status": "1", "message": "Sales order deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class DeliveryFormAPI(APIView):
    
    def get(self, request, did=None):
        if did:
            delivery = get_object_or_404(DeliveryFormModel, id=did)
            delivery_serializer = NewDeliverySerializer(delivery)
            
            delivery_items = DeliveryItem.objects.filter(delivery_form=delivery)
            item_list = []

            for item in delivery_items:
                product_serializer = ProductSerializer(item.product)
                product_data = product_serializer.data
                
                product_data["quantity"] = item.quantity
                product_data["delivered_quantity"] = item.delivered_quantity
                product_data["status"] = item.status

                item_list.append(product_data)
            
            return Response({
                'status': '1',
                'message': 'success',
                'delivery': delivery_serializer.data,
                'items': item_list
            })
        else:
            deliveries = DeliveryFormModel.objects.all()
            serializer = NewDeliverySerializer(deliveries, many=True)
            return Response({"status": "1", "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            with transaction.atomic():
                # Validate Sales Order ID
                sales_order_id = data.get("sales_order")
                if not SalesOrderModel.objects.filter(id=sales_order_id).exists():
                    return Response({"error": "Invalid sales order ID"}, status=status.HTTP_400_BAD_REQUEST)

                # Validate Salesperson ID
                salesperson_id = data.get("salesperson")
                if not SalesPerson.objects.filter(id=salesperson_id).exists():
                    return Response({"error": "Invalid salesperson ID"}, status=status.HTTP_400_BAD_REQUEST)

                # Create Delivery Form
                delivery_form = DeliveryFormModel.objects.create(
                    customer_name=data.get("customer_name"),
                    delivery_number=f"DLV-{random.randint(111111, 999999)}",  # Unique delivery number
                    delivery_date=data.get("delivery_date"),
                    sales_order_id=sales_order_id,
                    terms=data.get("terms", ""),
                    due_date=data.get("due_date"),
                    salesperson_id=salesperson_id,
                    delivery_location=data.get("delivery_location", ""),
                    delivery_address=data.get("delivery_address", ""),
                    contact_person=data.get("contact_person"),
                    mobile_number=data.get("mobile_number"),
                    time=data.get("time"),
                    date=data.get("date"),
                    grand_total=0  # Will be updated after adding items
                )

                # Validate and Add Delivery Items
                items = data.get("items", [])
                if not items:
                    return Response({"error": "Delivery must have at least one item."}, status=status.HTTP_400_BAD_REQUEST)

                for item in items:
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)

                    product = Product.objects.get(id=product_id)
                    quantity = Decimal(str(item.get("quantity", 1)))

                    DeliveryItem.objects.create(
                        delivery_form=delivery_form,
                        product=product,
                        quantity=quantity
                    ) 

                # Update grand total
                delivery_form.update_grand_total()

                return Response({
                    "status": "1",
                    "message": "Delivery form created successfully.",
                    "delivery_number": delivery_form.delivery_number,
                    "grand_total": delivery_form.grand_total
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def patch(self, request, did=None):
        if not did:
            return Response({"error": "Delivery ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data
        try:
            with transaction.atomic():
                delivery = get_object_or_404(DeliveryFormModel, id=did)
                
                delivery.delivery_date = data.get("delivery_date", delivery.delivery_date)
                delivery.delivery_location = data.get("delivery_location", delivery.delivery_location)
                delivery.delivery_status = data.get("delivery_status", delivery.delivery_status)
                delivery.save()
                
                delivery.items.all().delete()
                
                for item in data.get("items", []):
                    product_id = item.get("product")
                    if not Product.objects.filter(id=product_id).exists():
                        return Response({"error": f"Invalid product ID {product_id}"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    product = Product.objects.get(id=product_id)
                    quantity = Decimal(str(item.get("quantity", 1)))
                    delivered_quantity = Decimal(str(item.get("delivered_quantity", 0)))
                    
                    DeliveryItem.objects.create(
                        delivery_form=delivery,
                        product=product,
                        quantity=quantity,
                        delivered_quantity=delivered_quantity,
                        status=item.get("status", "Pending")
                    )
                
                return Response({
                    "status": "1",
                    "message": "Delivery updated successfully.",
                    "delivery_id": delivery.id
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, did=None):
        if not did:
            return Response({"error": "Delivery ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                delivery = get_object_or_404(DeliveryFormModel, id=did)
                delivery.items.all().delete()
                delivery.delete()
                return Response({"status": "1", "message": "Delivery deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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