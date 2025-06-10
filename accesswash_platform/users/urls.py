from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet, UserInvitationViewSet,
    CustomTokenObtainPairView, LogoutView
)

app_name = 'users'

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'invitations', UserInvitationViewSet, basename='invitation')

urlpatterns = [
    # Auth endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Router URLs
    path('', include(router.urls)),
]