from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q

from ..models import *
from ..serializers.ReportSerializer import *
from ..serializers.serializers import *
from accounts.permissions import HasModulePermission
from rest_framework.authtoken.models import Token 
from decimal import Decimal
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from datetime import timedelta, datetime, date, time

from finance.models import *


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
    

# Generate from_month, to_month_start, and to_month_end
def get_month_range(from_date, to_date):
    from_month = from_date.replace(day=1)

    to_month_start = to_date.replace(day=1)
    to_month_end = to_month_start + relativedelta(months=1) - timedelta(days=1)

    return from_month, to_month_start, to_month_end

# Generate a list of months between from_month and to_month
def generate_months(from_month, to_month_start):
    months = []
    current = to_month_start

    while current >= from_month:
        months.append(current)
        current -= relativedelta(months=1)

    return months



#sales report

class SalesReportSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        # DATE HANDLING
        try:
            if from_date and to_date:
                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            else:
                to_date_obj = date.today()
                from_date_obj = to_date_obj - timedelta(days=365)
        except ValueError:
            return Response({
                "Status": "0",
                "Message": "Invalid date format"
            }, status=status.HTTP_400_BAD_REQUEST)

        # MONTH RANGE
        from_month, to_month_start, to_month_end = get_month_range(from_date_obj, to_date_obj)

        # -------------------------
        # QUERYSETS
        # -------------------------
        invoice_qs = InvoiceModel.objects.filter(
            invoice_date__gte=from_month,
            invoice_date__lte=to_month_end
        )

        return_qs = SalesReturnModel.objects.filter(
            return_date__gte=from_month,
            return_date__lte=to_month_end
        )

        # -------------------------
        # GROUP BY MONTH
        # -------------------------
        sales_data = invoice_qs.annotate(
            month=TruncMonth('invoice_date')
        ).values('month').annotate(
            total_sales=Sum('invoice_grand_total'),
            total_orders=Count('id'),
            avg_order_value=Avg('invoice_grand_total')
        ).order_by('month')

        return_data = return_qs.annotate(
            month=TruncMonth('return_date')
        ).values('month').annotate(
            total_returns=Sum('grand_total')
        ).order_by('month')

        sales_dict = {
            item['month'].strftime("%Y-%m"): item
            for item in sales_data
        }

        return_dict = {
            item['month'].strftime("%Y-%m"): item['total_returns']
            for item in return_data
        }

        # -------------------------
        # MONTH LIST
        # -------------------------
        months_list = generate_months(from_month, to_month_start)

        # -------------------------
        # FINAL DATA
        # -------------------------
        final_data = []

        for month in months_list:
            key = month.strftime("%Y-%m")

            sales_info = sales_dict.get(key)

            total_sales = sales_info['total_sales'] if sales_info else 0
            total_orders = sales_info['total_orders'] if sales_info else 0
            avg_order_value = sales_info['avg_order_value'] if sales_info else 0
            total_returns = return_dict.get(key, 0)

            net_sales = (total_sales or 0) - (total_returns or 0)

            final_data.append({
                "period": month.strftime("%b %Y"),
                "total_sales": total_sales or Decimal("0.00"),
                "total_orders": total_orders or 0,
                "avg_order_value": round(avg_order_value or 0, 2),
                "total_returns": total_returns or 0,
                "net_sales": net_sales
            })

        # -------------------------
        # YTD SUMMARY (FIXED)
        # -------------------------
        year = to_date_obj.year

        start_of_year = date(year, 1, 1)
        today_date = date.today()

        total_sales_ytd = InvoiceModel.objects.filter(
            invoice_date__gte=start_of_year,
            invoice_date__lte=today_date
        ).aggregate(total=Sum('invoice_grand_total'))['total'] or 0

        total_returns_ytd = SalesReturnModel.objects.filter(
            return_date__gte=start_of_year,
            return_date__lte=today_date
        ).aggregate(total=Sum('grand_total'))['total'] or 0

        net_sales_ytd = total_sales_ytd - total_returns_ytd

        summary_data = {
                "total_sales_ytd": total_sales_ytd,
                "total_returns_ytd": total_returns_ytd,
                "net_sales_ytd": net_sales_ytd
            }

        monthly_serializer = SalesSummaryReportSerializer(final_data, many=True)
        summary_serializer = SalesSummaryYtdSerializer(summary_data)

        return Response({
            "Status": "1",
            "Message": "Success",
            "Data": monthly_serializer.data,
            "Summary": summary_serializer.data
        }, status=status.HTTP_200_OK)


