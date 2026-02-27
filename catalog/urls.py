from rest_framework.routers import DefaultRouter
from .views import MakeViewSet, CarModelViewSet, GenerationViewSet, VariantViewSet

router = DefaultRouter()
router.register('makes', MakeViewSet, basename='make')
router.register('models', CarModelViewSet, basename='carmodel')
router.register('generations', GenerationViewSet, basename='cargeneration')
router.register('variants', VariantViewSet, basename='variant')

urlpatterns = router.urls
