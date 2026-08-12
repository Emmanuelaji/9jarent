# inspections/urls.py

from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    path('', views.my_inspections, name='list'),
    path('<int:pk>/', views.inspection_detail, name='detail'),
    path('request/<int:property_id>/', views.request_inspection, name='request'),
    path('<int:pk>/accept/', views.accept_inspection, name='accept'),
    path('<int:pk>/decline/', views.decline_inspection, name='decline'),
    path('<int:pk>/complete/', views.complete_inspection, name='complete'),
    path('<int:pk>/cancel/', views.cancel_inspection, name='cancel'),
]
