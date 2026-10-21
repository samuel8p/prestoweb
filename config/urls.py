from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.identity.urls')),
    path('api/v1/', include('apps.ledger.urls')),
    path('api/v1/', include('apps.offers.urls')),
    path('api/v1/', include('apps.matching.urls')),
    path('api/v1/', include('apps.loans.urls')),
    path('api/v1/', include('apps.investments.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
