# dashboard/urls.py

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.AdminDashboardView.as_view(), name='admin'),

    # Property moderation
    path('properties/', views.PropertyModerationListView.as_view(), name='properties_list'),
    path('properties/<int:pk>/approve/', views.approve_property, name='approve_property'),
    path('properties/<int:pk>/reject/', views.reject_property, name='reject_property'),
    path('properties/<int:pk>/unpublish/', views.unpublish_property, name='unpublish_property'),

    # Messaging oversight (metadata only - see ConversationModerationListView)
    path('messages/', views.ConversationModerationListView.as_view(), name='messages_list'),

    # Agent moderation
    path('agents/pending/', views.PendingAgentsView.as_view(), name='agents_pending'),
    path('agents/approved/', views.ApprovedAgentsView.as_view(), name='agents_approved'),
    path('agents/rejected/', views.RejectedAgentsView.as_view(), name='agents_rejected'),
    path('agents/suspended/', views.SuspendedAgentsView.as_view(), name='agents_suspended'),
    path('agents/<int:pk>/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('agents/<int:pk>/approve/', views.approve_agent, name='approve_agent'),
    path('agents/<int:pk>/reject/', views.reject_agent, name='reject_agent'),
    path('agents/<int:pk>/suspend/', views.suspend_agent, name='suspend_agent'),
    path('agents/<int:pk>/reactivate/', views.reactivate_agent, name='reactivate_agent'),

    # Inspection management
    path('inspections/', views.InspectionListView.as_view(), name='inspections_list'),
    path('inspections/<int:pk>/', views.InspectionDetailView.as_view(), name='inspection_detail'),

    # Report management
    path('reports/', views.ReportsListView.as_view(), name='reports_list'),
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('reports/<int:pk>/resolve/', views.resolve_report, name='resolve_report'),
]