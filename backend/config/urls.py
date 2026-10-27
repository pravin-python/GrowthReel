"""Root URL configuration for the GrowthReel Django backend."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.users.urls")),
    path("blog/", include("apps.blog.urls")),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
