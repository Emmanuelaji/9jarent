from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('property/<int:property_id>/', views.report_property, name='report_property'),
    path('agent/<int:agent_id>/', views.report_agent, name='report_agent'),
]
