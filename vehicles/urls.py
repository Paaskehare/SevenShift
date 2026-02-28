from rest_framework.routers import DefaultRouter
from .views import VehicleViewSet, MakeViewSet

router = DefaultRouter()
router.register('makes', MakeViewSet, basename='make')
router.register('', VehicleViewSet, basename='vehicle')

urlpatterns = router.urls
