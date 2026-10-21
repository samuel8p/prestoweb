"""Vistas de la API de offers."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import InvalidAmount, KYCNotCompleted
from apps.core.pagination import StandardPagination
from apps.identity.permissions import KycApprovedForUnsafeMethods
from apps.offers.exceptions import OfferNotEditable, OfferNotFound
from apps.offers.models import Offer
from apps.offers.permissions import HasApprovedKyc
from apps.offers.selectors import get_offer, list_offers_for_lender
from apps.offers.serializers import (
    CreateOfferSerializer,
    OfferSerializer,
    UpdateOfferSerializer,
)
from apps.offers.services import create_offer, expire_offer, update_offer


class OfferListCreateView(KycApprovedForUnsafeMethods, APIView):
    """Ofertas publicadas por el prestamista autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: OfferSerializer},
        summary='Listar las ofertas propias',
        operation_id='offers_list',
    )
    def get(self, request):
        """Lista las ofertas publicadas por el usuario autenticado."""
        offers = list_offers_for_lender(lender_user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(offers, request, view=self)
        return paginator.get_paginated_response(OfferSerializer(page, many=True).data)

    @extend_schema(
        request=CreateOfferSerializer,
        responses={201: OfferSerializer},
        summary='Publicar una oferta de préstamo',
    )
    def post(self, request):
        """Publica una oferta de préstamo. No reserva fondos."""
        serializer = CreateOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            offer = create_offer(
                lender_user_id=request.user.id,
                amount=data['amount'],
                currency=data['currency'],
                interest_rate=data['interest_rate'],
                term_months=data['term_months'],
                requirements=data.get('requirements', ''),
            )
        except KYCNotCompleted as exc:
            raise PermissionDenied(str(exc)) from exc
        except InvalidAmount as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        return Response(OfferSerializer(offer).data, status=status.HTTP_201_CREATED)


class OfferDetailView(APIView):
    """Detalle y edición de una oferta propia."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OfferSerializer},
        summary='Ver una oferta propia',
        operation_id='offers_retrieve',
    )
    def get(self, request, offer_id):
        """Devuelve la oferta del prestamista autenticado."""
        offer = get_offer(offer_id=offer_id, lender_user_id=request.user.id)
        if offer is None:
            raise NotFound('La oferta no existe.')
        return Response(OfferSerializer(offer).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UpdateOfferSerializer,
        responses={200: OfferSerializer},
        summary='Actualizar o expirar una oferta propia',
    )
    def patch(self, request, offer_id):
        """Actualiza los datos de la oferta o la expira."""
        serializer = UpdateOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get('status') == Offer.Status.EXPIRED:
            try:
                offer = expire_offer(offer_id=offer_id, lender_user_id=request.user.id)
            except OfferNotFound as exc:
                raise NotFound(str(exc)) from exc
            except OfferNotEditable as exc:
                raise ValidationError({'detail': [str(exc)]}) from exc
            return Response(OfferSerializer(offer).data, status=status.HTTP_200_OK)
        try:
            offer = update_offer(
                offer_id=offer_id,
                lender_user_id=request.user.id,
                amount=data.get('amount'),
                currency=data.get('currency'),
                interest_rate=data.get('interest_rate'),
                term_months=data.get('term_months'),
                requirements=data.get('requirements'),
            )
        except OfferNotFound as exc:
            raise NotFound(str(exc)) from exc
        except OfferNotEditable as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except KYCNotCompleted as exc:
            raise PermissionDenied(str(exc)) from exc
        except InvalidAmount as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        return Response(OfferSerializer(offer).data, status=status.HTTP_200_OK)
