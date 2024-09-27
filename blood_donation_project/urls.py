from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from delivery.views import DeliveryStaffViewSet, DeliveryViewSet, DeliveryIssueViewSet, register_user, confirm_email, login_user

router = DefaultRouter()
router.register(r'delivery-staff', DeliveryStaffViewSet)
router.register(r'deliveries', DeliveryViewSet)
router.register(r'delivery-issues', DeliveryIssueViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/register/', register_user, name='register'),
    path('api/confirm-email/<str:token>/', confirm_email, name='confirm-email'),
    path('api/auth/login/', login_user, name='api_token_auth'),
]