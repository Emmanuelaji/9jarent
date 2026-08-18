from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('property/<int:property_id>/', views.report_property, name='submit'),
    path('agent/<int:agent_id>/', views.report_agent, name='submit_agent'),
]
