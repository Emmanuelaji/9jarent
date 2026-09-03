from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # Public browsing
    path('', views.PropertyListView.as_view(), name='home'),
    path('properties/', views.PropertyListView.as_view(), name='list'),
    path('properties/<slug:slug>/', views.PropertyDetailView.as_view(), name='detail'),
    path('ajax/lgas/', views.lgas_for_state, name='ajax_lgas'),

    # Agent property management (requires approved agent)
    path('agent/dashboard/', views.AgentDashboardView.as_view(), name='agent_dashboard'),
    path('agent/properties/', views.MyListingsView.as_view(), name='mine'),
    path('agent/properties/drafts/', views.DraftListView.as_view(), name='drafts'),
    path('agent/properties/add/', views.PropertyCreateView.as_view(), name='create'),
    path('agent/properties/<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='edit'),
    path('agent/properties/<int:pk>/submit/', views.submit_property, name='submit'),
    path('agent/properties/<int:pk>/resubmit/', views.resubmit_property, name='resubmit'),
    path('agent/properties/<int:pk>/rented/', views.mark_property_rented, name='rented'),
    path('agent/properties/<int:pk>/available/', views.mark_property_available, name='available'),
    path('agent/properties/<int:pk>/archive/', views.archive_property, name='archive'),
    path('agent/properties/<int:pk>/images/<int:image_id>/delete/', views.delete_property_image, name='delete_image'),
]