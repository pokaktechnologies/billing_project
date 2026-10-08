"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from project_management.views import ProjectNoteListCreateView, ProjectNoteDetailView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('leads/', include('leads.urls')),
    path('project_management/', include('project_management.urls')),
    path('finance/', include('finance.urls')),
    path('hr/', include('hr_section.urls')),
    path('certificate/', include('certificates.urls')),
    path('attendance/', include('attendance.urls')),
    path('chat/', include('chat.urls')),
    path('activity_log/', include('activity_logs.urls')),

    path('internship/', include('internship.urls')),
    path('payroll/', include('payroll.urls')),

    # Direct project notes routes
    path('projects/<int:project_id>/notes/', ProjectNoteListCreateView.as_view(), name='direct_project_notes_list_create'),
    path('projects/<int:project_id>/notes/<int:note_id>/', ProjectNoteDetailView.as_view(), name='direct_project_notes_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)