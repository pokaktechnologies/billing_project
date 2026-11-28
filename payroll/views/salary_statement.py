from decimal import Decimal

from django.db.models import CharField, Count, DecimalField, IntegerField, Max, Min, Q, Sum, Value
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.response import Response

from ..filters import SalaryStatementFilter
from ..models import AttendanceSummary, Payroll
from ..pagination import OptionalPagination
from ..serializers.salary_statement import (
    FlatSalaryStatementSerializer,
    SalaryStatementSerializer,
    SalaryStatementSummarySerializer,
)

FLAT_SORT_PRESETS = {
    'newest': ('-period__month', '-created_at', '-id'),
    'oldest': ('period__month', 'created_at', 'id'),
    'highest': ('-net_salary', '-period__month', '-id'),
    'highest_salary': ('-net_salary', '-period__month', '-id'),
    'salary_high': ('-net_salary', '-period__month', '-id'),
    'lowest': ('net_salary', '-period__month', '-id'),
    'lowest_salary': ('net_salary', '-period__month', '-id'),
    'salary_low': ('net_salary', '-period__month', '-id'),
}

SUMMARY_SORT_PRESETS = {
    'newest': ('-latest_period', '-latest_created_at', 'staff_id'),
    'oldest': ('earliest_period', 'earliest_created_at', 'staff_id'),
    'highest': ('-net_salary_total', 'staff_id'),
    'highest_salary': ('-net_salary_total', 'staff_id'),
    'salary_high': ('-net_salary_total', 'staff_id'),
    'lowest': ('net_salary_total', 'staff_id'),
    'lowest_salary': ('net_salary_total', 'staff_id'),
    'salary_low': ('net_salary_total', 'staff_id'),
}

FLAT_ALLOWED_ORDERING = {
    'gross_salary',
    'net_salary',
    'deduction',
    'working_days',
    'created_at',
    'period__month',
    'status',
}

SUMMARY_ORDERING_MAP = {
    'gross_salary': 'gross_salary_total',
    '-gross_salary': '-gross_salary_total',
    'net_salary': 'net_salary_total',
    '-net_salary': '-net_salary_total',
    'deduction': 'deduction_total',
    '-deduction': '-deduction_total',
    'working_days': 'working_days_total',
    '-working_days': '-working_days_total',
    'period__month': 'earliest_period',
    '-period__month': '-latest_period',
    'created_at': 'earliest_created_at',
    '-created_at': '-latest_created_at',
    'staff_name': 'staff__user__first_name',
    '-staff_name': '-staff__user__first_name',
}

SUMMARY_GROUP_FIELDS = (
    'staff_id',
    'staff__user__first_name',
    'staff__user__last_name',
    'staff__user__email',
    'staff__phone_number',
    'staff__job_detail__employee_id',
    'staff__job_detail__department__name',
    'staff__job_detail__role',
    'staff__job_detail__job_type',
)


def _get_sort_preset_key(request):
    return (request.query_params.get('sort_by') or request.query_params.get('sort') or '').strip().lower()


def _resolve_flat_ordering(request):
    sort_key = _get_sort_preset_key(request)
    if sort_key in FLAT_SORT_PRESETS:
        return FLAT_SORT_PRESETS[sort_key]

    ordering_param = (request.query_params.get('ordering') or '').strip()
    if ordering_param:
        resolved = []
        for token in ordering_param.split(','):
            field = token.strip()
            bare = field.lstrip('-')
            if bare in FLAT_ALLOWED_ORDERING:
                resolved.append(field)
        if resolved:
            return tuple(resolved)

    return FLAT_SORT_PRESETS['newest']


def _resolve_summary_ordering(request):
    sort_key = _get_sort_preset_key(request)
    if sort_key in SUMMARY_SORT_PRESETS:
        return SUMMARY_SORT_PRESETS[sort_key]

    ordering_param = (request.query_params.get('ordering') or '').strip()
    if ordering_param:
        resolved = []
        for token in ordering_param.split(','):
            mapped = SUMMARY_ORDERING_MAP.get(token.strip())
            if mapped:
                resolved.append(mapped)
        if resolved:
            return tuple(resolved)

    return SUMMARY_SORT_PRESETS['newest']


