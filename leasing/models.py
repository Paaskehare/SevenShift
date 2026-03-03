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


class Financing(models.Model):
    RATE_TYPE_CHOICES = [
        ('fixed', 'Fixed'),
        ('variable', 'Variable'),
    ]

    interest_rate = models.DecimalField(max_digits=6, decimal_places=4, help_text='Annual interest rate as a decimal (e.g. 0.0499 for 4.99%)')
    tax_interest = models.DecimalField(max_digits=6, decimal_places=4, help_text='Tax interest rate as a decimal')
    rate_type = models.CharField(max_length=10, choices=RATE_TYPE_CHOICES, default='fixed')

    lienholder_declaration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plates_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    import_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Fixed additional monthly cost')

    def __str__(self):
        return f"Financing #{self.pk} ({self.get_rate_type_display()}, {self.interest_rate*100:.2f}%)"


class Listing(models.Model):
    LEASING_TYPE_CHOICES = [
        ('financial', 'Financial'),
        ('operating', 'Operating'),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='listings',
    )
    financing = models.ForeignKey(
        Financing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )

    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='DKK')
    tax_value = models.DecimalField(max_digits=12, decimal_places=2)
    mileage = models.PositiveIntegerField(help_text='Current mileage in km')
    km_per_year = models.PositiveIntegerField()
    tax_exempt = models.BooleanField(default=False)
    yearly_greentax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    residual_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    residual_deprecation_pct = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True, help_text='Residual deprecation as a percentage (e.g. 0.40 for 40%)')
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.PositiveSmallIntegerField(default=12)
    leasing_type = models.CharField(max_length=15, choices=LEASING_TYPE_CHOICES, default='financial')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Listing #{self.pk} — {self.vehicle} @ {self.price} {self.currency}"


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
