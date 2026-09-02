"""IoT ingestion: stores readings and escalates critical values automatically."""

from ..domain.iot import (IoTReading, METRIC_DEVICE_STATUS, METRIC_OCCUPANCY,
                          METRIC_PARKING_OCCUPANCY, METRICS)
from ..domain.resources import ParkingArea, SmartDevice
from ..domain.users import Permission
from ..exceptions import PermissionDeniedError, ValidationError
from ..patterns.observer import IOT_CRITICAL_ALERT, IOT_READING_RECORDED
from ..utils import now, require_choice, require_float


class IoTService:
    """External IoT gateway entry point plus the monitoring read models."""

    def __init__(self, iot_repository, alert_repository, resource_repository,
                 user_repository, maintenance_service, event_bus):
        self._iot = iot_repository
        self._alerts = alert_repository
        self._resources = resource_repository
        self._users = user_repository
        self._maintenance = maintenance_service
        self._bus = event_bus

    # ------------------------------------------------------------- helpers
    def _watchers(self):
        ids = [user.id for user in self._users.list_users(role="SECURITY", active_only=True)]
        ids += [user.id for user in self._users.list_users(role="ADMIN", active_only=True)]
        return ids

    def _apply_side_effects(self, reading, device):
        """Keep the resource aggregates consistent with the newest reading."""
        target_id = reading.resource_id
        if reading.metric == METRIC_PARKING_OCCUPANCY and target_id:
            area = self._resources.get(target_id)
            if isinstance(area, ParkingArea) and area.total_slots:
                occupied = int(round(area.total_slots * min(reading.value, 100.0) / 100.0))
                self._resources.update_parking_occupancy(area.id, occupied)
        elif reading.metric == METRIC_DEVICE_STATUS:
            self._resources.set_device_online(device.id, reading.value >= 1,
                                              heartbeat=reading.recorded_at)

    # ------------------------------------------------------------- ingest
    def record_reading(self, device_id, metric, value, recorded_at=None):
        """Ingest one reading from the IoT gateway (the external actor)."""
        metric = require_choice(metric, "metric", set(METRICS))
        value = require_float(value, "value", minimum=-50, maximum=10000)
        device = self._resources.require_resource(device_id)
        if not isinstance(device, SmartDevice):
            raise ValidationError("%s is not a smart device." % device.code,
                                  {"field": "device_id"})
        target_id = device.monitors_id or device.id
        target = self._resources.get(target_id)
        reading = IoTReading(None, device.id, metric, value, resource_id=target_id,
                             recorded_at=recorded_at or now(),
                             device_code=device.code, device_name=device.name,
                             resource_code=target.code if target else device.code,
                             resource_name=target.name if target else device.name)
        stored = self._iot.add_reading(reading)
        self._apply_side_effects(stored, device)
        self._bus.notify(IOT_READING_RECORDED, {
            "reading": stored,
            "entity_type": "READING",
            "entity_id": stored.id,
            "message": stored.describe(),
        })

        result = {"reading": stored, "alert": None, "request": None,
                  "duplicate_suppressed": False}
        if not stored.requires_intervention():
            return result

        # A still-open alert for the same resource/metric must not raise a
        # second ticket for the same underlying problem.
        existing = self._alerts.open_for(stored.resource_id or device.id, stored.metric)
        if existing:
            result["alert"] = existing
            result["duplicate_suppressed"] = True
            return result

        request = self._maintenance.create_automatic_request(
            stored, resource_label=target.code if target else device.code)
        payload = {
            "reading": stored,
            "request_id": request.id,
            "recipients": self._watchers() + ([request.assigned_to] if request.assigned_to else []),
            "title": "Critical IoT alert on %s" % (stored.resource_code or device.code),
            "message": "%s Ticket %s was raised automatically (%s priority)."
                       % (stored.describe(), request.ticket, request.priority),
            "entity_type": "ALERT",
            "entity_id": stored.id,
        }
        self._bus.notify(IOT_CRITICAL_ALERT, payload)
        alert_id = payload.get("alert_id")
        if alert_id:
            self._alerts.link_request(alert_id, request.id)
            result["alert"] = self._alerts.get(alert_id)
        result["request"] = request
        return result

    # --------------------------------------------------------------- reads
    def monitoring_snapshot(self, user=None, limit=40):
        if user is not None and not user.has_permission(Permission.VIEW_IOT):
            raise PermissionDeniedError("%s users cannot access IoT monitoring." % user.role)
        latest = self._iot.latest_per_device()
        by_metric = {}
        for reading in latest:
            by_metric.setdefault(reading.metric, []).append(reading.to_dict())
        parking = [area.to_dict() for area in self._resources.parking_areas()]
        devices = [device.to_dict() for device in self._resources.smart_devices()]
        return {
            "latest": [reading.to_dict() for reading in latest],
            "by_metric": by_metric,
            "recent": [reading.to_dict() for reading in self._iot.list_readings(limit=limit)],
            "severity_counts": self._iot.severity_counts(),
            "parking": parking,
            "devices": devices,
            "online_devices": len([d for d in devices if d["operational"]]),
            "total_devices": len(devices),
            "alerts": self._alerts.list_alerts(status=["OPEN", "ACKNOWLEDGED"]),
            "alert_counts": self._alerts.status_counts(),
            "occupancy": [r.to_dict() for r in latest if r.metric == METRIC_OCCUPANCY],
        }

    def acknowledge_alert(self, user, alert_id):
        if not user.has_permission(Permission.ACKNOWLEDGE_ALERT):
            raise PermissionDeniedError("%s users cannot acknowledge alerts." % user.role)
        return self._alerts.acknowledge(alert_id, user.id)

    def parking_overview(self, user=None):
        if user is not None and not user.has_permission(Permission.MONITOR_PARKING):
            raise PermissionDeniedError("%s users cannot monitor parking." % user.role)
        areas = [area for area in self._resources.parking_areas()]
        total = sum(area.total_slots for area in areas)
        occupied = sum(area.occupied_slots for area in areas)
        return {
            "areas": [area.to_dict() for area in areas],
            "total_slots": total,
            "occupied_slots": occupied,
            "free_slots": max(total - occupied, 0),
            "occupancy_rate": round((occupied / float(total)) * 100, 1) if total else 0.0,
        }
