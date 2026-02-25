from __future__ import annotations

import json
from datetime import timedelta

from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods

from .auth import SESSION_KEY, require_auth, verify_login
from .forms import CashTransactionForm, ContractForm, DailyEntryForm
from .models import CashTransaction, Contract, DailyEntry


def get_active_contract():
    return Contract.objects.filter(is_active=True).order_by("-created_at").first()


# =========================
# AUTH
# =========================
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "POST":
        access_code = request.POST.get("access_code", "").strip()
        pin = request.POST.get("pin", "").strip()

        if verify_login(access_code, pin):
            request.session[SESSION_KEY] = True
            return redirect(reverse("dashboard"))

        return render(request, "core/login.html", {"error": "Access Code atau PIN salah."})

    return render(request, "core/login.html")


def logout_view(request):
    request.session.flush()
    return redirect(reverse("login"))


# =========================
# DASHBOARD
# =========================
@require_auth
def dashboard(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    entries_qs = DailyEntry.objects.filter(contract=c).order_by("date")

    agg = entries_qs.aggregate(
        total_portions=Sum("portions"),
        mat=Sum("cost_material"),
        lab=Sum("cost_labor"),
        ovh=Sum("cost_overhead"),
    )

    total_portions = int(agg["total_portions"] or 0)
    sum_mat = float(agg["mat"] or 0)
    sum_lab = float(agg["lab"] or 0)
    sum_ovh = float(agg["ovh"] or 0)
    total_cost = sum_mat + sum_lab + sum_ovh

    price = float(c.price_per_portion)
    revenue = total_portions * price
    profit = revenue - total_cost

    cpp = (total_cost / total_portions) if total_portions > 0 else 0.0
    mpp = price - cpp

    target_margin_pct = float(c.target_margin_pct)
    target_margin_per_portion = price * (target_margin_pct / 100.0)
    target_cost_per_portion = price - target_margin_per_portion

    target_total_portions = int(c.target_portions_per_day * c.duration_days)
    target_profit_total = target_margin_per_portion * target_total_portions

    progress_portions = (
        (total_portions / target_total_portions * 100.0) if target_total_portions > 0 else 0.0
    )

    projected_profit = (price - cpp) * target_total_portions if target_total_portions > 0 else 0.0
    dev_vs_target_pct = (
        ((projected_profit - target_profit_total) / target_profit_total * 100.0)
        if target_profit_total
        else 0.0
    )

    # chart data
    labels: list[str] = []
    margin_series: list[float] = []
    target_series: list[float] = []

    for e in entries_qs:
        labels.append(e.date.strftime("%d %b"))
        portions = float(e.portions or 0)
        tcost = float(e.total_cost)
        cpp_day = (tcost / portions) if portions > 0 else 0.0
        margin_series.append(round(price - cpp_day, 2))
        target_series.append(round(target_margin_per_portion, 2))

    # early warning: 3 hari terakhir di bawah target margin/porsi
    warn = False
    warn_text = None
    last3 = list(entries_qs.order_by("-date")[:3])
    if len(last3) == 3:
        below = 0
        for e in last3:
            portions = float(e.portions or 0)
            tcost = float(e.total_cost)
            cpp_day = (tcost / portions) if portions > 0 else 0.0
            mpp_day = price - cpp_day
            if mpp_day < target_margin_per_portion:
                below += 1
        if below == 3:
            warn = True
            warn_text = "Margin di bawah target 3 hari berturut-turut."

    ctx = {
        "contract": c,
        "kpi_mpp": mpp,
        "kpi_cpp": cpp,
        "kpi_profit": profit,
        "kpi_projected_profit": projected_profit,
        "price": price,
        "target_margin_per_portion": target_margin_per_portion,
        "target_cost_per_portion": target_cost_per_portion,
        "total_portions": total_portions,
        "revenue": revenue,
        "total_cost": total_cost,
        "progress_portions": progress_portions,
        "target_total_portions": target_total_portions,
        "target_profit_total": target_profit_total,
        "dev_vs_target_pct": dev_vs_target_pct,
        "sum_mat": sum_mat,
        "sum_lab": sum_lab,
        "sum_ovh": sum_ovh,
        "chart_labels_json": json.dumps(labels),
        "chart_margin_json": json.dumps(margin_series),
        "chart_target_json": json.dumps(target_series),
        "donut_cost_json": json.dumps([sum_mat, sum_lab, sum_ovh]),
        "warn": warn,
        "warn_text": warn_text,
    }

    return render(request, "core/dashboard.html", ctx)


# =========================
# PROFIT SUMMARY
# =========================
@require_auth
def profit_summary(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    entries = DailyEntry.objects.filter(contract=c)

    agg = entries.aggregate(
        portions=Sum("portions"),
        mat=Sum("cost_material"),
        lab=Sum("cost_labor"),
        ovh=Sum("cost_overhead"),
    )

    total_portions = float(agg["portions"] or 0)
    total_cost = float((agg["mat"] or 0) + (agg["lab"] or 0) + (agg["ovh"] or 0))

    price = float(c.price_per_portion)
    revenue = total_portions * price
    profit = revenue - total_cost
    margin_pct = (profit / revenue * 100) if revenue else 0.0

    return render(
        request,
        "core/profit_summary.html",
        {
            "contract": c,
            "revenue": revenue,
            "total_cost": total_cost,
            "profit": profit,
            "margin_pct": margin_pct,
        },
    )


# =========================
# CONTRACT SETUP
# =========================
@require_auth
@require_http_methods(["GET", "POST"])
def contract_setup(request):
    c = get_active_contract()

    if request.method == "POST":
        form = ContractForm(request.POST, instance=c)
        if form.is_valid():
            Contract.objects.update(is_active=False)
            obj = form.save(commit=False)
            obj.is_active = True
            obj.save()
            return redirect("dashboard")
    else:
        form = ContractForm(instance=c)

    return render(request, "core/contract_form.html", {"form": form})


# =========================
# DAILY ENTRY CRUD
# =========================
@require_auth
@require_http_methods(["GET", "POST"])
def entry_create(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    if request.method == "POST":
        form = DailyEntryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.contract = c

            # AUTO ISI paid_amount kalau Tunai dan kosong
            if obj.payment_type == "CASH" and (obj.paid_amount is None or float(obj.paid_amount) == 0):
                obj.paid_amount = float(obj.portions or 0) * float(c.price_per_portion)

            obj.save()
            return redirect("history")
    else:
        form = DailyEntryForm()

    return render(request, "core/entry_form.html", {"form": form, "contract": c, "is_edit": False})


@require_auth
def history(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    entries = DailyEntry.objects.filter(contract=c).order_by("-date", "-id")
    return render(request, "core/history.html", {"contract": c, "entries": entries})


@require_auth
@require_http_methods(["GET", "POST"])
def entry_edit(request, pk):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    obj = get_object_or_404(DailyEntry, pk=pk, contract=c)

    if request.method == "POST":
        form = DailyEntryForm(request.POST, instance=obj)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.contract = c

            # auto isi paid_amount jika tunai & kosong
            if edited.payment_type == "CASH" and (edited.paid_amount is None or float(edited.paid_amount) == 0):
                edited.paid_amount = float(edited.portions or 0) * float(c.price_per_portion)

            edited.save()
            return redirect("history")
    else:
        form = DailyEntryForm(instance=obj)

    return render(
        request,
        "core/entry_form.html",
        {
            "form": form,
            "contract": c,
            "is_edit": True,
            "entry": obj,
        },
    )


@require_auth
@require_http_methods(["GET", "POST"])
def entry_delete(request, pk):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    obj = get_object_or_404(DailyEntry, pk=pk, contract=c)

    if request.method == "POST":
        obj.delete()
        return redirect("history")

    return render(request, "core/entry_confirm_delete.html", {"entry": obj, "contract": c})


# =========================
# CASHFLOW (from DailyEntry)
# =========================
@require_auth
def cashflow(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    qs = DailyEntry.objects.filter(contract=c).order_by("date")

    price = float(c.price_per_portion)

    sales_total = sum(float(e.portions or 0) * price for e in qs)
    cash_in_total = sum(float(e.paid_amount or 0) for e in qs)

    credit_sales_total = sum(
        float(e.portions or 0) * price for e in qs if e.payment_type == "CREDIT"
    )
    credit_paid_total = sum(float(e.paid_amount or 0) for e in qs if e.payment_type == "CREDIT")
    ar_outstanding = max(0.0, credit_sales_total - credit_paid_total)

    since = now().date() - timedelta(days=6)
    last7 = [e for e in qs if e.date >= since]

    rows = []
    for e in last7:
        sales = float(e.portions or 0) * price
        cash_in = float(e.paid_amount or 0)
        rows.append(
            {
                "date": e.date,
                "payment_type": e.payment_type,
                "sales": sales,
                "cash_in": cash_in,
                "due": e.credit_due_date,
            }
        )

    return render(
        request,
        "core/cashflow.html",
        {
            "contract": c,
            "sales_total": sales_total,
            "cash_in_total": cash_in_total,
            "credit_sales_total": credit_sales_total,
            "credit_paid_total": credit_paid_total,
            "ar_outstanding": ar_outstanding,
            "rows": rows,
        },
    )


# =========================
# CASH TRANSACTION CRUD (manual cash in/out)
# =========================
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils.timezone import now
from datetime import timedelta

from .auth import require_auth
from .models import CashTransaction, DailyEntry
from .forms import CashTransactionForm

@require_auth
def cash_list(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    # ---- 1) Manual cash transactions (kas real di luar penjualan harian) ----
    tx_qs = CashTransaction.objects.filter(contract=c)

    manual_in = tx_qs.filter(flow="IN").aggregate(s=Sum("amount"))["s"] or 0
    manual_out = tx_qs.filter(flow="OUT").aggregate(s=Sum("amount"))["s"] or 0

    # ---- 2) Cash masuk dari penjualan harian (yang benar2 dibayar) ----
    entry_qs = DailyEntry.objects.filter(contract=c)

    sales_cash_in = entry_qs.aggregate(s=Sum("paid_amount"))["s"] or 0

    # ---- 3) Total kas ----
    total_in = float(sales_cash_in) + float(manual_in)
    total_out = float(manual_out)
    net = total_in - total_out

    # ---- 4) Info piutang (AR) dari transaksi kredit ----
    price = float(c.price_per_portion)

    credit_sales_total = 0.0
    credit_paid_total = 0.0

    for e in entry_qs:
        if e.payment_type == "CREDIT":
            credit_sales_total += float(e.portions or 0) * price
            credit_paid_total += float(e.paid_amount or 0)

    ar_outstanding = max(0.0, credit_sales_total - credit_paid_total)

    # ---- 5) List transaksi manual untuk tabel ----
    rows = tx_qs.order_by("-date", "-id")

    ctx = {
        "contract": c,
        "rows": rows,

        # kartu ringkasan
        "total_in": total_in,
        "total_out": total_out,
        "net": net,

        # breakdown biar jelas di UI
        "sales_cash_in": sales_cash_in,
        "manual_in": manual_in,
        "manual_out": manual_out,

        # piutang
        "credit_sales_total": credit_sales_total,
        "credit_paid_total": credit_paid_total,
        "ar_outstanding": ar_outstanding,
    }
    return render(request, "core/cash_list.html", ctx)

@require_auth
@require_http_methods(["GET", "POST"])
def cash_create(request):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    form = CashTransactionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.contract = c
        obj.save()
        return redirect("cash_list")

    return render(request, "core/cash_form.html", {"form": form, "is_edit": False, "contract": c})


@require_auth
@require_http_methods(["GET", "POST"])
def cash_edit(request, pk):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    obj = get_object_or_404(CashTransaction, pk=pk, contract=c)
    form = CashTransactionForm(request.POST or None, instance=obj)

    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.contract = c
        updated.save()
        return redirect("cash_list")

    return render(request, "core/cash_form.html", {"form": form, "is_edit": True, "contract": c})


@require_auth
@require_http_methods(["POST"])
def cash_delete(request, pk):
    c = get_active_contract()
    if not c:
        return redirect("contract_setup")

    obj = get_object_or_404(CashTransaction, pk=pk, contract=c)
    obj.delete()
    return redirect("cash_list")