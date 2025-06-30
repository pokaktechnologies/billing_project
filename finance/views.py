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




class FinaceNumberGeneratorView(APIView):
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
        model_type = request.query_params.get('type')

        if model_type == 'ACT':
            model_number = self.generate_next_number(Account, "account_number", "ACT", 6)
        elif model_type == 'JE':
            model_number = self.generate_next_number(JournalEntry, "journal_number", "JE", 6)
        else:
            return Response({
                'status': '0',
                'message': 'Invalid order type',
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': '1',
            'message': 'Success',
            'number': model_number
        }, status=status.HTTP_200_OK)
