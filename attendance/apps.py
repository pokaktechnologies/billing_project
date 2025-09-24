from django.apps import AppConfig
from . import scheduler

class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'
    def ready(self):
        scheduler.start()
