from django.contrib import admin
from .models import DailyAttendance, AttendanceSession, Holiday

# Register your models here.
admin.site.register(DailyAttendance)
admin.site.register(AttendanceSession)
admin.site.register(Holiday)

