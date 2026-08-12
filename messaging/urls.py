# messaging/urls.py

from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('<int:pk>/', views.inbox, name='detail'),
    path('start/<int:property_id>/', views.start_conversation, name='start'),
]
