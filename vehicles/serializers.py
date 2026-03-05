from rest_framework import serializers
from catalog.serializers import VariantListSerializer
from .models import Vehicle, VehicleImage, Make, CarModel


class VehicleImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = VehicleImage
        fields = ['id', 'image', 'order']

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class CarModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarModel
        fields = ['id', 'name', 'slug', 'mobile_de_id']


class MakeSerializer(serializers.ModelSerializer):
    models = CarModelSerializer(source='car_models', many=True, read_only=True)

    class Meta:
        model = Make
        fields = ['id', 'name', 'slug', 'mobile_de_id', 'models']


class VehicleSerializer(serializers.ModelSerializer):
    variant_detail = VariantListSerializer(source='variant', read_only=True)
    images = VehicleImageSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()
    thumbnail_url = serializers.SerializerMethodField()

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail_url:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.thumbnail_url) if request else obj.thumbnail_url

    class Meta:
        model = Vehicle
        fields = [
            'id',
            # Relationships
            'search_config', 'variant', 'variant_detail', 'make', 'model',
            # Identity
            'display_name', 'trim', 'year', 'first_registration', 'body_type',
            'listing_id', 'source_url',
            # Pricing
            'price', 'price_vat', 'price_vat_exempt',
            # Condition
            'mileage_km', 'mileage_updated_at',
            # Specs
            'fuel_type', 'power_hp', 'battery_capacity_kwh',
            # Appearance
            'color', 'color_code', 'interior_color', 'equipment', 'thumbnail_url',
            'images',
            # Market / seller
            'price_rating', 'price_rating_thresholds', 'country', 'seller_type',
            # Fleet
            'plate_number', 'vin', 'status', 'purchase_date', 'purchase_price', 'notes',
            'is_active',
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
