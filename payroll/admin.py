from django.contrib import admin
from .models import *

admin.site.register(PayrollPeriod)
admin.site.register(Payroll)
admin.site.register(AttendanceSummary)

# Register your models here.
