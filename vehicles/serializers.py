from rest_framework import serializers
from catalog.serializers import VariantListSerializer
from .models import Vehicle, VehicleImage, Make, CarModel


class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ['id', 'url', 'order']


class MakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Make
        fields = ['id', 'name', 'slug', 'mobile_de_id']


class CarModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarModel
        fields = ['id', 'make', 'name', 'slug', 'mobile_de_id']


class VehicleSerializer(serializers.ModelSerializer):
    variant_detail = VariantListSerializer(source='variant', read_only=True)
    images = VehicleImageSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Vehicle
        fields = [
            'id',
            # Relationships
            'search_config', 'variant', 'variant_detail', 'make', 'car_model',
            # Identity
            'display_name', 'trim', 'year', 'first_registration', 'body_type',
            'listing_id', 'source_url',
            # Pricing
            'price', 'price_vat', 'price_vat_applicable',
            # Condition
            'mileage_km', 'mileage_updated_at',
            # Specs
            'fuel_type', 'power_hp', 'battery_capacity_kwh',
            # Appearance
            'color', 'color_code', 'interior_color', 'equipment', 'thumbnail_url',
            'images',
            # Fleet
            'plate_number', 'vin', 'status', 'purchase_date', 'purchase_price', 'notes',
            'is_active',
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
