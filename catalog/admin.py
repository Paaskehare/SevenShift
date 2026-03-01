from django.contrib import admin
from .models import Make, CarModel, Generation, Variant


@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'founded', 'data_id']
    search_fields = ['name', 'country']


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ['make', 'name', 'data_id']
    list_filter = ['make']
    search_fields = ['name', 'make__name']


@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    list_display = ['car_model', 'name', 'production_start', 'production_end', 'data_id']
    list_filter = ['car_model__make']
    search_fields = ['name', 'car_model__name', 'car_model__make__name']
    raw_id_fields = ['car_model']


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ['generation', 'variant', 'modification', 'body_type', 'power_hp', 'fuel_type', 'data_id']
    list_filter = ['body_type', 'fuel_type', 'transmission', 'drivetrain', 'electric_motor_location', 'generation__car_model__make']
    search_fields = ['variant', 'modification', 'generation__name', 'generation__car_model__name', 'generation__car_model__make__name']
    raw_id_fields = ['generation']
    fieldsets = (
        ('Identity', {
            'fields': ('generation', 'variant', 'modification', 'body_type', 'seats', 'doors', 'data_id', 'scraped_at'),
        }),
        ('Engine & Drivetrain', {
            'fields': ('fuel_type', 'engine_displacement_cc', 'engine_cylinders', 'power_hp', 'power_kw', 'torque_nm', 'transmission', 'drivetrain'),
        }),
        ('Performance & Economy', {
            'fields': ('acceleration_0_100', 'top_speed_kmh', 'fuel_consumption_l100km', 'co2_g_km'),
        }),
        ('Battery & Electric', {
            'fields': ('gross_battery_capacity', 'all_electric_range', 'average_energy_consumption', 'charging_ports', 'electric_motor_type', 'electric_motor_location', 'electric_motor_code', 'electric_platform'),
        }),
        ('Dimensions & Weight', {
            'fields': ('length_mm', 'width_mm', 'height_mm', 'wheelbase_mm', 'curb_weight_kg', 'max_weight_kg', 'max_load_kg', 'trunk_volume_l'),
        }),
    )
