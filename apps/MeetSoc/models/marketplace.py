import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Product(models.Model):
    STATUS_CHOICES = [
        ("pending_review", "Pending Review"),
        ("active", "Active"),
        ("sold", "Sold"),
        ("hidden", "Hidden"),
        ("deleted", "Deleted"),
    ]
    CONDITION_CHOICES = [
        ("new", "New"),
        ("like_new", "Like new"),
        ("good", "Good"),
        ("fair", "Fair"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    category = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    location = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    is_on_hold = models.BooleanField(default=False, help_text="Held by admin — hidden from all users")
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "marketplace_product"
        ordering = ["-created_at"]


class ProductMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media_items")
    file = models.ImageField(upload_to="marketplace/%Y/%m/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "marketplace_productmedia"
        ordering = ["order"]
