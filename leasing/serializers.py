from rest_framework import serializers
from vehicles.models import Vehicle
from vehicles.serializers import VehicleImageSerializer
from .models import LeasingOffer, LeasingContract, Listing


class VehiclePublicSerializer(serializers.ModelSerializer):
    """Slim read-only vehicle snapshot embedded in public listing responses."""
    display_name  = serializers.ReadOnlyField()
    thumbnail_url = serializers.SerializerMethodField()
    images        = VehicleImageSerializer(many=True, read_only=True)

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'display_name', 'year', 'fuel_type', 'power_hp',
            'mileage_km', 'body_type', 'transmission', 'color',
            'thumbnail_url', 'images',
        ]

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail_url:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.thumbnail_url) if request else obj.thumbnail_url


class ListingPublicSerializer(serializers.ModelSerializer):
    vehicle = VehiclePublicSerializer(read_only=True)

    class Meta:
        model  = Listing
        fields = [
            'id', 'vehicle',
            'price', 'currency',
            'monthly_payment', 'down_payment', 'duration_months',
            'km_per_year', 'mileage',
            'registration_tax', 'tax_exempt', 'yearly_greentax',
            'residual_value', 'residual_deprecation_pct',
            'leasing_type',
            'created_at', 'updated_at',
        ]


class LeasingOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeasingOffer
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        if not data.get('vehicle') and not data.get('variant'):
            raise serializers.ValidationError(
                "An offer must reference either a fleet vehicle or a catalog variant."
            )
        return data


class LeasingContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeasingContract
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError("end_date must be after start_date.")
        return data
