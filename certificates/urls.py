from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.CertificateListCreateView.as_view(), name='certificate-list-create'),
    path('generate/<int:pk>/', views.CertificateDetailView.as_view(), name='certificate-detail'),
    path('generate/<int:pk>/proof/', views.CertificateProofView.as_view(), name='certificate-proof'),
    path('generate/<int:pk>/data/', views.CertificateDataView.as_view(), name='certificate-data'),
    path('generate/<int:pk>/send/', views.CertificateSendView.as_view(), name='certificate-send'),
    path('generate/<int:pk>/download/', views.CertificateDownloadView.as_view(), name='certificate-download'),
    # Staff endpoints
    path('staff/', views.StaffListView.as_view(), name='staff-list'),
    path('staff/<int:id>/', views.StaffDetailView.as_view(), name='staff-detail'),
    path('employee-certificates/', views.EmployeeCertificateCreateView.as_view(), name='employee-certificate-create'),
]