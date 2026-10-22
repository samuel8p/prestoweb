"""Serializers de la app identity: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.identity.models import KYCVerification, Profile, User


class RegisterSerializer(serializers.Serializer):
    """Datos necesarios para registrar un usuario."""

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )


class LoginSerializer(serializers.Serializer):
    """Credenciales de acceso."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class TokenRefreshSerializer(serializers.Serializer):
    """Body del refresh: el token que se quiere rotar."""

    refresh = serializers.CharField(
        help_text='El refresh token que se renueva (queda en blacklist).',
    )


class UserSerializer(serializers.ModelSerializer):
    """Datos públicos de un usuario."""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'alias']
        read_only_fields = ['id', 'email', 'alias']


class AliasSerializer(serializers.Serializer):
    """El alias que el usuario se pone o cambia."""

    alias = serializers.CharField(
        max_length=20,
        help_text=(
            'Identificador público: 6 a 20 caracteres, minúsculas, dígitos, '
            'punto, guion o guion bajo; empieza y termina con letra o dígito.'
        ),
    )


class AliasResponseSerializer(serializers.Serializer):
    """El alias del usuario (null si no tiene)."""

    alias = serializers.CharField(
        allow_null=True,
        required=False,
        help_text='El alias del usuario, o null si todavía no tiene.',
    )


class ProfileSerializer(serializers.ModelSerializer):
    """Datos del perfil de un usuario."""

    class Meta:
        model = Profile
        fields = ['id', 'phone_number', 'date_of_birth', 'country']
        read_only_fields = ['id']


class MeUpdateSerializer(serializers.Serializer):
    """Campos del perfil que el usuario puede actualizar sobre sí mismo."""

    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=32,
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    country = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2,
        validators=[Profile.country_validator],
    )


class KYCRequestSerializer(serializers.Serializer):
    """Metadata de documentos para solicitar la verificación KYC."""

    documents = serializers.JSONField()


class KYCVerificationSerializer(serializers.ModelSerializer):
    """Estado de una verificación KYC."""

    class Meta:
        model = KYCVerification
        fields = [
            'id',
            'status',
            'requested_at',
            'resolved_at',
            'resolved_by_user_id',
            'documents',
        ]
        read_only_fields = fields


class LoginResponseSerializer(serializers.Serializer):
    """Respuesta del login con tokens y datos del usuario."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
