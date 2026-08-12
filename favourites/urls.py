# favourites/urls.py

from django.urls import path
from . import views

app_name = 'favourites'

urlpatterns = [
    path('', views.FavouriteListView.as_view(), name='list'),
    path('toggle/<int:property_id>/', views.toggle_favourite, name='toggle'),
]
