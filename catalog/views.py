from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Make, CarModel, Generation, Variant
from .serializers import MakeSerializer, CarModelSerializer, GenerationSerializer, VariantSerializer


class MakeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['country']
    search_fields = ['name']


class CarModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CarModel.objects.select_related('make').all()
    serializer_class = CarModelSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['make']
    search_fields = ['name', 'make__name']


class GenerationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Generation.objects.select_related('car_model__make').all()
    serializer_class = GenerationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['car_model']
    search_fields = ['name', 'car_model__name', 'car_model__make__name']


class VariantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Variant.objects.select_related('generation__car_model__make').all()
    serializer_class = VariantSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['generation', 'fuel_type', 'transmission', 'drive', 'body_type']
    search_fields = ['variant', 'modification', 'generation__car_model__name', 'generation__car_model__make__name']
