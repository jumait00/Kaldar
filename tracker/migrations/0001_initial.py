from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cash_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("digital_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("loan_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("lend_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("initialized", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="account", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("category", models.CharField(max_length=20, validators=[django.core.validators.MaxLengthValidator(20)])),
                ("transaction_type", models.CharField(choices=[("expense","Expense"),("deposit","Deposit"),("withdraw","Withdraw"),("repay_loan","Repay Loan"),("give_loan","Give Loan"),("receive_loan","Receive Loan"),("take_loan","Take Loan")], max_length=20)),
                ("method", models.CharField(choices=[("cash","Cash"),("digital","Digital")], max_length=10)),
                ("note", models.CharField(blank=True, max_length=120)),
                ("cash_balance", models.DecimalField(decimal_places=2, max_digits=14)),
                ("digital_balance", models.DecimalField(decimal_places=2, max_digits=14)),
                ("loan_balance", models.DecimalField(decimal_places=2, max_digits=14)),
                ("lend_balance", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-date", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["user", "-date"], name="tracker_tra_user_id_5a7c65_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["user", "transaction_type"], name="tracker_tra_user_id_9d6e8f_idx"),
        ),
    ]
