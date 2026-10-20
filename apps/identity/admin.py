"""Administración de Django para la app identity."""

from django.contrib import admin

from apps.identity.exceptions import InvalidKYCResolution, KYCAlreadyResolved
from apps.identity.models import KYCVerification, Profile, User
from apps.identity.services import resolve_kyc


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Listado de usuarios de Presto."""

    list_display = ['id', 'email', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active']
    search_fields = ['email']
    readonly_fields = ['id', 'last_login', 'date_joined']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Listado de perfiles de usuario."""

    list_display = ['id', 'user', 'phone_number', 'country']
    search_fields = ['user__email']
    readonly_fields = ['id']


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    """Gestión de verificaciones KYC: la decisión se toma acá, no por API."""

    list_display = ['id', 'user', 'status', 'requested_at', 'resolved_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['user__email']
    readonly_fields = [
        'id',
        'user',
        'status',
        'requested_at',
        'resolved_at',
        'resolved_by_user_id',
        'documents',
    ]
    actions = ['approve_kyc', 'reject_kyc']

    @admin.action(description='Aprobar las verificaciones KYC seleccionadas')
    def approve_kyc(self, request, queryset):
        """Aprueba las verificaciones seleccionadas que estén pendientes."""
        self._resolve_selected(request, queryset, KYCVerification.Status.APPROVED)

    @admin.action(description='Rechazar las verificaciones KYC seleccionadas')
    def reject_kyc(self, request, queryset):
        """Rechaza las verificaciones seleccionadas que estén pendientes."""
        self._resolve_selected(request, queryset, KYCVerification.Status.REJECTED)

    def _resolve_selected(self, request, queryset, status):
        """Resuelve las verificaciones pendientes del queryset, omitiendo las ya resueltas."""
        resolved = 0
        for verification in queryset:
            try:
                resolve_kyc(
                    verification_id=verification.id,
                    status=status,
                    resolved_by_user_id=request.user.id,
                )
            except (KYCAlreadyResolved, InvalidKYCResolution):
                continue
            resolved += 1
        self.message_user(request, f'{resolved} verificación(es) resuelta(s).')
