from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("", views.dashboard, name="dashboard"),
    path("contract/", views.contract_setup, name="contract_setup"),
    path("entry/new/", views.entry_create, name="entry_create"),
    path("history/", views.history, name="history"),
    path("profit/", views.profit_summary, name="profit_summary"),
    path("cashflow/", views.cashflow, name="cashflow"),
    path("entry/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entry/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
]
