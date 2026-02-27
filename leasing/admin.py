from django.contrib import admin
from .models import LeasingOffer, LeasingContract


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