class SalesReportByClientView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        client_id = request.GET.get('client', 'all')
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')

        # DATE PARSE & VALIDATION
        from_date = parse_date(from_date_str) if from_date_str else None
        to_date = parse_date(to_date_str) if to_date_str else None

        if (from_date_str and not from_date) or (to_date_str and not to_date):
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if from_date and to_date and from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'from_date must be before or equal to to_date.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # CLIENT VALIDATION
        if client_id != 'all':
            try:
                client_id = int(client_id)
                if not Customer.objects.filter(id=client_id).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid client ID.'
                }, status=status.HTTP_400_BAD_REQUEST)

        # BASE QUERY
        invoices = InvoiceModel.objects.filter(invoice_type='client')

        # OPTIONAL DATE FILTER
        if from_date:
            invoices = invoices.filter(invoice_date__gte=from_date)

        if to_date:
            invoices = invoices.filter(invoice_date__lte=to_date)

        # CLIENT FILTER
        if client_id != 'all':
            invoices = invoices.filter(client_id=client_id)

        # FETCH ITEMS
        invoice_items = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).select_related(
            'invoice',
            'invoice__client',
            'invoice__sales_order',
            'product'
        )

        # RESPONSE DATA
        data = []

        for item in invoice_items:
            invoice = item.invoice
            client = invoice.client

            data.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "client_id": client.id if client else None,
                "client_name": f"{client.first_name} {client.last_name}" if client else None,
                "sales_order_id": invoice.sales_order.id if invoice.sales_order else None,
                "sales_order_number": invoice.sales_order.sales_order_number if invoice.sales_order else None,
                "product_id": item.product.id if item.product else None,
                "product_name": item.product.name if item.product else None,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "sgst_percentage": item.sgst_percentage,
                "cgst_percentage": item.cgst_percentage,
                "sgst": item.sgst,
                "cgst": item.cgst,
                "sub_total": item.sub_total,
                "total": item.total,
            })

        # PAGINATION
        paginator = Pagination()
        result_page = paginator.paginate_queryset(data, request)

        if result_page is not None:
            return paginator.get_paginated_response(result_page)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Count': len(data),
            'Data': data
        }, status=status.HTTP_200_OK)

class SalesReportByItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        item = request.GET.get('item', 'all')
        client = request.GET.get('client', 'all')

        # --------------------
        # DATE PARSE & VALIDATION (OPTIONAL)
        # --------------------
        from_date = parse_date(from_date_str) if from_date_str else None
        to_date = parse_date(to_date_str) if to_date_str else None

        if (from_date_str and not from_date) or (to_date_str and not to_date):
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=400)

        if from_date and to_date and from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range.'
            }, status=400)

        # --------------------
        # CLIENT VALIDATION
        # --------------------
        if client not in ['all', None, '', 'null', 'undefined']:
            try:
                client = int(client)
                if not Customer.objects.filter(id=client).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid client ID.'
                }, status=400)

        # --------------------
        # ITEM VALIDATION
        # --------------------
        if item not in ['all', None, '', 'null', 'undefined']:
            try:
                item = int(item)
                if not Product.objects.filter(id=item).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid item ID.'
                }, status=400)

        # --------------------
        # BASE INVOICE QUERY
        # --------------------
        invoices = InvoiceModel.objects.filter(invoice_type='client')

        # --------------------
        # OPTIONAL DATE FILTER
        # --------------------
        if from_date:
            invoices = invoices.filter(invoice_date__gte=from_date)

        if to_date:
            invoices = invoices.filter(invoice_date__lte=to_date)

        # --------------------
        # CLIENT FILTER
        # --------------------
        if client != 'all':
            invoices = invoices.filter(client_id=client)

        # --------------------
        # FETCH ITEMS
        # --------------------
        invoice_items = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).select_related(
            'invoice',
            'invoice__client',
            'invoice__sales_order',
            'product'
        )

        # --------------------
        # ITEM FILTER
        # --------------------
        if item != 'all':
            invoice_items = invoice_items.filter(product_id=item)

        # --------------------
        # RESPONSE DATA
        # --------------------
        data = []

        for i in invoice_items:
            inv = i.invoice
            c = inv.client
            p = i.product

            data.append({
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "client_name": f"{c.first_name} {c.last_name}" if c else None,
                "product_name": p.name if p else None,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "sgst": i.sgst,
                "cgst": i.cgst,
                "sub_total": i.sub_total,
                "total": i.total,
            })

        # --------------------
        # PAGINATION
        # --------------------
        paginator = Pagination()
        result_page = paginator.paginate_queryset(data, request)

        if result_page is not None:
            return paginator.get_paginated_response(result_page)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Count': len(data),
            'Data': data
        })

