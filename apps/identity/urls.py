"""URLs de la app identity bajo el prefijo /api/v1/."""

from django.urls import path

from apps.identity import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/token/refresh/', views.TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    path('kyc/', views.KycView.as_view(), name='kyc'),
    path('kyc/<uuid:verification_id>/', views.KycDetailView.as_view(), name='kyc-detail'),
]
