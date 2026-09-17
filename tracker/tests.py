from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Account, Transaction


class TrackerFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="StrongPassword123!",
        )
        self.client.login(username="testuser", password="StrongPassword123!")

    def setup_account(self, cash="100.00", digital="500.00"):
        response = self.client.post(
            reverse("setup"),
            {"cash_balance": cash, "digital_balance": digital},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.account = Account.objects.get(user=self.user)

    def test_signup_creates_account_and_redirects_to_setup(self):
        self.client.logout()
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPassword123!",
                "password2": "StrongPassword123!",
            },
        )
        self.assertRedirects(response, reverse("setup"))
        self.assertTrue(Account.objects.filter(user__username="newuser").exists())

    def test_setup_does_not_create_zero_amount_transaction(self):
        self.setup_account()
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(self.account.cash_balance, Decimal("100.00"))
        self.assertEqual(self.account.digital_balance, Decimal("500.00"))

    def test_expense_updates_selected_balance(self):
        self.setup_account()
        response = self.client.post(
            reverse("expense"),
            {
                "date": "2026-09-17",
                "amount": "25.50",
                "category": "Food",
                "method": "cash",
                "note": "Lunch",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.account.refresh_from_db()
        self.assertEqual(self.account.cash_balance, Decimal("74.50"))
        tx = Transaction.objects.get()
        self.assertEqual(tx.transaction_type, Transaction.TransactionType.EXPENSE)

    def test_expense_cannot_overdraw_balance(self):
        self.setup_account(cash="10.00")
        response = self.client.post(
            reverse("expense"),
            {
                "date": "2026-09-17",
                "amount": "25.00",
                "category": "Food",
                "method": "cash",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.cash_balance, Decimal("10.00"))
        self.assertEqual(Transaction.objects.count(), 0)

    def test_deposit_and_withdraw(self):
        self.setup_account(cash="100.00", digital="500.00")

        response = self.client.post(
            reverse("income"),
            {
                "income_action": "deposit",
                "date": "2026-09-17",
                "amount": "50.00",
                "category": "Salary",
                "method": "digital",
                "note": "",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))

        response = self.client.post(
            reverse("income"),
            {
                "income_action": "withdraw",
                "date": "2026-09-17",
                "amount": "75.00",
                "category": "Cash",
                "method": "digital",
                "note": "",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.account.refresh_from_db()
        self.assertEqual(self.account.digital_balance, Decimal("475.00"))
        self.assertEqual(self.account.cash_balance, Decimal("175.00"))

    def test_loan_and_repayment(self):
        self.setup_account(cash="100.00", digital="500.00")

        self.client.post(
            reverse("loan_lend") + "?action=give_loan",
            {
                "loan_action": "give_loan",
                "date": "2026-09-17",
                "amount": "50.00",
                "category": "Friend",
                "method": "cash",
                "note": "",
            },
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.cash_balance, Decimal("50.00"))
        self.assertEqual(self.account.lend_balance, Decimal("50.00"))

        self.client.post(
            reverse("loan_lend") + "?action=receive_loan",
            {
                "loan_action": "receive_loan",
                "date": "2026-09-17",
                "amount": "50.00",
                "category": "Friend",
                "method": "cash",
                "note": "",
            },
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.cash_balance, Decimal("100.00"))
        self.assertEqual(self.account.lend_balance, Decimal("0.00"))

    def test_transaction_history_is_user_scoped(self):
        self.setup_account()
        Transaction.objects.create(
            user=self.user,
            date="2026-09-17",
            amount=Decimal("5.00"),
            category="Test",
            transaction_type=Transaction.TransactionType.EXPENSE,
            method=Transaction.Method.CASH,
            cash_balance=Decimal("95.00"),
            digital_balance=Decimal("500.00"),
            loan_balance=Decimal("0.00"),
            lend_balance=Decimal("0.00"),
        )
        response = self.client.get(reverse("transactions"))
        self.assertContains(response, "Test")
