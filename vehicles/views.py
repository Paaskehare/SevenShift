from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from .models import Vehicle, Make
from .serializers import VehicleSerializer, MakeSerializer


class MakeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Make.objects.prefetch_related('car_models').order_by('name')
    serializer_class = MakeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related(
        'variant__generation__car_model__make',
        'make', 'car_model', 'search_config',
    ).prefetch_related('images').all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'year', 'fuel_type', 'make', 'is_active']
    search_fields = [
        'plate_number', 'vin', 'listing_id', 'trim',
        'make__name', 'car_model__name',
    ]
    ordering_fields = ['created_at', 'year', 'mileage_km', 'status', 'price']
