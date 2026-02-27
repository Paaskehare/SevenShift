from django.db import models
from django.utils.text import slugify
from catalog.models import Variant


# ---------------------------------------------------------------------------
# Vehicles-app Make / CarModel (normalised, slugged)
# ---------------------------------------------------------------------------

class Make(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    mobile_de_id = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text='mobile.de numeric make ID (used in the ms= URL parameter)',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Make'
        verbose_name_plural = 'Makes'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    make = models.ForeignKey(Make, on_delete=models.CASCADE, related_name='car_models')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    mobile_de_id = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text='mobile.de numeric model ID (used in the ms= URL parameter)',
    )

    class Meta:
        ordering = ['make', 'name']
        unique_together = [('make', 'name')]
        verbose_name = 'Car Model'
        verbose_name_plural = 'Car Models'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.make.name}-{self.name}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.make} {self.name}'


# ---------------------------------------------------------------------------
# mobile.de scraper configuration
# ---------------------------------------------------------------------------

class MobileDeSearchConfig(models.Model):
    """
    Stored search criteria for a mobile.de scrape run.

    The scraper builds the ms= URL parameter from make.mobile_de_id and
    car_model.mobile_de_id when set.  Leave both blank to search without a
    make/model constraint.
    """

    FUEL_CHOICES = [
        ('', 'Any'),
        ('DIESEL', 'Diesel'),
        ('PETROL', 'Petrol'),
        ('ELECTRICITY', 'Electric'),
        ('HYBRID_PETROL', 'Hybrid (Petrol)'),
        ('HYBRID_DIESEL', 'Hybrid (Diesel)'),
        ('NATURAL_GAS', 'CNG'),
        ('LPG', 'LPG'),
    ]

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    make = models.ForeignKey(
        Make, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='search_configs',
    )
    car_model = models.ForeignKey(
        CarModel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='search_configs',
    )

    year_from = models.PositiveSmallIntegerField(null=True, blank=True)
    year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    price_min = models.PositiveIntegerField(null=True, blank=True)
    price_max = models.PositiveIntegerField(null=True, blank=True)
    mileage_max = models.PositiveIntegerField(null=True, blank=True)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, blank=True, default='')

    # Upper bound on results fetched per run (caps pagination)
    max_results = models.PositiveSmallIntegerField(default=100)

    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'mobile.de Search Config'
        verbose_name_plural = 'mobile.de Search Configs'
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Vehicle (unified fleet-vehicle + market-listing model)
# ---------------------------------------------------------------------------

class Vehicle(models.Model):
    """
    Unified model for fleet vehicles and listings scraped from mobile.de.

    Scraper-sourced rows have listing_id / source_url / search_config set.
    Manually entered fleet cars leave those nullable fields blank.
    Scraped listings are keyed on listing_id and updated in-place on re-runs.
    is_active is cleared when a listing no longer appears in search results.
    """

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('leased', 'Leased'),
        ('in_service', 'In Service'),
        ('reserved', 'Reserved'),
        ('retired', 'Retired'),
    ]

    # Relationships
    search_config = models.ForeignKey(
        MobileDeSearchConfig,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicles',
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fleet_vehicles',
        help_text='Optional link to a catalog Variant if matched.',
    )
    make = models.ForeignKey(
        Make,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicles',
    )
    car_model = models.ForeignKey(
        CarModel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicles',
    )

    # Scraper-specific identifiers (null for manually created records)
    listing_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    source_url = models.URLField(max_length=500, blank=True)

    # Vehicle identity
    trim = models.CharField(max_length=300, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    first_registration = models.CharField(max_length=10, blank=True, help_text='MM/YYYY')
    body_type = models.CharField(max_length=50, blank=True)

    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_vat = models.BooleanField(
        default=False,
        help_text='True if the listed price already includes VAT.',
    )
    price_vat_applicable = models.BooleanField(
        default=True,
        help_text='False for private sellers where VAT does not apply.',
    )

    # Condition
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    mileage_updated_at = models.DateTimeField(null=True, blank=True)

    # Technical specs
    fuel_type = models.CharField(max_length=50, blank=True)
    power_hp = models.PositiveSmallIntegerField(null=True, blank=True)
    battery_capacity_kwh = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True,
        help_text='Only populated for electric/hybrid vehicles.',
    )

    # Appearance
    color = models.CharField(max_length=100, blank=True)
    color_code = models.CharField(max_length=20, blank=True)
    interior_color = models.CharField(max_length=100, blank=True)
    equipment = models.JSONField(default=list, blank=True)

    # Quick-access thumbnail — set to the first image URL during scraping
    thumbnail_url = models.URLField(max_length=500, blank=True)

    # Fleet management fields
    plate_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    vin = models.CharField(max_length=17, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    notes = models.TextField(blank=True)

    is_active = models.BooleanField(
        default=True,
        help_text='Set to False when the listing no longer appears in search results.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'

    def __str__(self):
        make = self.make.name if self.make else ''
        model = self.car_model.name if self.car_model else ''
        parts = [p for p in [make, model, self.trim] if p]
        label = ' '.join(parts) or self.plate_number or self.listing_id or f'#{self.pk}'
        return f'{label} ({self.year})' if self.year else label

    @property
    def display_name(self):
        if self.variant:
            return str(self.variant)
        make = self.make.name if self.make else ''
        model = self.car_model.name if self.car_model else ''
        parts = [p for p in [make, model, self.trim] if p]
        return ' '.join(parts) or self.plate_number or str(self.pk)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

class VehicleImage(models.Model):
    """
    An image belonging to a Vehicle, ordered by the `order` field.
    The image with order=0 is treated as the primary image;
    thumbnail_url on the parent Vehicle caches that first image URL.
    """

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='images',
    )
    url = models.URLField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Vehicle Image'
        verbose_name_plural = 'Vehicle Images'

    def __str__(self):
        return f'Image {self.order} – {self.vehicle}'
