from rest_framework import serializers
from .models import Make, CarModel, Generation, Variant


class VariantListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ['id', 'variant', 'modification', 'body_type', 'fuel_type', 'power_hp', 'transmission', 'drivetrain']


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = '__all__'


class GenerationSerializer(serializers.ModelSerializer):
    variants = VariantListSerializer(many=True, read_only=True)

    class Meta:
        model = Generation
        fields = ['id', 'car_model', 'name', 'production_start', 'production_end', 'data_id', 'variants']


class CarModelSerializer(serializers.ModelSerializer):
    generations = GenerationSerializer(many=True, read_only=True)

    class Meta:
        model = CarModel
        fields = ['id', 'make', 'name', 'data_id', 'generations']


class MakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Make
        fields = ['id', 'name', 'country', 'founded', 'logo_url', 'data_id']
