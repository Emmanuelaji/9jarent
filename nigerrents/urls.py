from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

handler400 = 'nigerrents.views.handler400'
handler403 = 'nigerrents.views.handler403'
handler404 = 'nigerrents.views.handler404'
handler500 = 'nigerrents.views.handler500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('properties.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('favourites/', include('favourites.urls')),
    path('notifications/', include('notifications.urls')),
    path('reports/', include('reports.urls')),
    path('messages/', include('messaging.urls')),
    path('inspections/', include('inspections.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)