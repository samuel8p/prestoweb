"""Vistas de la API de identity."""

from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from apps.identity.exceptions import EmailAlreadyRegistered, PendingKYCExists, WeakPassword
from apps.identity.permissions import LoginThrottle, RegisterThrottle
from apps.identity.selectors import get_kyc_by_id, get_kyc_for_user, get_profile
from apps.identity.serializers import (
    KYCRequestSerializer,
    KYCVerificationSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    MeUpdateSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.identity.services import register_user, submit_kyc, update_profile


def build_me_payload(user) -> dict:
    """Arma la respuesta del perfil propio con los datos del usuario y su perfil."""
    payload = UserSerializer(user).data
    profile = get_profile(user_id=user.id)
    payload['profile'] = ProfileSerializer(profile).data if profile else None
    return payload


class RegisterView(APIView):
    """Alta de usuarios."""

    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]
    throttle_scope = 'register'

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer},
        summary='Registrar un usuario',
    )
    def post(self, request):
        """Registra un usuario nuevo y devuelve sus datos."""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = register_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
            )
        except EmailAlreadyRegistered as exc:
            raise ValidationError({'email': [str(exc)]}) from exc
        except WeakPassword as exc:
            raise ValidationError({'password': [str(exc)]}) from exc
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Autenticación con JWT."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]
    throttle_scope = 'login'

    @extend_schema(
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
        summary='Iniciar sesión y obtener tokens JWT',
    )
    def post(self, request):
        """Valida las credenciales y devuelve access y refresh tokens."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            raise AuthenticationFailed('Credenciales inválidas.')
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            }
        )


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """Renueva el access token rotando el refresh token."""

    @extend_schema(
        request=None,
        responses={200: LoginResponseSerializer},
        summary='Renovar el access token rotando el refresh token',
    )
    def post(self, request, *args, **kwargs):
        """Rota el refresh token, blacklista el anterior y devuelve los nuevos tokens."""
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    """Perfil del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer}, summary='Ver el propio perfil')
    def get(self, request):
        """Devuelve los datos del usuario autenticado y su perfil."""
        return Response(build_me_payload(request.user))

    @extend_schema(
        request=MeUpdateSerializer,
        responses={200: UserSerializer},
        summary='Actualizar el propio perfil',
    )
    def patch(self, request):
        """Actualiza los datos del perfil del usuario autenticado."""
        serializer = MeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_profile(user=request.user, changes=serializer.validated_data)
        return Response(build_me_payload(request.user))


class KycView(APIView):
    """Estado y solicitud de verificación KYC del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: KYCVerificationSerializer},
        summary='Ver el estado KYC propio',
        operation_id='kyc_list',
    )
    def get(self, request):
        """Devuelve la verificación KYC vigente del usuario, o null si no tiene."""
        verification = get_kyc_for_user(user_id=request.user.id)
        if verification is None:
            return Response(None, status=status.HTTP_200_OK)
        return Response(KYCVerificationSerializer(verification).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=KYCRequestSerializer,
        responses={201: KYCVerificationSerializer},
        summary='Solicitar la verificación KYC',
    )
    def post(self, request):
        """Crea una solicitud de verificación KYC en estado pending."""
        serializer = KYCRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            verification = submit_kyc(
                user=request.user,
                documents=serializer.validated_data['documents'],
            )
        except PendingKYCExists as exc:
            raise ValidationError({'documents': [str(exc)]}) from exc
        return Response(
            KYCVerificationSerializer(verification).data,
            status=status.HTTP_201_CREATED,
        )


class KycDetailView(APIView):
    """Detalle de una verificación KYC propia."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: KYCVerificationSerializer},
        summary='Ver una verificación KYC propia',
        operation_id='kyc_retrieve',
    )
    def get(self, request, verification_id):
        """Devuelve la verificación KYC indicada si pertenece al usuario."""
        verification = get_kyc_by_id(verification_id=verification_id, user_id=request.user.id)
        if verification is None:
            raise NotFound('La verificación KYC no existe.')
        return Response(KYCVerificationSerializer(verification).data, status=status.HTTP_200_OK)
