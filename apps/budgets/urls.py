"""URLs de la app budgets bajo el prefijo /api/v1/."""

from django.urls import path

from apps.budgets import views

urlpatterns = [
    path('budgets/', views.BudgetListCreateView.as_view(), name='budgets'),
    path('budgets/<uuid:budget_id>/', views.BudgetDetailView.as_view(), name='budget-detail'),
    path(
        'budgets/<uuid:budget_id>/status/',
        views.BudgetStatusView.as_view(),
        name='budget-status',
    ),
    path(
        'budgets/categories/',
        views.CategoryListCreateView.as_view(),
        name='budget-categories',
    ),
    path(
        'budgets/categories/<uuid:category_id>/',
        views.CategoryDetailView.as_view(),
        name='budget-category-detail',
    ),
    path('budgets/expenses/', views.ExpenseListCreateView.as_view(), name='budget-expenses'),
]
