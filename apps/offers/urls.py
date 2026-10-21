"""URLs de la app offers bajo el prefijo /api/v1/."""

from django.urls import path

from apps.offers import views

urlpatterns = [
    path('offers/', views.OfferListCreateView.as_view(), name='offers'),
    path('offers/<uuid:offer_id>/', views.OfferDetailView.as_view(), name='offer-detail'),
]
