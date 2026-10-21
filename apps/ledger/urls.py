"""URLs de la app ledger bajo el prefijo /api/v1/."""

from django.urls import path

from apps.ledger import views

urlpatterns = [
    path('ledger/accounts/', views.AccountListCreateView.as_view(), name='ledger-accounts'),
    path(
        'ledger/accounts/<uuid:account_id>/balance/',
        views.AccountBalanceView.as_view(),
        name='ledger-account-balance',
    ),
    path(
        'ledger/transactions/',
        views.TransactionListCreateView.as_view(),
        name='ledger-transactions',
    ),
    path(
        'ledger/transactions/<uuid:transaction_id>/',
        views.TransactionDetailView.as_view(),
        name='ledger-transaction-detail',
    ),
]