class SalesReportBySalespersonView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        salesperson = request.GET.get('salesperson', 'all')
        item = request.GET.get('item', 'all')

        # --------------------
        # DATE PARSE & VALIDATION (OPTIONAL)
        # --------------------
        from_date = parse_date(from_date_str) if from_date_str else None
        to_date = parse_date(to_date_str) if to_date_str else None

        if (from_date_str and not from_date) or (to_date_str and not to_date):
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=400)

        if from_date and to_date and from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range.'
            }, status=400)

        # --------------------
        # SALESPERSON VALIDATION
        # --------------------
        if salesperson not in ['all', None, '', 'null', 'undefined']:
            try:
                salesperson = int(salesperson)
                if not SalesPerson.objects.filter(id=salesperson).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid salesperson ID.'
                }, status=400)

        # --------------------
        # ITEM VALIDATION
        # --------------------
        if item not in ['all', None, '', 'null', 'undefined']:
            try:
                item = int(item)
                if not Product.objects.filter(id=item).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid item ID.'
                }, status=400)

        # --------------------
        # BASE QUERY
        # --------------------
        invoices = InvoiceModel.objects.filter(invoice_type='client')

        # --------------------
        # OPTIONAL DATE FILTER
        # --------------------
        if from_date:
            invoices = invoices.filter(invoice_date__gte=from_date)

        if to_date:
            invoices = invoices.filter(invoice_date__lte=to_date)

        # --------------------
        # SALESPERSON FILTER
        # --------------------
        if salesperson != 'all':
            invoices = invoices.filter(client__salesperson_id=salesperson)

        # --------------------
        # FETCH ITEMS
        # --------------------
        invoice_items = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).select_related(
            'invoice',
            'invoice__client',
            'invoice__client__salesperson',
            'product'
        )

        # --------------------
        # ITEM FILTER
        # --------------------
        if item != 'all':
            invoice_items = invoice_items.filter(product_id=item)

        # --------------------
        # RESPONSE DATA
        # --------------------
        data = []

        for i in invoice_items:
            inv = i.invoice
            c = inv.client
            s = c.salesperson if c else None

            data.append({
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "client_name": f"{c.first_name} {c.last_name}" if c else None,
                "salesperson_name": f"{s.first_name} {s.last_name}" if s else None,
                "product_name": i.product.name if i.product else None,
                "quantity": i.quantity,
                "total": i.total,
            })

        # --------------------
        # PAGINATION
        # --------------------
        paginator = Pagination()
        result_page = paginator.paginate_queryset(data, request)

        if result_page is not None:
            return paginator.get_paginated_response(result_page)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Count': len(data),
            'Data': data
        })

class SalesReportByCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        category = request.GET.get('category', 'all')
        item = request.GET.get('item', 'all')

        # --------------------
        # DATE PARSE & VALIDATION (OPTIONAL)
        # --------------------
        from_date = parse_date(from_date_str) if from_date_str else None
        to_date = parse_date(to_date_str) if to_date_str else None

        if (from_date_str and not from_date) or (to_date_str and not to_date):
            return Response({
                'Status': '0',
                'Message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=400)

        if from_date and to_date and from_date > to_date:
            return Response({
                'Status': '0',
                'Message': 'Invalid date range.'
            }, status=400)

        # --------------------
        # ITEM VALIDATION
        # --------------------
        if item not in ['all', None, '', 'null', 'undefined']:
            try:
                item = int(item)
                if not Product.objects.filter(id=item).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid item ID.'
                }, status=400)

        # --------------------
        # CATEGORY VALIDATION
        # --------------------
        if category not in ['all', None, '', 'null', 'undefined']:
            try:
                category = int(category)
                if not Category.objects.filter(id=category).exists():
                    raise ValueError
            except:
                return Response({
                    'Status': '0',
                    'Message': 'Invalid category ID.'
                }, status=400)

        # --------------------
        # BASE QUERY
        # --------------------
        invoices = InvoiceModel.objects.filter(invoice_type='client')

        # --------------------
        # OPTIONAL DATE FILTER
        # --------------------
        if from_date:
            invoices = invoices.filter(invoice_date__gte=from_date)

        if to_date:
            invoices = invoices.filter(invoice_date__lte=to_date)

        # --------------------
        # FETCH ITEMS
        # --------------------
        invoice_items = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).select_related(
            'invoice',
            'invoice__client',
            'product',
            'product__category'
        )

        # --------------------
        # ITEM FILTER
        # --------------------
        if item != 'all':
            invoice_items = invoice_items.filter(product_id=item)

        # --------------------
        # CATEGORY FILTER
        # --------------------
        if category != 'all':
            invoice_items = invoice_items.filter(product__category_id=category)

        # --------------------
        # RESPONSE DATA
        # --------------------
        data = []

        for i in invoice_items:
            inv = i.invoice
            c = inv.client
            p = i.product
            cat = p.category if p else None

            data.append({
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "client_name": f"{c.first_name} {c.last_name}" if c else None,
                "product_name": p.name if p else None,
                "category_name": cat.name if cat else None,
                "quantity": i.quantity,
                "total": i.total,
            })

        # --------------------
        # PAGINATION
        # --------------------
        paginator = Pagination()
        result_page = paginator.paginate_queryset(data, request)

        if result_page is not None:
            return paginator.get_paginated_response(result_page)

        return Response({
            'Status': '1',
            'Message': 'Success',
            'Count': len(data),
            'Data': data
        })

# quotation report
class QuotationReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        client = request.query_params.get('client')
        search = request.query_params.get('search')
        salesperson = request.query_params.get('salesperson')

        quotations = QuotationOrderModel.objects.all().order_by('-id')

        if start_date and end_date:
            quotations = quotations.filter(
                quotation_date__range=[start_date, end_date]
            )

        if client:
            quotations = quotations.filter(client__id=client)

        if salesperson:
            quotations = quotations.filter(client__salesperson=salesperson)

        if search:
            quotations = quotations.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(project_name__icontains=search)
            )

        paginator = Pagination()
        paginated_quotations = paginator.paginate_queryset(quotations, request)
        if paginated_quotations is not None:
            serializer = QuotationOrderSerializer(paginated_quotations, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = QuotationOrderSerializer(quotations, many=True)
        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": quotations.count(),
            "Data": serializer.data
        })

#invoice report
class InvoiceReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        client = request.query_params.get('client')
        intern = request.query_params.get('intern')
        search = request.query_params.get('search')
        invoice_type = request.query_params.get('invoice_type')

        invoices = InvoiceModel.objects.select_related(
            "client",
            "intern__user"
        ).prefetch_related(
            "items"
        ).annotate(
            total_without_tax=Coalesce(
                Sum("items__total"),
                Decimal("0.00")
            ),
            total_tax=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("items__sgst") + F("items__cgst"),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ),
                Decimal("0.00")
            )
        ).order_by("-id")

        if start_date and end_date:
            invoices = invoices.filter(
                invoice_date__range=[start_date, end_date]
            )

        if invoice_type and invoice_type != "null":
            invoices = invoices.filter(invoice_type=invoice_type)

        if client and intern:
            return Response({
                "Status": "0",
                "Message": "You cannot filter by both client and intern at the same time."
            })

        if client and client != "null":
            invoices = invoices.filter(client_id=client)

        if intern and intern != "null":
            invoices = invoices.filter(intern_id=intern)

        if search:
            invoices = invoices.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(intern__user__first_name__icontains=search) |
                Q(intern__user__last_name__icontains=search) |
                Q(invoice_number__icontains=search) 
            )
        paginator = Pagination()
        paginated_invoices = paginator.paginate_queryset(invoices, request)


        if paginated_invoices is not None:
            serializer = InvoiceReportSerializer(paginated_invoices, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = InvoiceReportSerializer(invoices, many=True)
        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": invoices.count(),
            "Data": serializer.data
        })

