"""
Views cho data_collector app.
Bao gồm:
- CRUD API cho DataSource, ThresholdConfig, CollectionLog
- Export/Import API
- Test Collect API
- Template-based views cho Bootstrap UI
"""
import csv
import io
import json
from datetime import datetime

from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CollectionLog, DataSource, ThresholdConfig
from .serializers import (
    CollectionLogCreateSerializer,
    CollectionLogSerializer,
    DataSourceSerializer,
    ExportRequestSerializer,
    ImportRequestSerializer,
    TestConnectionSerializer,
    ThresholdConfigSerializer,
)
from .services import ExportImportService, SourceService, TestCollectService


# =============================================================================
# API Views (REST Framework)
# =============================================================================

class DataSourceViewSet(viewsets.ModelViewSet):
    """
    API ViewSet cho DataSource model.
    CRUD endpoints: /api/datasources/
    """
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        vendor = self.request.query_params.get("vendor")
        system = self.request.query_params.get("system")
        protocol = self.request.query_params.get("protocol")
        cycle = self.request.query_params.get("cycle_minutes")
        active = self.request.query_params.get("active")

        if vendor:
            queryset = queryset.filter(vendor__iexact=vendor)
        if system:
            queryset = queryset.filter(system__iexact=system)
        if protocol:
            queryset = queryset.filter(protocol__iexact=protocol)
        if cycle:
            if cycle.lower() == "null" or cycle.lower() == "batch":
                queryset = queryset.filter(cycle_minutes__isnull=True)
            else:
                queryset = queryset.filter(cycle_minutes=int(cycle))
        if active is not None:
            queryset = queryset.filter(active=active.lower() == "true")

        return queryset


class ThresholdConfigViewSet(viewsets.ModelViewSet):
    """API ViewSet cho ThresholdConfig model."""
    queryset = ThresholdConfig.objects.all()
    serializer_class = ThresholdConfigSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        _system = self.request.query_params.get("system")
        _level = self.request.query_params.get("level")
        cycle = self.request.query_params.get("cycle_minutes")

        if _system:
            queryset = queryset.filter(_system__iexact=_system)
        if _level:
            queryset = queryset.filter(_level__iexact=_level)
        if cycle:
            if cycle.lower() == "null" or cycle.lower() == "batch":
                queryset = queryset.filter(cycle_minutes__isnull=True)
            else:
                queryset = queryset.filter(cycle_minutes=int(cycle))

        return queryset


class CollectionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet cho CollectionLog (read-only)."""
    queryset = CollectionLog.objects.all()
    serializer_class = CollectionLogSerializer


class TestConnectionAPIView(APIView):
    """
    API để test kết nối SFTP/FTP của một source.
    POST /api/test-connection/
    """

    def post(self, request):
        serializer = TestConnectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source_id = serializer.validated_data["source_id"]
        success, message, details = SourceService.test_connection(source_id)

        return Response({
            "success": success,
            "message": message,
            "details": details
        })


class TestCollectAPIView(APIView):
    """
    API để thực hiện test collect với ghi log chi tiết.
    POST /api/test-collect/
    """

    def post(self, request):
        serializer = CollectionLogCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source_id = serializer.validated_data["source_id"]
        test_date = request.data.get("test_date")
        test_hour = request.data.get("test_hour")

        service = TestCollectService(
            source_id=source_id,
            test_date=test_date,
            test_hour=test_hour
        )

        result = service.execute()
        return Response(result)


class ExportAPIView(APIView):
    """
    API export dữ liệu ra JSON/CSV.
    GET /api/export/<model_name>/
    """

    def get(self, request, model_name):
        filters_json = request.query_params.get("filters")
        fmt = request.query_params.get("format", "json")

        filters = None
        if filters_json:
            try:
                filters = json.loads(filters_json)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid filters JSON"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        result = ExportImportService.export_table(
            model_name=model_name,
            filters=filters,
            format=fmt
        )

        if not result.get("success"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        if fmt == "csv":
            response = HttpResponse(result["data"], content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{model_name}_export.csv"'
            return response

        return Response(result)


class ImportAPIView(APIView):
    """
    API import dữ liệu từ JSON.
    POST /api/import/<model_name>/
    """

    def post(self, request, model_name):
        serializer = ImportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data["data"]
        mode = serializer.validated_data.get("mode", "upsert")

        result = ExportImportService.import_data(
            model_name=model_name,
            data=data,
            mode=mode
        )

        return Response(result)


# =============================================================================
# Template Views (Bootstrap UI)
# =============================================================================

class DataCollectorBaseView(TemplateView):
    """Base view với context chung."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = getattr(self, "page_title", "Data Collector")
        return context


