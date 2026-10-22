"""URLs de la app notifications bajo el prefijo /api/v1/."""

from django.urls import path

from apps.notifications import views

urlpatterns = [
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path(
        'notifications/read-all/',
        views.NotificationReadAllView.as_view(),
        name='notifications-read-all',
    ),
    path(
        'notifications/unread-count/',
        views.NotificationUnreadCountView.as_view(),
        name='notifications-unread-count',
    ),
    path(
        'notifications/<uuid:notification_id>/read/',
        views.NotificationReadView.as_view(),
        name='notifications-read',
    ),
    path(
        'notifications/preferences/',
        views.NotificationPreferenceView.as_view(),
        name='notifications-preferences',
    ),
]
