from django.views import View
from django.http import HttpResponse
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import *
from .serializers import *



class AccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = Account.objects.filter(user=request.user).order_by('-created_at')
        serializer = AccountSerializer(accounts, many=True)
        return Response({
            "status": True,
            "message": "Accounts retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                "status": True,
                "message": "Account created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": False,
            "message": "Account creation failed.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AccountDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            account = Account.objects.get(pk=pk, user=self.request.user)
            return account
        except Account.DoesNotExist:
            return None

    def get(self, request, pk):
        account = self.get_object(pk)
        if account is None:
            return Response({
                "status": False,
                "message": "Account not found."
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = AccountSerializer(account)
        return Response({
            "status": True,
            "message": "Account details retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        account = self.get_object(pk)
        if account is None:
            return Response({
                "status": False,
                "message": "Account not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = AccountSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": True,
                "message": "Account updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "status": False,
            "message": "Failed to update account.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        account = self.get_object(pk)
        if account is None:
            return Response({
                "status": False,
                "message": "Account not found."
            }, status=status.HTTP_404_NOT_FOUND)
        account.delete()
        return Response({
            "status": True,
            "message": "Account deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)




class JournalEntryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        journal_entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')
        serializer = JournalEntryListSerializer(journal_entries, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        serializer = JournalEntrySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()  # Handles creation and user setting inside serializer
            return Response({"message": "Journal entry created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JournalEntryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            journal_entry = JournalEntry.objects.get(pk=pk, user=self.request.user)
            return journal_entry
        except JournalEntry.DoesNotExist:
            return None

    def get(self, request, pk):
        journal_entry = self.get_object(pk)
        if journal_entry is None:
            return Response({"message": "Journal entry not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = JournalEntryDisplaySerializer(journal_entry)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        journal_entry = self.get_object(pk)
        serializer = JournalEntrySerializer(
            journal_entry,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Journal entry updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        journal_entry = self.get_object(pk)
        if journal_entry is None:
            return Response({"message": "Journal entry not found."}, status=status.HTTP_404_NOT_FOUND)
        journal_entry.delete()
        return Response({"message": "Journal entry deleted successfully."}, status=status.HTTP_204_NO_CONTENT)




class PaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Optional: adjust as needed
    def get(self, request):
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        serializer = PaymentDisplaySerializer(payments, many=True)
        return Response(serializer.data)
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                payment = serializer.save()
                return Response({
                    'status': 'success',
                    'message': 'Payment created successfully.',
                    'payment_id': payment.id,
                    'payment_number': payment.payment_number,
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    

class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            payment = Payment.objects.get(pk=pk, user=self.request.user)
            return payment
        except Payment.DoesNotExist:
            return None

    def get(self, request, pk):
        payment = self.get_object(pk)
        if payment is None:
            return Response({"message": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentDisplaySerializer(payment)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        payment = self.get_object(pk)
        if not payment:
            return Response({"message": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PaymentCreateSerializer(payment, data=request.data, partial=True, context={'request': request})  # ✅ context added
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"message": "Payment updated successfully."}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment = self.get_object(pk)
        if payment is None:
            return Response({"message": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            if payment.journal_entry:
                payment.journal_entry.delete()
            payment.delete()
        return Response({"message": "Payment deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

from .utils import generate_next_number

class FinaceNumberGeneratorView(APIView):
    def get(self, request):
        model_type = request.query_params.get('type')

        model_map = {
            'ACT': (Account, 'account_number', 'ACT'),
            'JE': (JournalEntry, 'journal_number', 'JE'),
            'PAY': (Payment, 'payment_number', 'PAY'),
        }

        if model_type not in model_map:
            return Response({
                'status': '0',
                'message': 'Invalid order type',
            }, status=status.HTTP_400_BAD_REQUEST)

        model, field_name, prefix = model_map[model_type]
        number = generate_next_number(model, field_name, prefix, 6)

        return Response({
            'status': '1',
            'message': 'Success',
            'number': number
        }, status=status.HTTP_200_OK)
