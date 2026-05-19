"""
URL configuration for data_collector app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# REST Framework Router
router = DefaultRouter()
router.register(r"sources", views.SourceViewSet, basename="source")
router.register(r"sources-realtime", views.SourceRealtimeViewSet, basename="sourcerealtime")
router.register(r"thresholds", views.ThresholdViewSet, basename="threshold")
router.register(r"thresholds-realtime", views.ThresholdRealtimeViewSet, basename="threshold-realtime")
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
    
    # UI Template Views
    path("", views.SourceListView.as_view(), name="source-list"),
    path("sources/", views.SourceListView.as_view(), name="source-list"),
    path("sources/add/", views.SourceCreateView.as_view(), name="source-add"),
    path("sources/<int:pk>/", views.SourceUpdateView.as_view(), name="source-detail"),
    path("sources/<int:pk>/edit/", views.SourceUpdateView.as_view(), name="source-edit"),
    path("sources/<int:pk>/delete/", views.SourceDeleteView.as_view(), name="source-delete"),
    
    # Realtime Sources
    path("sources-realtime/", views.SourceRealtimeListView.as_view(), name="sourcerealtime-list"),
    path("sources-realtime/add/", views.SourceRealtimeCreateView.as_view(), name="sourcerealtime-add"),
    path("sources-realtime/<int:pk>/edit/", views.SourceRealtimeUpdateView.as_view(), name="sourcerealtime-edit"),
    path("sources-realtime/<int:pk>/delete/", views.SourceRealtimeDeleteView.as_view(), name="sourcerealtime-delete"),
    
    # Test Collect
    path("test-collect/", views.TestCollectView.as_view(), name="test-collect"),
    
    # Collection Logs
    path("collection-logs/", views.CollectionLogListView.as_view(), name="collection-log-list"),
    path("collection-logs/<int:pk>/", views.CollectionLogDetailView.as_view(), name="collection-log-detail"),
    
    # Export/Import
    path("export-import/", views.ExportImportView.as_view(), name="export-import"),
]
