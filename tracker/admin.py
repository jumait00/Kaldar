from django.contrib import admin
from .models import Account, Transaction

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("user", "cash_balance", "digital_balance", "loan_balance", "lend_balance", "updated_at")
    search_fields = ("user__username",)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "transaction_type", "amount", "category", "method")
    list_filter = ("transaction_type", "method", "date")
    search_fields = ("user__username", "category", "note")
    date_hierarchy = "date"
