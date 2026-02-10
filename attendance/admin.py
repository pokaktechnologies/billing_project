from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(DailyAttendance)
admin.site.register(AttendanceSession)
admin.site.register(Holiday)
admin.site.register(LeaveRequest)


