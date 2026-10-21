"""Vistas de la API de matching (app de solo lectura)."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.matching.exceptions import NotEnoughOffersToCompare, OfferNotFound
from apps.matching.selectors import compare_offers, search_offers
from apps.matching.serializers import (
    CompareOffersSerializer,
    OfferComparisonSerializer,
    OfferMatchSerializer,
    SearchOffersQuerySerializer,
)


class MatchingOfferListView(APIView):
    """Búsqueda de ofertas activas del marketplace."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        parameters=[SearchOffersQuerySerializer],
        responses={200: OfferMatchSerializer},
        summary='Buscar ofertas activas',
    )
    def get(self, request):
        """Busca ofertas activas con los filtros de la query string."""
        serializer = SearchOffersQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        offers = search_offers(
            currency=data.get('currency'),
            amount_min=data.get('amount_min'),
            amount_max=data.get('amount_max'),
            max_rate=data.get('max_rate'),
            term_months=data.get('term_months'),
            ordering=data.get('ordering', 'rate'),
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(offers, request, view=self)
        return paginator.get_paginated_response(OfferMatchSerializer(page, many=True).data)


class OfferComparisonView(APIView):
    """Comparación de dos o más ofertas."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CompareOffersSerializer,
        responses={200: OfferComparisonSerializer},
        summary='Comparar ofertas',
    )
    def post(self, request):
        """Compara las ofertas indicadas y devuelve sus números."""
        serializer = CompareOffersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            comparison = compare_offers(offer_ids=serializer.validated_data['offer_ids'])
        except NotEnoughOffersToCompare as exc:
            raise ValidationError({'offer_ids': [str(exc)]}) from exc
        except OfferNotFound as exc:
            raise NotFound(str(exc)) from exc
        return Response(
            OfferComparisonSerializer(comparison, many=True).data,
            status=status.HTTP_200_OK,
        )
