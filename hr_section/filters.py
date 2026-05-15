import django_filters
from .models import OfferLetter


class OfferLetterFilter(django_filters.FilterSet):
    # ── Exact filters ─────────────────────────────────────────────────────────
    status    = django_filters.CharFilter(field_name="status",    lookup_expr="exact")
    duty_type = django_filters.CharFilter(field_name="duty_type", lookup_expr="exact")

    # ── Search / icontains ────────────────────────────────────────────────────
    candidate_name  = django_filters.CharFilter(field_name="candidate_name",  lookup_expr="icontains")
    candidate_email = django_filters.CharFilter(field_name="candidate_email", lookup_expr="icontains")
    job_title       = django_filters.CharFilter(field_name="job_title",       lookup_expr="icontains")
    company_name    = django_filters.CharFilter(field_name="company_name",    lookup_expr="icontains")

    # ── Boolean ───────────────────────────────────────────────────────────────
    is_target_based = django_filters.BooleanFilter(field_name="is_target_based")

    # ── Date range (joining_date) ─────────────────────────────────────────────
    joining_date_from = django_filters.DateFilter(field_name="joining_date", lookup_expr="gte")
    joining_date_to   = django_filters.DateFilter(field_name="joining_date", lookup_expr="lte")

    # ── Salary range ──────────────────────────────────────────────────────────
    salary_min = django_filters.NumberFilter(field_name="monthly_salary", lookup_expr="gte")
    salary_max = django_filters.NumberFilter(field_name="monthly_salary", lookup_expr="lte")

    # ── Created date range ────────────────────────────────────────────────────
    created_from = django_filters.DateFilter(field_name="created_at__date", lookup_expr="gte")
    created_to   = django_filters.DateFilter(field_name="created_at__date", lookup_expr="lte")

    class Meta:
        model  = OfferLetter
        fields = [
            "status", "duty_type", "candidate_name", "candidate_email",
            "job_title", "company_name", "is_target_based",
            "joining_date_from", "joining_date_to",
            "salary_min", "salary_max",
            "created_from", "created_to",
        ]