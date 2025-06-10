from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'infrastructure'

router = DefaultRouter()
router.register(r'asset-types', views.AssetTypeViewSet, basename='assettype')
router.register(r'zones', views.ZoneViewSet, basename='zone')
router.register(r'assets', views.AssetViewSet, basename='asset')
router.register(r'photos', views.AssetPhotoViewSet, basename='assetphoto')
router.register(r'inspections', views.AssetInspectionViewSet, basename='assetinspection')

urlpatterns = [
    path('', include(router.urls)),
]