def _build_attendance_map(payrolls):
    staff_ids = {p.staff_id for p in payrolls}
    period_ids = {p.period_id for p in payrolls if p.period_id is not None}
    if not staff_ids or not period_ids:
        return {}
    summaries = AttendanceSummary.objects.filter(
        staff_id__in=staff_ids,
        period_id__in=period_ids,
    )
    return {(summary.staff_id, summary.period_id): summary for summary in summaries}


def _build_attendance_totals(filtered_qs, staff_ids):
    if not staff_ids:
        return {}
    valid_pairs = set(
        filtered_qs.filter(staff_id__in=staff_ids, period_id__isnull=False)
        .values_list('staff_id', 'period_id')
    )
    if not valid_pairs:
        return {}

    period_ids = {period_id for _, period_id in valid_pairs}
    summaries = AttendanceSummary.objects.filter(
        staff_id__in=staff_ids,
        period_id__in=period_ids,
    ).only('staff_id', 'period_id', 'full_days', 'half_days', 'leave_days', 'absent_days')

    totals = {}
    for summary in summaries:
        if (summary.staff_id, summary.period_id) not in valid_pairs:
            continue
        bucket = totals.setdefault(
            summary.staff_id,
            {'full_days': 0, 'half_days': 0, 'leave_days': 0, 'absent_days': 0},
        )
        bucket['full_days'] += summary.full_days
        bucket['half_days'] += summary.half_days
        bucket['leave_days'] += summary.leave_days
        bucket['absent_days'] += summary.absent_days
    return totals


