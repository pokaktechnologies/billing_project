from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models.functions import ExtractMonth
from django.db.models import Count
from django.utils import timezone
from ..models import Lead

class LeadsChartView(APIView):
    def get(self, request):
        year_param = request.query_params.get("year")
        first_lead = Lead.objects.order_by("created_at").first()
        last_lead = Lead.objects.order_by("-created_at").first()
        current_year = timezone.now().year

        min_year = 2023
        if first_lead:
            min_year = min(2023, first_lead.created_at.year)
        max_year = current_year
        if last_lead:
            max_year = max(current_year, last_lead.created_at.year)

        available_years = list(range(min_year, max_year + 1))

        if year_param:
            try:
                year = int(year_param)
            except ValueError:
                return Response({"error": "Year must be an integer"}, status=400)
        else:
            year = last_lead.created_at.year if last_lead else current_year

        if year == current_year:
            last_month = timezone.now().month
        else:
            last_month = 12
        available_months = list(range(1, last_month + 1))

        monthly_counts = (
            Lead.objects.filter(created_at__year=year)
            .annotate(month=ExtractMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        result = {m: 0 for m in available_months}

        for item in monthly_counts:
            month = item.get("month")
            if month in result:
                result[month] = item["count"]

        return Response({
            "year": year,
            "available_years": available_years,
            "available_months": available_months,
            "monthly_counts": [
                {"month": m, "count": result[m]} for m in available_months
            ]
        })