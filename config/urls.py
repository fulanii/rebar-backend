"""Root URL configuration. Each app owns a urls.py and is mounted here."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from authentication.views import CustomTokenBlacklistView, CustomTokenObtainPairView, CustomTokenRefreshView

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("token/blacklist/", CustomTokenBlacklistView.as_view(), name="token_blacklist"),
    path("auth/", include("authentication.urls")),
    path("admin/", include("administration.urls")),
]

if settings.ENABLE_API_DOCS:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
        path("admin/", admin.site.urls),
    ]
