from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(ProjectManagement)
admin.site.register(Member)
admin.site.register(Stack)
admin.site.register(ProjectMember)
admin.site.register(Task)
admin.site.register(ClientContract)