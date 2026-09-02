"""IoT ingestion, threshold classification and automatic escalation."""

import pytest

from app.domain.iot import IoTReading
from app.exceptions import PermissionDeniedError, ValidationError
from app.utils import now


def test_threshold_classification_of_every_metric():
    assert IoTReading.classify("TEMPERATURE", 24) == "NORMAL"
    assert IoTReading.classify("TEMPERATURE", 31) == "WARNING"
    assert IoTReading.classify("TEMPERATURE", 36) == "CRITICAL"
    assert IoTReading.classify("TEMPERATURE", 8) == "CRITICAL"
    assert IoTReading.classify("AIR_QUALITY", 70) == "NORMAL"
    assert IoTReading.classify("AIR_QUALITY", 180) == "WARNING"
    assert IoTReading.classify("AIR_QUALITY", 260) == "CRITICAL"
    assert IoTReading.classify("OCCUPANCY", 55) == "NORMAL"
    assert IoTReading.classify("OCCUPANCY", 95) == "WARNING"
    assert IoTReading.classify("OCCUPANCY", 105) == "CRITICAL"
    assert IoTReading.classify("EQUIPMENT_STATUS", 1) == "NORMAL"
    assert IoTReading.classify("EQUIPMENT_STATUS", 0.5) == "WARNING"
    assert IoTReading.classify("EQUIPMENT_STATUS", 0) == "CRITICAL"


def test_reading_display_and_description():
    reading = IoTReading(1, 2, "TEMPERATURE", 24.5, resource_code="CR-101")
    assert reading.display_value() == "24.5 C"
    assert "CR-101" in reading.describe()
    status = IoTReading(2, 3, "EQUIPMENT_STATUS", 0, resource_code="EB-301")
    assert status.display_value() == "Failed"
    assert status.is_critical() is True


def test_reading_validation():
    with pytest.raises(ValidationError):
        IoTReading(1, 2, "HUMIDITY", 44)
    with pytest.raises(ValidationError):
        IoTReading(1, 2, "TEMPERATURE", "warm")


def test_normal_reading_is_stored_without_escalation(facade, resources):
    result = facade.ingest_reading(resources["IOT-CLI-101"].id, "TEMPERATURE", 23.4)
    assert result["reading"].severity == "NORMAL"
    assert result["request"] is None
    assert result["alert"] is None
    assert facade.repos.iot.get(result["reading"].id) is not None


def test_warning_reading_does_not_raise_a_ticket(facade, resources):
    result = facade.ingest_reading(resources["IOT-CLI-CS1"].id, "TEMPERATURE", 31.0)
    assert result["reading"].severity == "WARNING"
    assert result["request"] is None


def test_critical_reading_creates_alert_and_high_priority_request(facade, resources):
    before = len(facade.repos.requests.list_requests())
    result = facade.ingest_reading(resources["IOT-CLI-101"].id, "TEMPERATURE", 38.5)
    assert result["reading"].severity == "CRITICAL"
    assert result["request"] is not None
    assert result["request"].priority == "CRITICAL"
    assert result["request"].source == "IOT"
    assert result["alert"] is not None
    assert result["alert"]["severity"] == "CRITICAL"
    assert len(facade.repos.requests.list_requests()) == before + 1


def test_automatic_request_is_assigned_to_a_technician(facade, resources, users):
    result = facade.ingest_reading(resources["IOT-CLI-101"].id, "TEMPERATURE", 39.0)
    request = result["request"]
    assert request.assigned_to is not None
    assert request.status == "ASSIGNED"
    technician = facade.repos.users.get(request.assigned_to)
    assert technician.role == "MAINTENANCE"


def test_air_quality_critical_reading_is_classified_as_safety(facade, resources):
    result = facade.ingest_reading(resources["IOT-AIR-101"].id, "AIR_QUALITY", 320.0)
    assert result["request"].category == "SAFETY"
    assert result["request"].sla_hours == 1


