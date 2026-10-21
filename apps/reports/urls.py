"""URLs de la app reports bajo el prefijo /api/v1/."""

from django.urls import path

from apps.reports import views

urlpatterns = [
    path(
        'reports/spending/',
        views.SpendingReportView.as_view(),
        name='report-spending',
    ),
    path(
        'reports/investments/',
        views.InvestmentsReportView.as_view(),
        name='report-investments',
    ),
    path(
        'reports/loans/',
        views.LoansReportView.as_view(),
        name='report-loans',
    ),
    path(
        'reports/movements/',
        views.MovementsReportView.as_view(),
        name='report-movements',
    ),
]
