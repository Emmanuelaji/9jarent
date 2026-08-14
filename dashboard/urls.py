
# dashboard/urls.py

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.AdminDashboardView.as_view(), name='admin'),
    
    # Property moderation
    path('properties/<int:pk>/approve/', views.approve_property, name='approve_property'),
    path('properties/<int:pk>/reject/', views.reject_property, name='reject_property'),
    path('properties/<int:pk>/unpublish/', views.unpublish_property, name='unpublish_property'),
    
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
]
