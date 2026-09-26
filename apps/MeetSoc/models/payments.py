import uuid

from django.conf import settings
from django.db import models


class PaymentMethod(models.Model):
    """Available payment methods (bKash, Nagad, bank, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    icon = models.ImageField(upload_to="payments/icons/", blank=True, null=True)
    number = models.CharField(max_length=30, help_text="Merchant/account number to send payment to")
    help_text = models.TextField(
        blank=True,
        help_text="Info shown to users when they select this method (e.g. account name, instructions)",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_method"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class Payment(models.Model):
    """Tracks user payment transactions for ad campaigns."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="payments", null=True, blank=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="BDT", help_text="BDT or USD")

    transaction_id = models.CharField(max_length=200, blank=True)
    sender_number = models.CharField(max_length=30, blank=True, help_text="Phone/account number payment was sent from")
    screenshot = models.ImageField(upload_to="payments/screenshots/", blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment({self.amount} {self.currency}) by {self.user_id} — {self.status}"


class UserWallet(models.Model):
    """Personal wallet for each user — holds BDT and USD balances."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_wallet"

    def __str__(self):
        return f"Wallet({self.user_id}): ৳{self.balance_bdt} / ${self.balance_usd}"


class WalletTransaction(models.Model):
    """Every deposit or deduction on a user wallet."""

    TYPE_CHOICES = [
        ("deposit", "Deposit"),
        ("deduct", "Deduction"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(UserWallet, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    currency = models.CharField(max_length=3, help_text="BDT or USD")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300, blank=True)
    related_payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="wallet_txns"
    )
    admin_note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="completed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_wallettransaction"
        ordering = ["-created_at"]

    def __str__(self):
        return f"WalletTxn({self.type} {self.amount} {self.currency}) — {self.wallet_id}"
