from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/read/', views.mark_notification_read, name='mark_read'),
    path('<int:pk>/go/', views.notification_redirect, name='redirect'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]
