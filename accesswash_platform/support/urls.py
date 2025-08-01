from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'support'

router = DefaultRouter()
router.register(r'requests', views.ServiceRequestViewSet, basename='servicerequest')
router.register(r'comments', views.ServiceRequestCommentViewSet, basename='comment')
router.register(r'photos', views.ServiceRequestPhotoViewSet, basename='photo')

urlpatterns = [
    path('', include(router.urls)),
]