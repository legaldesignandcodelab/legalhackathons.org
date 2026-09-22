from django.contrib import admin
from django.urls import path, include, re_path
from registrations.views import protected_media

admin.site.site_header = 'Legal Hackathon Admin'
admin.site.site_title = 'Legal Hackathon'
admin.site.index_title = 'Registration Management'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('registrations.urls')),
    re_path(r'^media/(?P<path>.+)$', protected_media, name='protected_media'),
]