def test_equipment_failure_is_classified_as_it_support(facade, resources):
    result = facade.ingest_reading(resources["IOT-EQP-CS1"].id, "EQUIPMENT_STATUS", 0.0)
    assert result["request"].category == "IT_SUPPORT"


def test_repeated_critical_reading_does_not_duplicate_the_ticket(facade, resources):
    first = facade.ingest_reading(resources["IOT-CLI-101"].id, "TEMPERATURE", 37.0)
    second = facade.ingest_reading(resources["IOT-CLI-101"].id, "TEMPERATURE", 37.5)
    assert first["request"] is not None
    assert second["request"] is None
    assert second["duplicate_suppressed"] is True


def test_parking_reading_updates_the_parking_area(facade, resources):
    area = resources["PK-C"]
    facade.ingest_reading(resources["IOT-PRK-A"].id, "PARKING_OCCUPANCY", 50.0)
    updated = facade.repos.resources.get_by_code("PK-A")
    assert updated.occupied_slots == round(updated.total_slots * 0.5)
    assert area.total_slots == 40


def test_device_status_zero_takes_the_device_offline(facade, resources):
    facade.ingest_reading(resources["IOT-OCC-201"].id, "DEVICE_STATUS", 0.0)
    device = facade.repos.resources.get_by_code("IOT-OCC-201")
    assert device.is_operational() is False


def test_reading_must_come_from_a_smart_device(facade, resources):
    with pytest.raises(ValidationError):
        facade.ingest_reading(resources["CR-101"].id, "TEMPERATURE", 25.0)


def test_unknown_metric_is_rejected(facade, resources):
    with pytest.raises(ValidationError):
        facade.ingest_reading(resources["IOT-CLI-101"].id, "HUMIDITY", 55.0)


def test_seeded_campus_already_contains_critical_alerts(facade):
    alerts = facade.repos.alerts.list_alerts()
    assert len(alerts) >= 2
    assert all(alert["request_id"] for alert in alerts)
    auto_requests = facade.repos.requests.list_requests(source="IOT")
    assert len(auto_requests) >= 2


def test_security_can_acknowledge_an_alert(facade, users):
    alert = facade.repos.alerts.list_alerts(status="OPEN")[0]
    acknowledged = facade.iot.acknowledge_alert(users["security.ravi"], alert["id"])
    assert acknowledged["status"] == "ACKNOWLEDGED"
    assert acknowledged["acknowledged_by"] == users["security.ravi"].id


def test_students_cannot_acknowledge_alerts_or_read_monitoring(facade, users):
    alert = facade.repos.alerts.list_alerts(status="OPEN")[0]
    with pytest.raises(PermissionDeniedError):
        facade.iot.acknowledge_alert(users["athisaya"], alert["id"])
    with pytest.raises(PermissionDeniedError):
        facade.iot.monitoring_snapshot(users["athisaya"])


def test_monitoring_snapshot_reports_every_metric(facade, users):
    snapshot = facade.iot.monitoring_snapshot(users["security.ravi"])
    assert "OCCUPANCY" in snapshot["by_metric"]
    assert "TEMPERATURE" in snapshot["by_metric"]
    assert "AIR_QUALITY" in snapshot["by_metric"]
    assert "EQUIPMENT_STATUS" in snapshot["by_metric"]
    assert snapshot["total_devices"] >= 10
    assert snapshot["severity_counts"]["CRITICAL"] >= 1


def test_parking_overview_totals(facade, users):
    overview = facade.iot.parking_overview(users["security.ravi"])
    assert overview["total_slots"] == sum(area["total_slots"] for area in overview["areas"])
    assert overview["free_slots"] == overview["total_slots"] - overview["occupied_slots"]
    assert 0 <= overview["occupancy_rate"] <= 100


def test_latest_occupancy_map_feeds_the_recommendation_engine(facade, resources):
    facade.ingest_reading(resources["IOT-OCC-101"].id, "OCCUPANCY", 12.0, now())
    occupancy = facade.repos.iot.latest_occupancy_map()
    assert occupancy[resources["CR-101"].id] == pytest.approx(0.12)
