"""
Celery tasks cho data_collector app.
Định nghĩa các background tasks để thu thập dữ liệu tự động.
"""
from datetime import datetime

from celery import shared_task

from .collectors import collect_data_from_source
from .models import Source, SourceRealtime


@shared_task(name="collect_all_sources")
def collect_all_sources():
    """
    Task thu thập dữ liệu từ tất cả các source active.
    """
    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "details": []
    }

    now = datetime.now()

    # Collect from batch sources
    batch_sources = Source.objects.filter(active="1")
    for source in batch_sources:
        results["total"] += 1
        try:
            result = collect_data_from_source(source, now, write_to_db=True)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "source_name": str(source),
                "result": result
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "source_name": str(source),
                "error": str(e)
            })

    # Collect from realtime sources
    realtime_sources = SourceRealtime.objects.filter(active=True)
    for source in realtime_sources:
        results["total"] += 1
        try:
            result = collect_data_from_source(source, now, write_to_db=True)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "source_name": str(source),
                "result": result
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "source_name": str(source),
                "error": str(e)
            })

    return results


@shared_task(name="collect_sources_by_system")
def collect_sources_by_system(system: str):
    """
    Task thu thập dữ liệu theo system (2G, 3G, 4G, 5G).
    """
    results = {
        "system": system,
        "total": 0,
        "success": 0,
        "failed": 0,
        "details": []
    }

    now = datetime.now()

    # Batch sources
    batch_sources = Source.objects.filter(system__iexact=system, active="1")
    for source in batch_sources:
        results["total"] += 1
        try:
            result = collect_data_from_source(source, now, write_to_db=True)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "result": result
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "error": str(e)
            })

    # Realtime sources
    realtime_sources = SourceRealtime.objects.filter(system__iexact=system, active=True)
    for source in realtime_sources:
        results["total"] += 1
        try:
            result = collect_data_from_source(source, now, write_to_db=True)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "result": result
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "error": str(e)
            })

    return results


@shared_task(name="collect_realtime_sources")
def collect_realtime_sources(cycle_minutes: int = 15):
    """
    Task thu thập dữ liệu realtime theo chu kỳ.
    """
    results = {
        "cycle_minutes": cycle_minutes,
        "total": 0,
        "success": 0,
        "failed": 0,
        "details": []
    }

    now = datetime.now()

    sources = SourceRealtime.objects.filter(
        active=True,
        cycle_minutes=cycle_minutes
    )

    for source in sources:
        results["total"] += 1
        try:
            result = collect_data_from_source(source, now, write_to_db=True)
            if result["success"]:
                results["success"] += 1
                # Update last_fetch_time
                source.last_fetch_time = now
                source.last_file_name = result.get("file", "")
                source.save(update_fields=["last_fetch_time", "last_file_name"])
            else:
                results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "result": result
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "source_id": source.pk,
                "error": str(e)
            })

    return results


@shared_task(name="collect_single_source")
def collect_single_source(source_type: str, source_id: int):
    """
    Task thu thập dữ liệu từ một source cụ thể.
    """
    now = datetime.now()

    if source_type == "source":
        source = Source.objects.filter(_id=source_id).first()
    elif source_type == "source_realtime":
        source = SourceRealtime.objects.filter(_id=source_id).first()
    else:
        return {"success": False, "error": f"Invalid source_type: {source_type}"}

    if not source:
        return {"success": False, "error": f"Source not found: {source_type}/{source_id}"}

    try:
        result = collect_data_from_source(source, now, write_to_db=True)

        if source_type == "source_realtime" and result["success"]:
            source.last_fetch_time = now
            source.last_file_name = result.get("file", "")
            source.save(update_fields=["last_fetch_time", "last_file_name"])

        return {
            "success": result["success"],
            "source_id": source_id,
            "source_name": str(source),
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "source_id": source_id,
            "source_name": str(source),
            "error": str(e)
        }


@shared_task(name="collect_batch_sources")
def collect_batch_sources(source_ids: list):
    """
    Task thu thập dữ liệu từ nhiều sources cụ thể.
    """
    results = {
        "total": len(source_ids),
        "success": 0,
        "failed": 0,
        "details": []
    }

    now = datetime.now()

    for source_id in source_ids:
        source = Source.objects.filter(_id=source_id).first()
        if not source:
            results["failed"] += 1
            results["details"].append({
                "source_id": source_id,
                "error": "Source not found"
            })
            continue

        try:
            result = collect_data_from_source(source, now, write_to_db=True)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "source_id": source_id,
                "result": result
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "source_id": source_id,
                "error": str(e)
            })

    return results
