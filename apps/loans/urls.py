"""URLs de la app loans bajo el prefijo /api/v1/."""

from django.urls import path

from apps.loans import views

urlpatterns = [
    path('loans/', views.LoanListCreateView.as_view(), name='loans'),
    path('loans/<uuid:loan_id>/', views.LoanDetailView.as_view(), name='loan-detail'),
    path(
        'loans/<uuid:loan_id>/installments/<int:number>/pay/',
        views.InstallmentPayView.as_view(),
        name='loan-installment-pay',
    ),
]
