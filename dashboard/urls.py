from django.urls import path
from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.AdminDashboardView.as_view(), name='admin'),
    path('approve/<int:pk>/', views.approve_property, name='approve'),
    path('reject/<int:pk>/', views.reject_property, name='reject'),
]
