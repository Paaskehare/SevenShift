from django.contrib import admin
from .models import Make, CarModel, MobileDePageCache, MobileDeSearchConfig, Vehicle, VehicleImage


@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'mobile_de_id']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'make', 'slug', 'mobile_de_id']
    list_filter = ['make']
    search_fields = ['name', 'make__name']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['make']


@admin.register(MobileDePageCache)
class MobileDePageCacheAdmin(admin.ModelAdmin):
    list_display = ['page_type', 'listing_id', 'url_key', 'source_url', 'scraped_at']
    list_filter = ['page_type']
    search_fields = ['listing_id', 'url_key', 'source_url']
    readonly_fields = ['url_key', 'listing_id', 'page_type', 'source_url', 'html_file', 'scraped_at']


@admin.register(MobileDeSearchConfig)
class MobileDeSearchConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'make', 'car_model', 'year_from', 'year_to', 'price_min', 'price_max', 'mileage_max', 'fuel_type', 'is_active', 'last_run_at']
    list_filter = ['is_active', 'fuel_type']
    search_fields = ['name']
    raw_id_fields = ['make', 'car_model']
    readonly_fields = ['last_run_at', 'created_at', 'updated_at']


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 0
    fields = ['url', 'image', 'order']
    ordering = ['order']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'make', 'car_model', 'year', 'status', 'mileage_km', 'price', 'plate_number', 'is_active']
    list_filter = ['status', 'is_active', 'fuel_type', 'transmission', 'make']
    search_fields = ['plate_number', 'vin', 'listing_id', 'trim', 'make__name', 'car_model__name']
    raw_id_fields = ['variant', 'make', 'car_model', 'search_config']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [VehicleImageInline]
    fieldsets = [
        ('Identity', {
            'fields': ['make', 'car_model', 'trim', 'variant', 'year', 'first_registration', 'mobile_body_type', 'body_type', 'num_doors'],
        }),
        ('Scraper', {
            'fields': ['search_config', 'listing_id', 'source_url', 'is_active', 'country', 'seller_type'],
            'classes': ['collapse'],
        }),
        ('Pricing', {
            'fields': ['price', 'price_vat', 'price_vat_exempt', 'purchase_price', 'purchase_date', 'price_rating', 'price_rating_thresholds'],
        }),
        ('Condition', {
            'fields': ['mileage_km', 'mileage_updated_at', 'fuel_type', 'power_hp', 'displacement_cc', 'battery_capacity_kwh', 'transmission', 'transmission_type', 'num_gears', 'drivetrain'],
        }),
        ('Appearance', {
            'fields': ['color', 'color_code', 'interior_color', 'thumbnail_url', 'equipment'],
        }),
        ('Fleet', {
            'fields': ['plate_number', 'vin', 'status', 'notes'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]
