from django.utils import timezone
from .models import PayrollPeriod

def create_monthly_payroll_period():
    """
    Creates a PayrollPeriod record for the current month at the beginning of the month.
    """
    now = timezone.localtime()
    target_month = now.strftime("%Y-%m")
    
    period, created = PayrollPeriod.objects.get_or_create(
        month=target_month,
        defaults={"status": "open"}
    )
    
    if created:
        print(f"✅ Automated System: Created PayrollPeriod for {target_month}")
    else:
        print(f"ℹ️ Automated System: PayrollPeriod for {target_month} already exists.")
