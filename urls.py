# reports/urls.py

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.list_reports, name='list_reports'),
    path('<int:report_id>/generate/', views.generate_report, name='generate_report'),
]
