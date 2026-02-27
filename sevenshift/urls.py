from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

api_urlpatterns = [
    path('auth/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('vehicles/', include('vehicles.urls')),
    path('leasing/', include('leasing.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urlpatterns)),
    # Catch-all: serve the Vue SPA for any non-API, non-admin route. Must be last.
    re_path(
        r'^(?!api/|admin/|static/|media/).*$',
        TemplateView.as_view(template_name='index.html'),
        name='spa',
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
