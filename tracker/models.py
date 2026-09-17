from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxLengthValidator


class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account")
    cash_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    digital_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    loan_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lend_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    initialized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_balance(self):
        return self.cash_balance + self.digital_balance

    @property
    def net_worth(self):
        return self.total_balance + self.lend_balance - self.loan_balance

    def __str__(self):
        return f"{self.user.username}'s account"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        EXPENSE = "expense", "Expense"
        DEPOSIT = "deposit", "Deposit"
        WITHDRAW = "withdraw", "Withdraw"
        REPAY_LOAN = "repay_loan", "Repay Loan"
        GIVE_LOAN = "give_loan", "Give Loan"
        RECEIVE_LOAN = "receive_loan", "Receive Loan"
        TAKE_LOAN = "take_loan", "Take Loan"

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        DIGITAL = "digital", "Digital"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    category = models.CharField(max_length=20, validators=[MaxLengthValidator(20)])
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    method = models.CharField(max_length=10, choices=Method.choices)
    note = models.CharField(max_length=120, blank=True)
    cash_balance = models.DecimalField(max_digits=14, decimal_places=2)
    digital_balance = models.DecimalField(max_digits=14, decimal_places=2)
    loan_balance = models.DecimalField(max_digits=14, decimal_places=2)
    lend_balance = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["user", "transaction_type"]),
        ]

    @property
    def day(self):
        return self.date.strftime("%A")

    def __str__(self):
        return f"{self.user.username} - {self.get_transaction_type_display()} - {self.amount}"
