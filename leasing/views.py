from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import LeasingOffer, LeasingContract, Listing
from .serializers import LeasingOfferSerializer, LeasingContractSerializer, ListingPublicSerializer


class LeasingOfferViewSet(viewsets.ModelViewSet):
    queryset = LeasingOffer.objects.select_related('vehicle', 'variant__generation__car_model__make', 'created_by').all()
    serializer_class = LeasingOfferSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'vehicle', 'variant']
    search_fields = ['vehicle__plate_number', 'variant__variant', 'variant__generation__car_model__make__name']
    ordering_fields = ['created_at', 'monthly_rate', 'duration_months']


class PublicListingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only, unauthenticated endpoint for published leasing listings.
    GET /api/leasing/listings/
    GET /api/leasing/listings/{id}/
    """
    permission_classes = [AllowAny]
    serializer_class   = ListingPublicSerializer
    filterset_fields   = ['leasing_type', 'vehicle', 'financing']
    search_fields      = ['vehicle__make__name', 'vehicle__car_model__name', 'vehicle__trim']
    ordering_fields    = ['monthly_payment', 'price', 'km_per_year', 'duration_months', 'created_at']
    ordering           = ['-created_at']

    def get_queryset(self):
        return (
            Listing.objects
            .select_related('vehicle__make', 'vehicle__car_model', 'financing')
            .prefetch_related('vehicle__images')
            .all()
        )


class LeasingContractViewSet(viewsets.ModelViewSet):
    queryset = LeasingContract.objects.select_related('offer', 'vehicle', 'customer').all()
    serializer_class = LeasingContractSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'vehicle', 'customer']
    ordering_fields = ['start_date', 'end_date', 'created_at']
