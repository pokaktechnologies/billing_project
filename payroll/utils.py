from .models import PayrollPeriod

def is_payroll_locked(date):
    month = date.strftime("%Y-%m")
    return PayrollPeriod.objects.filter(month=month, is_locked=True).exists()
