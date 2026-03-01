import uuid

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from catalog.models import Variant


def _vehicle_image_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
    return f'vehicle_images/{uuid.uuid4().hex}.{ext}'


def _page_cache_upload_path(instance, filename):
    if instance.page_type == 'detail':
        return f'mobile_de_cache/detail/{filename}'
    return f'mobile_de_cache/search/{filename}'


# ---------------------------------------------------------------------------
# mobile.de HTML page cache
# ---------------------------------------------------------------------------

class MobileDePageCache(models.Model):
    """
    Stores raw HTML dumps of scraped mobile.de pages.

    Detail pages are keyed by listing_id and cached indefinitely — the scraper
    skips re-downloading a detail page if a record already exists.

    Search result pages are always re-fetched on each run (to pick up new
    listings) but overwritten here so you can replay/inspect the last result set.
    """

    PAGE_TYPE_CHOICES = [('search', 'Search result'), ('detail', 'Ad detail')]

    url_key = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text=(
            'Stable cache key. Detail pages: "detail-{listing_id}". '
            'Search pages: MD5 of the normalised URL (sorted params).'
        ),
    )
    listing_id = models.CharField(
        max_length=20, blank=True, db_index=True,
        help_text='mobile.de ad ID — only set for detail pages.',
    )
    page_type = models.CharField(max_length=10, choices=PAGE_TYPE_CHOICES)
    source_url = models.URLField(max_length=2000, blank=True)
    html_file = models.FileField(
        upload_to=_page_cache_upload_path,
        help_text='Stored HTML dump of the scraped page.',
    )
    scraped_at = models.DateTimeField()

    class Meta:
        verbose_name = 'mobile.de Page Cache'
        verbose_name_plural = 'mobile.de Page Cache'
        ordering = ['-scraped_at']

    def __str__(self):
        label = self.listing_id or self.url_key[:12]
        return f'{self.page_type} {label} @ {self.scraped_at:%Y-%m-%d %H:%M}'


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
    mobile_body_type = models.CharField(max_length=100, blank=True, help_text='Raw body type string from mobile.de, e.g. "SUV / Geländewagen"')
    body_type = models.CharField(max_length=100, blank=True, help_text='Normalized catalog slug, e.g. "suv"')
    TRANSMISSION_CHOICES = (
        ('automatic', _('Automatic')),
        ('manual', _('Manual')),
    )

    DRIVETRAIN_CHOICES = (
        ('fwd', _('Front-Wheel Drive')),
        ('rwd', _('Rear-Wheel Drive')),
        ('awd', _('All-Wheel Drive')),
    )

    transmission = models.CharField(choices=TRANSMISSION_CHOICES, max_length=16, blank=True, default='automatic')
    transmission_type = models.CharField(max_length=80, blank=True)
    drivetrain = models.CharField(choices=DRIVETRAIN_CHOICES, max_length=3, blank=True)
    num_gears = models.PositiveSmallIntegerField(null=True, blank=True)
    num_doors = models.PositiveSmallIntegerField(null=True, blank=True)

    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_vat = models.BooleanField(
        default=False,
        help_text='True if the listed price already includes VAT.',
    )
    price_vat_exempt = models.BooleanField(
        default=False,
        help_text='True for private sellers where VAT does not apply.',
    )

    # Condition
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    mileage_updated_at = models.DateTimeField(null=True, blank=True)

    # Technical specs
    fuel_type = models.CharField(max_length=50, blank=True)
    power_hp = models.PositiveSmallIntegerField(null=True, blank=True)
    displacement_cc = models.PositiveIntegerField(null=True, blank=True, help_text='Engine displacement in cc')
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

    # Market pricing signal from mobile.de
    price_rating = models.CharField(
        max_length=30, blank=True,
        help_text='e.g. GOOD_PRICE, FAIR_PRICE, HIGH_PRICE',
    )
    price_rating_thresholds = models.JSONField(
        default=list, blank=True,
        help_text='Ordered list of threshold prices in EUR as floats',
    )

    # Seller info
    country = models.CharField(max_length=5, blank=True, help_text='Seller country code, e.g. DE')
    seller_type = models.CharField(max_length=20, blank=True, help_text='DEALER or PRIVATE')

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

    `url` holds the original source URL (e.g. mobile.de CDN).
    `image` holds a locally downloaded copy (populated by the scraper).
    """

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='images',
    )
    url = models.URLField(max_length=500)
    image = models.ImageField(
        upload_to=_vehicle_image_upload_path,
        null=True, blank=True,
        help_text='Locally downloaded copy of the source image.',
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Vehicle Image'
        verbose_name_plural = 'Vehicle Images'

    def __str__(self):
        return f'Image {self.order} – {self.vehicle}'


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=Vehicle)
def vehicle_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return  # new instance — no images can exist yet
    first = instance.images.order_by('order').first()
    if first and first.image:
        instance.thumbnail_url = first.image.url