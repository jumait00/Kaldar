from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Transaction


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class InitialBalanceForm(forms.Form):
    digital_balance = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2, initial=0)
    cash_balance = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2, initial=0)


class TransactionForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    amount = forms.DecimalField(min_value=Decimal("0.01"), max_digits=14, decimal_places=2)
    category = forms.CharField(max_length=20)
    method = forms.ChoiceField(choices=Transaction.Method.choices)
    note = forms.CharField(max_length=120, required=False)


class LoanTransactionForm(TransactionForm):
    pass
