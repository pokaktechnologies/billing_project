from django.contrib import admin

# Register your models here.

from .models import Certificate, CertificateHistory, CertificateRecord, SignatoryPerson

admin.site.register(Certificate)
admin.site.register(CertificateHistory)
admin.site.register(CertificateRecord)
admin.site.register(SignatoryPerson)