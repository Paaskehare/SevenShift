from rest_framework.routers import DefaultRouter
from .views import LeasingOfferViewSet, LeasingContractViewSet, PublicListingViewSet

router = DefaultRouter()
router.register('offers',    LeasingOfferViewSet,    basename='leasingoffer')
router.register('contracts', LeasingContractViewSet, basename='leasingcontract')
router.register('listings',  PublicListingViewSet,   basename='listing')

urlpatterns = router.urls
