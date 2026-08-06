from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = 'Legal Hackathon Admin'
admin.site.site_title = 'Legal Hackathon'
admin.site.index_title = 'Registration Management'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('registrations.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
