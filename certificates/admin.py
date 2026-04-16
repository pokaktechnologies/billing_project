from django.contrib import admin

# Register your models here.

from .models import Certificate, CertificateHistory

admin.site.register(Certificate)
admin.site.register(CertificateHistory)