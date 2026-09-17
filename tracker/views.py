from collections import defaultdict
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import InitialBalanceForm, LoanTransactionForm, SignupForm, TransactionForm
from .models import Account, Transaction


def ensure_account(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        account, _ = Account.objects.get_or_create(user=request.user)
        if not account.initialized and request.resolver_match.url_name != "setup":
            return redirect("setup")
        return view_func(request, *args, **kwargs)
    return wrapper


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            Account.objects.create(user=user)
            login(request, user)
            return redirect("setup")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def setup_account(request):
    account, _ = Account.objects.get_or_create(user=request.user)
    if account.initialized:
        return redirect("dashboard")
    if request.method == "POST":
        form = InitialBalanceForm(request.POST)
        if form.is_valid():
            account.digital_balance = form.cleaned_data["digital_balance"]
            account.cash_balance = form.cleaned_data["cash_balance"]
            account.loan_balance = Decimal("0")
            account.lend_balance = Decimal("0")
            account.initialized = True
            account.save()
            messages.success(request, "Your account has been initialized.")
            return redirect("dashboard")
    else:
        form = InitialBalanceForm()
    return render(request, "tracker/setup.html", {"form": form})


def _transaction_direction(transaction_type):
    return transaction_type


@ensure_account
def dashboard(request):
    account = request.user.account
    recent = Transaction.objects.filter(user=request.user).exclude(amount=0)[:8]

    month_start = timezone.localdate().replace(day=1)
    monthly = Transaction.objects.filter(user=request.user, date__gte=month_start).exclude(amount=0)
    monthly_expenses = monthly.filter(transaction_type=Transaction.TransactionType.EXPENSE).aggregate(total=Sum("amount"))["total"] or 0
    monthly_income = monthly.filter(transaction_type__in=[
        Transaction.TransactionType.DEPOSIT,
        Transaction.TransactionType.WITHDRAW,
        Transaction.TransactionType.RECEIVE_LOAN,
        Transaction.TransactionType.TAKE_LOAN,
    ]).aggregate(total=Sum("amount"))["total"] or 0

    category_rows = (
        monthly.filter(transaction_type=Transaction.TransactionType.EXPENSE)
        .values("category").annotate(total=Sum("amount")).order_by("-total")[:6]
    )

    return render(request, "tracker/dashboard.html", {
        "account": account,
        "recent": recent,
        "monthly_expenses": monthly_expenses,
        "monthly_income": monthly_income,
        "category_rows": list(category_rows),
    })


@ensure_account
def expense(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                account = Account.objects.select_for_update().get(user=request.user)
                amount = form.cleaned_data["amount"]
                method = form.cleaned_data["method"]
                available = account.cash_balance if method == Transaction.Method.CASH else account.digital_balance

                if amount > available:
                    form.add_error("amount", f"Insufficient {method} balance. Available: {available:,.2f}")
                else:
                    if method == Transaction.Method.CASH:
                        account.cash_balance -= amount
                    else:
                        account.digital_balance -= amount
                    account.save()

                    Transaction.objects.create(
                        user=request.user,
                        date=form.cleaned_data["date"],
                        amount=amount,
                        category=form.cleaned_data["category"],
                        transaction_type=Transaction.TransactionType.EXPENSE,
                        method=method,
                        note=form.cleaned_data["note"],
                        cash_balance=account.cash_balance,
                        digital_balance=account.digital_balance,
                        loan_balance=account.loan_balance,
                        lend_balance=account.lend_balance,
                    )
                    messages.success(request, "Expense recorded successfully.")
                    return redirect("dashboard")
    else:
        form = TransactionForm(initial={"date": timezone.localdate(), "method": Transaction.Method.CASH})
    return render(request, "tracker/form.html", {"form": form, "title": "Add Expense", "subtitle": "Record money spent from cash or digital balance.", "submit_label": "Save Expense"})


@ensure_account
def income(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            action = request.POST.get("income_action", "deposit")
            with db_transaction.atomic():
                account = Account.objects.select_for_update().get(user=request.user)
                amount = form.cleaned_data["amount"]
                method = form.cleaned_data["method"]

                if action == "withdraw":
                    if method != Transaction.Method.DIGITAL:
                        form.add_error("method", "Withdrawals must come from your digital balance.")
                    elif amount > account.digital_balance:
                        form.add_error("amount", f"Insufficient digital balance. Available: {account.digital_balance:,.2f}")
                    else:
                        account.digital_balance -= amount
                        account.cash_balance += amount
                else:
                    if method != Transaction.Method.DIGITAL:
                        form.add_error("method", "Deposits are recorded into the digital balance. Choose Digital.")
                    else:
                        account.digital_balance += amount

                if form.errors:
                    pass
                else:
                    account.save()
                    Transaction.objects.create(
                        user=request.user,
                        date=form.cleaned_data["date"],
                        amount=amount,
                        category=form.cleaned_data["category"],
                        transaction_type=Transaction.TransactionType.WITHDRAW if action == "withdraw" else Transaction.TransactionType.DEPOSIT,
                        method=method,
                        note=form.cleaned_data["note"],
                        cash_balance=account.cash_balance,
                        digital_balance=account.digital_balance,
                        loan_balance=account.loan_balance,
                        lend_balance=account.lend_balance,
                    )
                    messages.success(request, f"{'Withdrawal' if action == 'withdraw' else 'Deposit'} recorded successfully.")
                    return redirect("dashboard")
    else:
        form = TransactionForm(initial={"date": timezone.localdate(), "method": Transaction.Method.DIGITAL})
    return render(request, "tracker/income.html", {
        "form": form,
        "title": "Income & Transfers",
        "income_action": request.POST.get("income_action", "deposit"),
    })


@ensure_account
def loan_lend(request):
    action = request.GET.get("action") or request.POST.get("loan_action", "give_loan")
    valid_actions = {
        "repay_loan": Transaction.TransactionType.REPAY_LOAN,
        "give_loan": Transaction.TransactionType.GIVE_LOAN,
        "receive_loan": Transaction.TransactionType.RECEIVE_LOAN,
        "take_loan": Transaction.TransactionType.TAKE_LOAN,
    }
    if action not in valid_actions:
        action = "give_loan"

    if request.method == "POST":
        form = LoanTransactionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                account = Account.objects.select_for_update().get(user=request.user)
                amount = form.cleaned_data["amount"]
                method = form.cleaned_data["method"]
                available = account.cash_balance if method == Transaction.Method.CASH else account.digital_balance
                tx_type = valid_actions[action]

                if action in {"repay_loan", "give_loan"} and amount > available:
                    form.add_error("amount", f"Insufficient {method} balance. Available: {available:,.2f}")
                elif action == "repay_loan" and amount > account.loan_balance:
                    form.add_error("amount", f"Repayment cannot exceed your loan balance of {account.loan_balance:,.2f}.")
                elif action == "receive_loan" and amount > account.lend_balance:
                    form.add_error("amount", f"Receipt cannot exceed your lend balance of {account.lend_balance:,.2f}.")
                else:
                    # Cash/digital movement
                    if action in {"repay_loan", "give_loan"}:
                        if method == Transaction.Method.CASH:
                            account.cash_balance -= amount
                        else:
                            account.digital_balance -= amount
                    else:
                        if method == Transaction.Method.CASH:
                            account.cash_balance += amount
                        else:
                            account.digital_balance += amount

                    # Debt movement
                    if action == "repay_loan":
                        account.loan_balance -= amount
                    elif action == "give_loan":
                        account.lend_balance += amount
                    elif action == "receive_loan":
                        account.lend_balance -= amount
                    elif action == "take_loan":
                        account.loan_balance += amount

                    account.save()
                    Transaction.objects.create(
                        user=request.user,
                        date=form.cleaned_data["date"],
                        amount=amount,
                        category=form.cleaned_data["category"],
                        transaction_type=tx_type,
                        method=method,
                        note=form.cleaned_data["note"],
                        cash_balance=account.cash_balance,
                        digital_balance=account.digital_balance,
                        loan_balance=account.loan_balance,
                        lend_balance=account.lend_balance,
                    )
                    messages.success(request, f"{dict(valid_actions.items())[action].label} recorded successfully.")
                    return redirect("dashboard")
    else:
        form = LoanTransactionForm(initial={"date": timezone.localdate(), "method": Transaction.Method.CASH})
    return render(request, "tracker/loan_lend.html", {
        "form": form,
        "action": action,
        "action_labels": {
            "repay_loan": "Repay Loan",
            "give_loan": "Give Loan",
            "receive_loan": "Receive Loan",
            "take_loan": "Take Loan",
        },
    })


@ensure_account
def transactions(request):
    qs = Transaction.objects.filter(user=request.user).exclude(amount=0)
    search = request.GET.get("q", "").strip()
    tx_type = request.GET.get("type", "").strip()
    method = request.GET.get("method", "").strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(category__icontains=search) | Q(note__icontains=search))
    if tx_type:
        qs = qs.filter(transaction_type=tx_type)
    if method:
        qs = qs.filter(method=method)
    return render(request, "tracker/transactions.html", {
        "transactions": qs[:200],
        "search": search,
        "selected_type": tx_type,
        "selected_method": method,
        "types": Transaction.TransactionType.choices,
        "methods": Transaction.Method.choices,
    })


@ensure_account
def delete_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    # Financial ledger rows are snapshots; deleting an old transaction would
    # invalidate subsequent balances. Therefore deletion is intentionally blocked.
    return HttpResponseForbidden("Transactions are immutable once recorded. Create a correcting transaction instead.")
