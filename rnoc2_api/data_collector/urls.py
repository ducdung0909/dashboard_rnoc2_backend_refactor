"""
URL configuration for data_collector app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# REST Framework Router
router = DefaultRouter()
router.register(r"datasources", views.DataSourceViewSet, basename="datasource")
router.register(r"thresholds", views.ThresholdConfigViewSet, basename="threshold")
router.register(r"collection-logs", views.CollectionLogViewSet, basename="collection-log")

urlpatterns = [
    # API endpoints via router
    path("api/", include(router.urls)),
    
    # Custom API endpoints
    path("api/test-connection/", views.TestConnectionAPIView.as_view(), name="test-connection-api"),
    path("api/test-collect/", views.TestCollectAPIView.as_view(), name="test-collect-api"),
    path("api/export/<str:model_name>/", views.ExportAPIView.as_view(), name="export-api"),
    path("api/import/<str:model_name>/", views.ImportAPIView.as_view(), name="import-api"),
    path("api/health/", views.health_check, name="health-check"),
    
    # UI Template Views - DataSource (unified)
    path("", views.DataSourceListView.as_view(), name="datasource-list"),
    path("sources/", views.DataSourceListView.as_view(), name="datasource-list"),
    path("sources/add/", views.DataSourceCreateView.as_view(), name="datasource-add"),
    path("sources/<int:pk>/", views.DataSourceUpdateView.as_view(), name="datasource-detail"),
    path("sources/<int:pk>/edit/", views.DataSourceUpdateView.as_view(), name="datasource-edit"),
    path("sources/<int:pk>/delete/", views.DataSourceDeleteView.as_view(), name="datasource-delete"),
    
    # UI Template Views - ThresholdConfig (unified)
    path("thresholds/", views.ThresholdConfigListView.as_view(), name="threshold-list"),
    path("thresholds/add/", views.ThresholdConfigCreateView.as_view(), name="threshold-add"),
    path("thresholds/<int:pk>/edit/", views.ThresholdConfigUpdateView.as_view(), name="threshold-edit"),
    path("thresholds/<int:pk>/delete/", views.ThresholdConfigDeleteView.as_view(), name="threshold-delete"),
    
    # Test Collect
    path("test-collect/", views.TestCollectView.as_view(), name="test-collect"),
    
    # Collection Logs
    path("collection-logs/", views.CollectionLogListView.as_view(), name="collection-log-list"),
    path("collection-logs/<int:pk>/", views.CollectionLogDetailView.as_view(), name="collection-log-detail"),
    
    # Export/Import
    path("export-import/", views.ExportImportView.as_view(), name="export-import"),
    
    # Backward compatibility URLs (redirects)
    # Realtime Sources -> DataSource
    path("sources-realtime/", views.DataSourceListView.as_view(), name="sourcerealtime-list"),
    path("sources-realtime/add/", views.DataSourceCreateView.as_view(), name="sourcerealtime-add"),
    path("sources-realtime/<int:pk>/edit/", views.DataSourceUpdateView.as_view(), name="sourcerealtime-edit"),
    path("sources-realtime/<int:pk>/delete/", views.DataSourceDeleteView.as_view(), name="sourcerealtime-delete"),
    
    # Threshold Realtime -> ThresholdConfig
    path("thresholds-realtime/", views.ThresholdConfigListView.as_view(), name="threshold-realtime-list"),
    path("thresholds-realtime/add/", views.ThresholdConfigCreateView.as_view(), name="threshold-realtime-add"),
    path("thresholds-realtime/<int:pk>/edit/", views.ThresholdConfigUpdateView.as_view(), name="threshold-realtime-edit"),
    path("thresholds-realtime/<int:pk>/delete/", views.ThresholdConfigDeleteView.as_view(), name="threshold-realtime-delete"),
]
