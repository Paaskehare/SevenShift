from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import LeasingOffer, LeasingContract
from .serializers import LeasingOfferSerializer, LeasingContractSerializer


class LeasingOfferViewSet(viewsets.ModelViewSet):
    queryset = LeasingOffer.objects.select_related('vehicle', 'variant__generation__car_model__make', 'created_by').all()
    serializer_class = LeasingOfferSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'vehicle', 'variant']
    search_fields = ['vehicle__plate_number', 'variant__variant', 'variant__generation__car_model__make__name']
    ordering_fields = ['created_at', 'monthly_rate', 'duration_months']


class LeasingContractViewSet(viewsets.ModelViewSet):
    queryset = LeasingContract.objects.select_related('offer', 'vehicle', 'customer').all()
    serializer_class = LeasingContractSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'vehicle', 'customer']
    ordering_fields = ['start_date', 'end_date', 'created_at']
