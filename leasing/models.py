from django.db import models
from django.conf import settings
from catalog.models import Variant
from vehicles.models import Vehicle


class LeasingOffer(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leasing_offers',
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leasing_offers',
    )

    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    duration_months = models.PositiveSmallIntegerField()
    km_limit_per_year = models.PositiveIntegerField()
    residual_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    excess_km_rate = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_offers',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.vehicle or self.variant
        return f"Offer #{self.pk} — {target} @ {self.monthly_rate}/mo"


class LeasingContract(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
    ]

    offer = models.ForeignKey(
        LeasingOffer,
        on_delete=models.PROTECT,
        related_name='contracts',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='contracts',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='leasing_contracts',
    )

    # Snapshot pricing at time of signing
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    duration_months = models.PositiveSmallIntegerField()
    km_limit_per_year = models.PositiveIntegerField()
    residual_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    signed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"Contract #{self.pk} — {self.vehicle} / {self.customer}"
