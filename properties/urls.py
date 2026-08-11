from django.urls import path
from . import views

app_name = 'properties'
urlpatterns = [
    path('', views.PropertyListView.as_view(), name='list'),
    path('mine/', views.MyListingsView.as_view(), name='mine'),
    path('property/<slug:slug>/', views.PropertyDetailView.as_view(), name='detail'),
    path('create/', views.PropertyCreateView.as_view(), name='create'),
]
