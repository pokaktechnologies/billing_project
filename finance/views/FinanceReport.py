from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import JournalEntry, JournalLine, Account
from ..serializers.ledger import JournalEntrySerializer, JournalLineListSerializer, LedgerReportSerializer
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, time
from decimal import Decimal
from ..serializers.accounts import AccountSerializer


#------------
#  pagination class
#--------------
from rest_framework.pagination import PageNumberPagination
class Pagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        page_size = request.query_params.get('page_size')
        if page_size is None:
            return None 
        return int(page_size)
    

# Finance Report

class JournalVoucherReportView(APIView):
    def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        salesperson = request.query_params.get('salesperson')
        search = request.query_params.get('search')

        queryset = JournalEntry.objects.filter(type='journal_voucher') \
            .select_related('salesperson', 'user') \
            .prefetch_related('lines__account') \
            .order_by('-date')

        if from_date:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
            from_date_obj = datetime.combine(from_date_obj, time.min)
            queryset = queryset.filter(date__gte=from_date_obj)


        if to_date:
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
            to_date_obj = datetime.combine(to_date_obj, time.max)
            queryset = queryset.filter(date__lte=to_date_obj)

        if salesperson:
            queryset = queryset.filter(salesperson_id=salesperson)


        if search:
            queryset = queryset.filter(
                Q(type_number__icontains=search) |
                Q(narration__icontains=search) |
                Q(salesperson__first_name__icontains=search) |
                Q(salesperson__last_name__icontains=search)
            )

        paginator = Pagination()
        result_page = paginator.paginate_queryset(queryset, request)

        if result_page is not None:
            serializer = JournalEntrySerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = JournalEntrySerializer(queryset, many=True)
        return Response(serializer.data)
    

class AccountReportView(APIView):
    def get(self, request):

        account_type = request.query_params.get('account_type')
        status = request.query_params.get('status')
        search = request.query_params.get('search')
        is_posting = request.query_params.get('is_posting')
        level = request.query_params.get('level')

        queryset = Account.objects.all().select_related('parent_account')

        if account_type:
            queryset = queryset.filter(type=account_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_posting is not None:
            queryset = queryset.filter(is_posting=is_posting.lower() == 'true')

        if level:
            if level == '2':
                queryset = queryset.filter(parent_account__isnull=True)
            elif level == '3':
                queryset = queryset.filter(parent_account__isnull=False)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(account_number__icontains=search) |
                Q(parent_account__name__icontains=search)
            )

        queryset = queryset.order_by('account_number')

        paginator = Pagination()
        result_page = paginator.paginate_queryset(queryset, request)
        if result_page is not None:
            serializer = AccountSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AccountSerializer(queryset, many=True)
        return Response(serializer.data)


class LedgerReportView(APIView):
    def get(self, request):
        queryset = JournalLine.objects.select_related('journal', 'account').order_by('journal__date', 'created_at')

        account = request.query_params.get('account_id')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')


        if from_date:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
            from_date_obj = datetime.combine(from_date_obj, time.min)
            queryset = queryset.filter(journal__date__gte=from_date_obj)


        if to_date:
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
            to_date_obj = datetime.combine(to_date_obj, time.max)
            queryset = queryset.filter(journal__date__lte=to_date_obj)

        if account: queryset = queryset.filter(account_id=account)

        paginator = Pagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        if paginated_queryset is not None:
            serializer = LedgerReportSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = LedgerReportSerializer(queryset, many=True)
        return Response(serializer.data)