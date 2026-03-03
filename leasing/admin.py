from django.contrib import admin
from .models import LeasingOffer, LeasingContract, Financing, Listing


@admin.register(Financing)
class FinancingAdmin(admin.ModelAdmin):
    list_display = ['pk', 'rate_type', 'interest_rate', 'tax_interest', 'additional_monthly']
    list_filter = ['rate_type']


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'price', 'currency', 'leasing_type', 'duration_months', 'monthly_payment', 'created_at']
    list_filter = ['leasing_type', 'currency', 'tax_exempt']
    search_fields = ['vehicle__plate_number']
    raw_id_fields = ['vehicle', 'financing']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LeasingOffer)
class LeasingOfferAdmin(admin.ModelAdmin):
    list_display = ['pk', 'vehicle', 'variant', 'monthly_rate', 'duration_months', 'km_limit_per_year', 'status']
    list_filter = ['status']
    search_fields = ['vehicle__plate_number', 'variant__variant', 'variant__generation__car_model__make__name']
    raw_id_fields = ['vehicle', 'variant', 'created_by']
    readonly_fields = ['created_at', 'updated_at', 'created_by']


@admin.register(LeasingContract)
class LeasingContractAdmin(admin.ModelAdmin):
    list_display = ['pk', 'vehicle', 'customer', 'monthly_rate', 'start_date', 'end_date', 'status']
    list_filter = ['status']
    search_fields = ['vehicle__plate_number', 'customer__username', 'customer__email']
    raw_id_fields = ['offer', 'vehicle', 'customer']
    readonly_fields = ['created_at', 'updated_at']
