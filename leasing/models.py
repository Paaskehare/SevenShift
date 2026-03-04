import numpy_financial as npf

from django.db import models
from django.conf import settings
from catalog.models import Variant
from vehicles.models import Vehicle
from leasing.utils import proportional_registration_tax as _proportional_reg_tax


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
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Fixed additional monthly cost')

    def __str__(self):
        return f"Financing #{self.pk} ({self.get_rate_type_display()}, {self.interest_rate*100:.2f}%)"

    def calculate_proportional_registration_tax(
        self,
        registration_tax: float,
        car_age_months: int,
        duration_months: int,
    ) -> float:
        """Total proportional registration tax for the lease period (DKK)."""
        return _proportional_reg_tax(
            registration_tax=registration_tax,
            car_age_months=car_age_months,
            duration_months=duration_months,
            tax_interest=float(self.tax_interest),
        )

    def calculate_monthly_payment(
        self,
        price: float,
        down_payment: float,
        residual_value: float,
        duration_months: int,
        registration_tax: float,
        yearly_greentax: float = 0.0,
    ) -> float:
        """
        Calculate the monthly financial leasing payment (finansiel leasing).

            monthly = pmt(price + fees - residual) + tax_interest + additional + greentax
        """
        spread_fees = (
            float(self.lienholder_declaration_fee)
            + float(self.plates_cost)
            + float(self.delivery)
            + float(self.import_fee)
            + float(self.commission)
        )


        pv = price - down_payment + spread_fees + registration_tax

        core = -npf.pmt(
            rate=float(self.interest_rate / 100) / 12,
            nper=duration_months,
            pv=pv,
            fv=-residual_value,
            when = 0,
        )

        return float(core) + float(self.additional_monthly) + (yearly_greentax / 12)


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
    registration_tax = models.DecimalField(max_digits=12, decimal_places=2)
    proportional_registration_tax = models.BooleanField(default = True)
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

    def calculate_monthly_payment(self) -> float:
        if self.proportional_registration_tax:
            car_age_months = self.vehicle.age_months or 0
            reg_tax = self.financing.calculate_proportional_registration_tax(
                registration_tax=float(self.registration_tax),
                car_age_months=car_age_months,
                duration_months=self.duration_months,
            )
        else:
            reg_tax = float(self.registration_tax)

        return self.financing.calculate_monthly_payment(
            price=float(self.price),
            down_payment=float(self.down_payment),
            residual_value=float(self.residual_value or 0),
            duration_months=self.duration_months,
            registration_tax=reg_tax,
            yearly_greentax=float(self.yearly_greentax or 0),
        )


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