class DataSourceListView(DataCollectorBaseView):
    """Trang danh sách DataSource."""
    template_name = "data_collector/datasource_list.html"
    page_title = "Data Sources"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sources"] = DataSource.objects.all()
        context["source_count"] = context["sources"].count()
        return context


class DataSourceCreateView(CreateView):
    """Trang tạo DataSource mới."""
    model = DataSource
    template_name = "data_collector/datasource_form.html"
    fields = "__all__"
    success_url = reverse_lazy("datasource-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add Data Source"
        context["form_action"] = "create"
        context["source"] = DataSource()
        return context


class DataSourceUpdateView(UpdateView):
    """Trang cập nhật DataSource."""
    model = DataSource
    template_name = "data_collector/datasource_form.html"
    fields = "__all__"
    success_url = reverse_lazy("datasource-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit Data Source"
        context["form_action"] = "update"
        if self.object.data_header_name:
            context["source"] = self.object
            context["source"].data_header_name_str = json.dumps(self.object.data_header_name, indent=2)
        else:
            context["source"] = self.object
            context["source"].data_header_name_str = ""
        return context


class DataSourceDeleteView(DeleteView):
    """Trang xóa DataSource."""
    model = DataSource
    template_name = "data_collector/datasource_confirm_delete.html"
    success_url = reverse_lazy("datasource-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Delete Data Source"
        return context


class ThresholdConfigListView(DataCollectorBaseView):
    """Trang danh sách ThresholdConfig."""
    template_name = "data_collector/threshold_list.html"
    page_title = "Threshold Configs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["thresholds"] = ThresholdConfig.objects.all()
        context["threshold_count"] = context["thresholds"].count()
        return context


class ThresholdConfigCreateView(CreateView):
    """Trang tạo ThresholdConfig mới."""
    model = ThresholdConfig
    template_name = "data_collector/threshold_form.html"
    fields = "__all__"
    success_url = reverse_lazy("threshold-list")


class ThresholdConfigUpdateView(UpdateView):
    """Trang cập nhật ThresholdConfig."""
    model = ThresholdConfig
    template_name = "data_collector/threshold_form.html"
    fields = "__all__"
    success_url = reverse_lazy("threshold-list")


class ThresholdConfigDeleteView(DeleteView):
    """Trang xóa ThresholdConfig."""
    model = ThresholdConfig
    template_name = "data_collector/threshold_confirm_delete.html"
    success_url = reverse_lazy("threshold-list")


class ExportImportView(DataCollectorBaseView):
    """Trang Export/Import dữ liệu."""
    template_name = "data_collector/export_import.html"
    page_title = "Export / Import Data"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["export_models"] = [
            ("datasource", "Data Sources"),
            ("thresholdconfig", "Threshold Configs"),
            ("collection_log", "Collection Logs"),
            # KPI 60min (batch/hourly)
            ("kpi2g_60min", "KPI 2G 60min"),
            ("kpi3g_60min", "KPI 3G 60min"),
            ("kpi4g_60min", "KPI 4G 60min"),
            ("kpi5g_60min", "KPI 5G 60min"),
            ("kpivolte_60min", "KPI VoLTE 60min"),
            # KPI 15min (realtime)
            ("kpi2g_15min", "KPI 2G 15min"),
            ("kpi3g_15min", "KPI 3G 15min"),
            ("kpi4g_15min", "KPI 4G 15min"),
            ("kpi5g_15min", "KPI 5G 15min"),
            ("kpivolte_15min", "KPI VoLTE 15min"),
        ]
        context["import_models"] = [
            ("datasource", "Data Sources"),
            ("thresholdconfig", "Threshold Configs"),
            ("collection_log", "Collection Logs"),
        ]
        return context


class TestCollectView(DataCollectorBaseView):
    """Trang Test Collect dữ liệu."""
    template_name = "data_collector/test_collect.html"
    page_title = "Test Data Collection"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sources = []
        for src in DataSource.objects.all():
            cycle_str = "batch" if src.is_batch() else f"{src.cycle_minutes}min"
            sources.append({
                "id": src._id,
                "name": f"[{src.system}] {src.vendor} - {src.ip}/{src.data_name} ({cycle_str})",
                "system": src.system,
                "vendor": src.vendor,
                "cycle": cycle_str,
            })

        context["sources"] = sources
        context["recent_logs"] = CollectionLog.objects.all()[:10]
        return context


class CollectionLogDetailView(DetailView):
    """Trang chi tiết Collection Log."""
    model = CollectionLog
    template_name = "data_collector/log_detail.html"
    context_object_name = "log"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Collection Log #{self.object._id}"
        return context


class CollectionLogListView(DataCollectorBaseView):
    """Trang danh sách Collection Logs."""
    template_name = "data_collector/collection_log_list.html"
    page_title = "Collection Logs"

    def get_context_data(self, **kwargs):
        from django.core.paginator import Paginator
        context = super().get_context_data(**kwargs)
        
        paginator = Paginator(CollectionLog.objects.all(), 50)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        
        context["page_obj"] = page_obj
        context["logs"] = page_obj.object_list
        return context


# =============================================================================
# Function-based Views (for AJAX calls)
# =============================================================================

@api_view(["GET", "POST"])
def test_connection(request):
    """AJAX endpoint cho test connection."""
    if request.method == "POST":
        serializer = TestConnectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source_id = serializer.validated_data["source_id"]
        success, message, details = SourceService.test_connection(source_id)

        return JsonResponse({
            "success": success,
            "message": message,
            "details": details
        })

    return JsonResponse({"error": "Method not allowed"}, status=405)


@api_view(["POST"])
def run_test_collect(request):
    """AJAX endpoint cho test collect."""
    serializer = CollectionLogCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    source_id = serializer.validated_data["source_id"]
    test_date = request.data.get("test_date")
    test_hour = request.data.get("test_hour")

    service = TestCollectService(
        source_id=source_id,
        test_date=test_date,
        test_hour=test_hour
    )

    result = service.execute()
    return JsonResponse(result)


@api_view(["GET"])
def export_data(request, model_name):
    """AJAX endpoint cho export."""
    filters_json = request.query_params.get("filters")
    fmt = request.query_params.get("format", "json")

    filters = None
    if filters_json:
        try:
            filters = json.loads(filters_json)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid filters JSON"}, status=400)

    result = ExportImportService.export_table(
        model_name=model_name,
        filters=filters,
        format=fmt
    )

    if not result.get("success"):
        return JsonResponse(result, status=400)

    if fmt == "csv":
        response = HttpResponse(result["data"], content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{model_name}_export.csv"'
        return response

    return JsonResponse(result)


@api_view(["POST"])
def import_data(request, model_name):
    """AJAX endpoint cho import."""
    data = request.data.get("data", [])
    mode = request.data.get("mode", "upsert")

    if not data:
        return JsonResponse({"error": "No data provided"}, status=400)

    result = ExportImportService.import_data(
        model_name=model_name,
        data=data,
        mode=mode
    )

    return JsonResponse(result)


# =============================================================================
# Health Check
# =============================================================================

@api_view(["GET"])
def health_check(request):
    """Health check endpoint."""
    return Response({
        "status": "healthy",
        "app": "data_collector",
        "timestamp": timezone.now().isoformat()
    })


# =============================================================================
# Backward compatibility aliases
# =============================================================================

SourceListView = DataSourceListView
SourceCreateView = DataSourceCreateView
SourceUpdateView = DataSourceUpdateView
SourceDeleteView = DataSourceDeleteView
SourceRealtimeListView = DataSourceListView
SourceRealtimeCreateView = DataSourceCreateView
SourceRealtimeUpdateView = DataSourceUpdateView
SourceRealtimeDeleteView = DataSourceDeleteView
ThresholdListView = ThresholdConfigListView
ThresholdCreateView = ThresholdConfigCreateView
ThresholdUpdateView = ThresholdConfigUpdateView
ThresholdDeleteView = ThresholdConfigDeleteView
ThresholdRealtimeListView = ThresholdConfigListView
ThresholdRealtimeCreateView = ThresholdConfigCreateView
ThresholdRealtimeUpdateView = ThresholdConfigUpdateView
ThresholdRealtimeDeleteView = ThresholdConfigDeleteView
