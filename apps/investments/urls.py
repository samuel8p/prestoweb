"""URLs de la app investments bajo el prefijo /api/v1/."""

from django.urls import path

from apps.investments import views

urlpatterns = [
    path(
        'investments/products/',
        views.InvestmentProductListView.as_view(),
        name='investment-products',
    ),
    path(
        'investments/positions/',
        views.PositionListCreateView.as_view(),
        name='investment-positions',
    ),
    path(
        'investments/positions/<uuid:position_id>/',
        views.PositionDetailView.as_view(),
        name='investment-position-detail',
    ),
]
