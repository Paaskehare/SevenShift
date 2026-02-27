from rest_framework import serializers
from .models import LeasingOffer, LeasingContract


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
