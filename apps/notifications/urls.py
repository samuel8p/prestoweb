"""URLs de la app notifications bajo el prefijo /api/v1/."""

from django.urls import path

from apps.notifications import views

urlpatterns = [
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path(
        'notifications/preferences/',
        views.NotificationPreferenceView.as_view(),
        name='notifications-preferences',
    ),
]
