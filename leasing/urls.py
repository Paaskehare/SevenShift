from rest_framework.routers import DefaultRouter
from .views import LeasingOfferViewSet, LeasingContractViewSet

router = DefaultRouter()
router.register('offers', LeasingOfferViewSet, basename='leasingoffer')
router.register('contracts', LeasingContractViewSet, basename='leasingcontract')

urlpatterns = router.urls