class AllSalaryStatementListView(generics.ListAPIView):
    """
    GET → List salary statements across all staff in a one-line representation.
    Default view=summary aggregates one row per staff across the filtered period;
    view=flat returns one flat row per (staff, period) payroll record.
    """

    queryset = Payroll.objects.all().select_related(
        'staff__user', 'staff__job_detail', 'staff__job_detail__department', 'period'
    )
    pagination_class = OptionalPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = SalaryStatementFilter
    search_fields = [
        'staff__user__first_name',
        'staff__user__last_name',
        'staff__user__email',
        'staff__job_detail__employee_id',
    ]

    def _compute_overall_summary(self, filtered_qs):
        zero_decimal = Value(
            Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2)
        )
        agg = filtered_qs.aggregate(
            total_staff=Count('staff_id', distinct=True),
            total_records=Count('id'),
            total_gross_salary=Coalesce(
                Sum('gross_salary'),
                zero_decimal,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_deduction=Coalesce(
                Sum('deduction'),
                zero_decimal,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_net_salary=Coalesce(
                Sum('net_salary'),
                zero_decimal,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        return {
            'total_staff': agg['total_staff'] or 0,
            'total_records': agg['total_records'] or 0,
            'total_gross_salary': f"{(agg['total_gross_salary'] or Decimal('0.00')):.2f}",
            'total_deduction': f"{(agg['total_deduction'] or Decimal('0.00')):.2f}",
            'total_net_salary': f"{(agg['total_net_salary'] or Decimal('0.00')):.2f}",
        }

    def _build_applied_filters(self, request):
        params = request.query_params
        sort_key = _get_sort_preset_key(request)
        ordering = (params.get('ordering') or '').strip()
        effective_sort = sort_key or (ordering if ordering else 'newest')
        status_val = (params.get('status') or '').strip().lower() or 'all'
        return {
            'year': params.get('year'),
            'month': params.get('month'),
            'period_month': params.get('period_month'),
            'start_month': params.get('start_month'),
            'end_month': params.get('end_month'),
            'start_date': params.get('start_date'),
            'end_date': params.get('end_date'),
            'duration': params.get('duration'),
            'status': status_val,
            'sort_by': effective_sort,
        }

    def _build_summary_queryset(self, filtered_qs, request):
        effective_month = Coalesce(
            'period__month',
            'month',
            output_field=CharField(max_length=7),
        )
        return (
            filtered_qs.order_by()
            .values(*SUMMARY_GROUP_FIELDS)
            .annotate(
                months_count=Count('id'),
                gross_salary_total=Coalesce(
                    Sum('gross_salary'),
                    Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                deduction_total=Coalesce(
                    Sum('deduction'),
                    Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                net_salary_total=Coalesce(
                    Sum('net_salary'),
                    Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                working_days_total=Coalesce(
                    Sum('working_days'),
                    Value(0, output_field=IntegerField()),
                    output_field=IntegerField(),
                ),
                total_working_hours_sum=Coalesce(
                    Sum('total_working_hours'),
                    Value(Decimal('0.00'), output_field=DecimalField(max_digits=10, decimal_places=2)),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                paid_leave_used_total=Coalesce(
                    Sum('paid_leave_used'),
                    Value(0, output_field=IntegerField()),
                    output_field=IntegerField(),
                ),
                unpaid_leave_days_total=Coalesce(
                    Sum('unpaid_leave_days'),
                    Value(Decimal('0.00'), output_field=DecimalField(max_digits=8, decimal_places=2)),
                    output_field=DecimalField(max_digits=8, decimal_places=2),
                ),
                paid_months=Count('id', filter=Q(status__iexact='Paid')),
                draft_months=Count('id', filter=Q(status__iexact='Draft')),
                latest_period=Max(effective_month, output_field=CharField(max_length=7)),
                earliest_period=Min(effective_month, output_field=CharField(max_length=7)),
                latest_created_at=Max('created_at'),
                earliest_created_at=Min('created_at'),
                latest_payroll_id=Max('id'),
            )
            .order_by(*_resolve_summary_ordering(request))
        )

    def list(self, request, *args, **kwargs):
        filtered_qs = self.filter_queryset(self.get_queryset())
        summary_data = self._compute_overall_summary(filtered_qs)
        applied_filters = self._build_applied_filters(request)

        raw_view = (request.query_params.get('view') or 'summary').strip().lower()
        view_mode = 'flat' if raw_view == 'flat' else 'summary'

        if view_mode == 'flat':
            flat_qs = filtered_qs.order_by(*_resolve_flat_ordering(request))
            page = self.paginate_queryset(flat_qs)
            items = list(page) if page is not None else list(flat_qs)
            attendance_map = _build_attendance_map(items)
            serializer = FlatSalaryStatementSerializer(
                items,
                many=True,
                context={**self.get_serializer_context(), 'attendance_map': attendance_map},
            )
        else:
            summary_qs = self._build_summary_queryset(filtered_qs, request)
            page = self.paginate_queryset(summary_qs)
            rows = list(page) if page is not None else list(summary_qs)
            staff_ids = [row['staff_id'] for row in rows]
            attendance_totals = _build_attendance_totals(filtered_qs, staff_ids)
            serializer = SalaryStatementSummarySerializer(
                rows,
                many=True,
                context={**self.get_serializer_context(), 'attendance_totals': attendance_totals},
            )

        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data = {
                'view': view_mode,
                'filters': applied_filters,
                'summary': summary_data,
                **response.data,
            }
            return response

        return Response({
            'view': view_mode,
            'filters': applied_filters,
            'summary': summary_data,
            'count': len(serializer.data),
            'results': serializer.data,
        })


class SalaryStatementListView(generics.ListAPIView):
    """
    GET → List salary statements for a single staff member with duration,
    year/month, date range, status, and sort presets.
    """

    queryset = Payroll.objects.all().select_related(
        'staff__user', 'staff__job_detail', 'staff__job_detail__department', 'period'
    )
    serializer_class = SalaryStatementSerializer
    pagination_class = OptionalPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = SalaryStatementFilter
    search_fields = [
        'staff__user__first_name',
        'staff__user__last_name',
        'staff__user__email',
        'staff__job_detail__employee_id',
    ]

    def get_queryset(self):
        staff_id = self.kwargs.get('staff_id')
        return super().get_queryset().filter(staff_id=staff_id)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.order_by(*_resolve_flat_ordering(request))

        page = self.paginate_queryset(queryset)
        items = list(page) if page is not None else list(queryset)
        attendance_map = _build_attendance_map(items)
        serializer = self.get_serializer(
            items,
            many=True,
            context={**self.get_serializer_context(), 'attendance_map': attendance_map},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
