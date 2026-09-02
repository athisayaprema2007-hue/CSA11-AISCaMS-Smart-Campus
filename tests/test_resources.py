"""Campus resource hierarchy: abstraction, polymorphism and validation."""

import pytest

from app.domain.resources import (Building, CampusResource, Classroom, Laboratory,
                                  ParkingArea, SmartDevice)
from app.exceptions import ValidationError

BUILDING = Building(1, "MB", "Main Block", 60)


def classroom(**kwargs):
    defaults = dict(resource_id=1, code="CR-900", name="Test Room", building=BUILDING,
                    floor=1, capacity=40, equipment={"PROJECTOR": "GOOD", "AC": "GOOD"})
    defaults.update(kwargs)
    return Classroom(**defaults)


def test_campus_resource_is_abstract():
    with pytest.raises(TypeError):
        CampusResource(1, "X-1", "Nope", BUILDING)


def test_resource_type_is_polymorphic():
    lab = Laboratory(2, "LB-900", "Test Lab", BUILDING, capacity=30, workstations=25)
    park = ParkingArea(3, "PK-900", "Test Parking", BUILDING, zone="Z", total_slots=10)
    device = SmartDevice(4, "IOT-900", "Test Sensor", BUILDING)
    assert classroom().resource_type == "CLASSROOM"
    assert lab.resource_type == "LABORATORY"
    assert park.resource_type == "PARKING_AREA"
    assert device.resource_type == "SMART_DEVICE"


def test_only_teaching_spaces_are_bookable():
    assert classroom().is_bookable() is True
    assert Laboratory(2, "LB-901", "Lab", BUILDING, capacity=20).is_bookable() is True
    assert ParkingArea(3, "PK-901", "Park", BUILDING, total_slots=5).is_bookable() is False
    assert SmartDevice(4, "IOT-901", "Sensor", BUILDING).is_bookable() is False


def test_summary_is_overridden_by_every_subclass():
    summaries = [
        classroom().summary(),
        Laboratory(2, "LB-902", "Lab", BUILDING, capacity=30, lab_type="COMPUTING",
                   workstations=25).summary(),
        ParkingArea(3, "PK-902", "Park", BUILDING, zone="A", total_slots=20,
                    occupied_slots=5).summary(),
        SmartDevice(4, "IOT-902", "Sensor", BUILDING, device_type="CLIMATE_SENSOR").summary(),
    ]
    assert len(set(summaries)) == 4
    assert "Classroom" in summaries[0]
    assert "laboratory" in summaries[1].lower()
    assert "5/20" in summaries[2]
    assert "Climate Sensor" in summaries[3]


def test_capacity_matching():
    room = classroom(capacity=40)
    assert room.matches_capacity(40) is True
    assert room.matches_capacity(41) is False


def test_laboratory_capacity_is_limited_by_workstations():
    lab = Laboratory(2, "LB-903", "Lab", BUILDING, capacity=60, workstations=25)
    assert lab.matches_capacity(25) is True
    assert lab.matches_capacity(30) is False


def test_equipment_matching_ignores_faulty_equipment():
    room = classroom(equipment={"PROJECTOR": "FAULTY", "AC": "GOOD"})
    assert room.has_equipment("AC") is True
    assert room.has_equipment("PROJECTOR") is False
    assert room.missing_equipment(["PROJECTOR", "AC"]) == ["PROJECTOR"]


def test_resource_validation_rejects_invalid_input():
    with pytest.raises(ValidationError):
        classroom(code="")
    with pytest.raises(ValidationError):
        classroom(capacity=-5)
    with pytest.raises(ValidationError):
        classroom(status="ON_FIRE")


def test_parking_area_occupancy_rules():
    park = ParkingArea(3, "PK-904", "Park", BUILDING, zone="A", total_slots=100,
                       occupied_slots=40)
    assert park.free_slots == 60
    assert park.occupancy_rate == 0.4
    park.update_occupancy(95)
    assert park.free_slots == 5
    with pytest.raises(ValidationError):
        park.update_occupancy(120)


def test_smart_device_operational_state():
    device = SmartDevice(4, "IOT-905", "Sensor", BUILDING, is_online=True)
    assert device.is_operational() is True
    device.set_status("OFFLINE")
    assert device.is_operational() is False


def test_equipment_condition_can_be_updated_and_is_validated():
    room = classroom()
    room.set_equipment_condition("PROJECTOR", "FAULTY")
    assert room.equipment["PROJECTOR"] == "FAULTY"
    with pytest.raises(ValidationError):
        room.set_equipment_condition("PROJECTOR", "BROKEN")
    with pytest.raises(ValidationError):
        room.set_equipment_condition("MICROSCOPE", "GOOD")


def test_seeded_resources_have_the_expected_types(resources):
    assert resources["CR-101"].resource_type == "CLASSROOM"
    assert resources["LB-CS1"].resource_type == "LABORATORY"
    assert resources["PK-A"].resource_type == "PARKING_AREA"
    assert resources["IOT-OCC-101"].resource_type == "SMART_DEVICE"
    assert resources["CR-102"].status == "MAINTENANCE"
