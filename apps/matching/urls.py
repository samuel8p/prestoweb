"""URLs de la app matching bajo el prefijo /api/v1/."""

from django.urls import path

from apps.matching import views

urlpatterns = [
    path('matching/offers/', views.MatchingOfferListView.as_view(), name='matching-offers'),
    path(
        'matching/comparisons/',
        views.OfferComparisonView.as_view(),
        name='matching-comparisons',
    ),
]