# Receipt  Report
class ReceiptReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        client = request.query_params.get('client')
        intern = request.query_params.get('intern')
        search = request.query_params.get('search')
        receipt_type = request.query_params.get('receipt_type')

        # Optimized queryset
        receipts = ReceiptModel.objects.select_related(
            "client", 
            "intern__user",
            "invoice",
            "course"
        ).order_by("-id")

        # Date filter (Correct field name)
        if start_date and end_date:
            receipts = receipts.filter(
                receipt_date__range=[start_date, end_date]
            )

        # Receipt type filter
        if receipt_type and receipt_type != "null":
            receipts = receipts.filter(receipt_type=receipt_type)

        # Prevent wrong combo
        if client and intern:
            return Response({
                "Status": "0",
                "Message": "You cannot filter by both client and intern at the same time."
            })

        # Client filter
        if client and client != "null":
            receipts = receipts.filter(
                receipt_type="client",
                client_id=client
            )

        # Intern filter
        if intern and intern != "null":
            receipts = receipts.filter(
                receipt_type="intern",
                intern_id=intern
            )

        if search:
            receipts = receipts.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(intern__user__first_name__icontains=search) |
                Q(intern__user__last_name__icontains=search) |
                Q(receipt_number__icontains=search)
            )

        paginator = Pagination()
        paginated_receipts = paginator.paginate_queryset(receipts, request)

        if paginated_receipts is not None:
            serializer = ReceiptSerializer(paginated_receipts, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ReceiptSerializer(receipts, many=True)

        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": receipts.count(),
            "Data": serializer.data
        })

# Sales Return Report
class SalesReturnReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        client = request.query_params.get('client')
        search = request.query_params.get('search')

        sales_returns = SalesReturnModel.objects.select_related(
            "client",
            "sales_order",
            "termsandconditions"
        ).prefetch_related(
            "items"
        ).order_by('-id')

        if start_date and end_date:
            sales_returns = sales_returns.filter(
                return_date__range=[start_date, end_date]
            )

        if client:
            sales_returns = sales_returns.filter(client_id=client)

        if search:
            sales_returns = sales_returns.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(sales_return_number__icontains=search) |
                Q(sales_order__sales_order_number__icontains=search)
            )

        paginator = Pagination()
        paginated_sales_returns = paginator.paginate_queryset(sales_returns, request)

        if paginated_sales_returns is not None:
            serializer = SalesReturnDetailDisplaySerializer(
                paginated_sales_returns,
                many=True
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = SalesReturnDetailDisplaySerializer(
            sales_returns,
            many=True
        )

        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": sales_returns.count(),
            "Data": serializer.data
        })

#---------------
# PurchaseReportView
# -----------------


# Purchase Order Report
class PurchaseOrderReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        supplier = request.query_params.get('supplier')
        search = request.query_params.get('search')

        purchases = PurchaseOrder.objects.select_related(
            "supplier",
            "terms_and_conditions"
        ).prefetch_related(
            "items"
        ).order_by('-id')

        if start_date and end_date:
            purchases = purchases.filter(
                purchase_order_date__range=[start_date, end_date]
            )

        if supplier:
            purchases = purchases.filter(supplier_id=supplier)

        if search:
            purchases = purchases.filter(
                Q(supplier__first_name__icontains=search) |
                Q(supplier__last_name__icontains=search) |
                Q(purchase_order_number__icontains=search)
            )

        paginator = Pagination()
        paginated_purchases = paginator.paginate_queryset(purchases, request)

        if paginated_purchases is not None:
            serializer = PurchaseOrderSerializer(
                paginated_purchases,
                many=True
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = PurchaseOrderReportSerializer(
            purchases,
            many=True
        )

        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": purchases.count(),
            "Data": serializer.data
        })


# Material Receive Report

class MaterialReceiveReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        supplier = request.query_params.get('supplier')
        search = request.query_params.get('search')

        material_receives = MaterialReceive.objects.select_related(
            "supplier",
            "purchase_order"
        ).prefetch_related(
            "items__product"
        ).order_by('-id')

        if start_date and end_date:
            material_receives = material_receives.filter(
                received_date__range=[start_date, end_date]
            )

        if supplier:
            material_receives = material_receives.filter(supplier_id=supplier)

        if search:
            material_receives = material_receives.filter(
                Q(supplier__first_name__icontains=search) |
                Q(supplier__last_name__icontains=search) |
                Q(material_receive_number__icontains=search)
            )

        paginator = Pagination()
        paginated_queryset = paginator.paginate_queryset(material_receives, request)

        if paginated_queryset is not None:
            serializer = MaterialReceiveReportSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MaterialReceiveReportSerializer(material_receives, many=True)

        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": material_receives.count(),
            "Data": serializer.data
        })

# Supplier Report
class SupplierReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        supplier_type = request.query_params.get('supplier_type')
        search = request.query_params.get('search')

        suppliers = Supplier.objects.order_by('-id')

        if start_date and end_date:
            suppliers = suppliers.filter(
                created_at__range=[start_date, end_date]
            )

        if supplier_type:
            suppliers = suppliers.filter(supplier_type=supplier_type)

        if search:
            suppliers = suppliers.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(supplier_number__icontains=search)
            )

        paginator = Pagination()
        paginated_suppliers = paginator.paginate_queryset(suppliers, request)

        if paginated_suppliers is not None:
            serializer = SupplierDetailSerializer(paginated_suppliers, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = SupplierDetailSerializer(suppliers, many=True)

        return Response({
            "Status": "1",
            "Message": "Success",
            "Count": suppliers.count(),
            "Data": serializer.data
        })
    
# Purchase Summary
class PurchaseSummaryReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        # -------------------------
        # DATE HANDLING
        # -------------------------
        try:
            if from_date and to_date:
                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            else:
                to_date_obj = date.today()
                from_date_obj = to_date_obj - timedelta(days=365)
        except ValueError:
            return Response({
                "Status": "0",
                "Message": "Invalid date format (YYYY-MM-DD)"
            }, status=status.HTTP_400_BAD_REQUEST)

        # -------------------------
        # MONTH RANGE
        # -------------------------
        from_month, to_month_start, to_month_end = get_month_range(from_date_obj, to_date_obj)

        # -------------------------
        # QUERYSET
        # -------------------------
        qs = PurchaseOrder.objects.filter(
            purchase_order_date__gte=from_month,
            purchase_order_date__lte=to_month_end
        )

        # -------------------------
        # GROUP BY MONTH
        # -------------------------
        data = qs.annotate(
            month=TruncMonth('purchase_order_date')
        ).values('month').annotate(
            total_orders=Count('id'),
            total_amount=Sum('grand_total'),
            avg_order_value=Avg('grand_total'),
            total_suppliers=Count('supplier', distinct=True)
        ).order_by('month')

        data_dict = {
            item['month'].strftime("%Y-%m"): item
            for item in data
        }

        # -------------------------
        # MONTH LIST
        # -------------------------
        months_list = generate_months(from_month, to_month_start)

        # -------------------------
        # FINAL DATA
        # -------------------------
        result = []

        for month in months_list:
            key = month.strftime("%Y-%m")
            item = data_dict.get(key)

            result.append({
                "month": month.strftime("%B %Y"),
                "total_orders": item['total_orders'] if item else 0,
                "total_suppliers": item['total_suppliers'] if item else 0,
                "total_amount": item['total_amount'] if item and item['total_amount'] else 0,
                "avg_order_value": round(item['avg_order_value'] or 0, 2) if item else 0
            })

        serializer = PurchaseSummaryReportSerializer(result, many=True)

        return Response({
            "Status": "1",
            "Message": "Success",
            "Data": serializer.data
        })
