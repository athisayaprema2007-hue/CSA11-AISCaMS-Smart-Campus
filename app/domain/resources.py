"""Campus resource hierarchy.

`CampusResource` is the abstraction every physical or logical campus asset
inherits from.  Sub-types add their own state (seating layout, parking slots,
device firmware) and override behaviour such as `is_bookable()` and
`summary()`, which the recommendation engine and the user interface rely on
without ever testing the concrete type.
"""

from abc import ABC, abstractmethod

from ..exceptions import ValidationError

STATUS_AVAILABLE = "AVAILABLE"
STATUS_OCCUPIED = "OCCUPIED"
STATUS_MAINTENANCE = "MAINTENANCE"
STATUS_OFFLINE = "OFFLINE"
RESOURCE_STATUSES = (STATUS_AVAILABLE, STATUS_OCCUPIED, STATUS_MAINTENANCE, STATUS_OFFLINE)


class Building:
    """Value object describing where a resource physically lives."""

    def __init__(self, building_id, code, name, walking_distance_m=0):
        self._id = building_id
        self._code = code
        self._name = name
        self._walking_distance_m = int(walking_distance_m or 0)

    @property
    def id(self):
        return self._id

    @property
    def code(self):
        return self._code

    @property
    def name(self):
        return self._name

    @property
    def walking_distance_m(self):
        return self._walking_distance_m

    def to_dict(self):
        return {"id": self._id, "code": self._code, "name": self._name,
                "walking_distance_m": self._walking_distance_m}


class CampusResource(ABC):
    """Abstract base class for every manageable campus asset."""

    def __init__(self, resource_id, code, name, building, floor=0, capacity=0,
                 status=STATUS_AVAILABLE, utilisation=0.0, equipment=None):
        if not (code or "").strip():
            raise ValidationError("Resource code is required.", {"field": "code"})
        if int(capacity) < 0:
            raise ValidationError("Capacity cannot be negative.", {"field": "capacity"})
        if status not in RESOURCE_STATUSES:
            raise ValidationError("Unknown resource status: %s" % status, {"field": "status"})
        self._id = resource_id
        self._code = code.strip()
        self._name = (name or code).strip()
        self._building = building
        self._floor = int(floor or 0)
        self._capacity = int(capacity)
        self._status = status
        self._utilisation = float(utilisation or 0.0)
        # equipment is a mapping {code: condition}
        self._equipment = dict(equipment or {})

    # ------------------------------------------------------------ properties
    @property
    def id(self):
        return self._id

    @property
    def code(self):
        return self._code

    @property
    def name(self):
        return self._name

    @property
    def building(self):
        return self._building

    @property
    def building_name(self):
        return self._building.name if self._building else "-"

    @property
    def walking_distance_m(self):
        return self._building.walking_distance_m if self._building else 0

    @property
    def floor(self):
        return self._floor

    @property
    def capacity(self):
        return self._capacity

    @property
    def status(self):
        return self._status

    @property
    def utilisation(self):
        return self._utilisation

    @property
    def equipment(self):
        """Read-only view of the installed equipment."""
        return dict(self._equipment)

    @property
    def equipment_codes(self):
        return sorted(self._equipment.keys())

    # ---------------------------------------------------------- behaviour
    def is_available(self):
        return self._status == STATUS_AVAILABLE

    def is_bookable(self):
        """Only teaching spaces can be reserved through the booking workflow."""
        return False

    def has_equipment(self, code):
        condition = self._equipment.get(code)
        return condition is not None and condition not in ("FAULTY", "OUT_OF_SERVICE")

    def missing_equipment(self, required):
        return [code for code in (required or []) if not self.has_equipment(code)]

    def matches_capacity(self, attendees):
        return self._capacity >= int(attendees or 0)

    def set_status(self, status):
        if status not in RESOURCE_STATUSES:
            raise ValidationError("Unknown resource status: %s" % status, {"field": "status"})
        self._status = status

    def set_equipment_condition(self, code, condition):
        allowed = ("GOOD", "FAIR", "FAULTY", "OUT_OF_SERVICE")
        if condition not in allowed:
            raise ValidationError("Unknown equipment condition: %s" % condition,
                                  {"field": "condition"})
        if code not in self._equipment:
            raise ValidationError("%s does not have equipment %s." % (self._code, code),
                                  {"field": "equipment"})
        self._equipment[code] = condition

    @property
    @abstractmethod
    def resource_type(self):
        """Discriminator stored in `campus_resources.resource_type`."""

    @abstractmethod
    def summary(self):
        """One line description used in listings and recommendations."""

    def to_dict(self):
        return {
            "id": self._id,
            "code": self._code,
            "name": self._name,
            "resource_type": self.resource_type,
            "building": self.building_name,
            "building_code": self._building.code if self._building else None,
            "walking_distance_m": self.walking_distance_m,
            "floor": self._floor,
            "capacity": self._capacity,
            "status": self._status,
            "utilisation": round(self._utilisation, 3),
            "equipment": self.equipment,
            "equipment_codes": self.equipment_codes,
            "bookable": self.is_bookable(),
            "summary": self.summary(),
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<%s %s>" % (self.__class__.__name__, self._code)


class Classroom(CampusResource):
    """Lecture room that can be reserved by students, faculty and admins."""

    def __init__(self, *args, seating_type="FIXED", board_type="WHITEBOARD", **kwargs):
        super().__init__(*args, **kwargs)
        self._seating_type = seating_type
        self._board_type = board_type

    @property
    def seating_type(self):
        return self._seating_type

    @property
    def board_type(self):
        return self._board_type

    @property
    def resource_type(self):
        return "CLASSROOM"

    def is_bookable(self):
        return True

    def summary(self):
        return "Classroom | %d seats | %s seating | %s" % (
            self.capacity, self._seating_type.lower(), self._board_type.lower())

    def to_dict(self):
        data = super().to_dict()
        data.update({"seating_type": self._seating_type, "board_type": self._board_type})
        return data


class Laboratory(CampusResource):
    """Specialised practical room; bookable but with safety constraints."""

    def __init__(self, *args, lab_type="COMPUTING", safety_level="STANDARD",
                 workstations=0, **kwargs):
        super().__init__(*args, **kwargs)
        self._lab_type = lab_type
        self._safety_level = safety_level
        self._workstations = int(workstations or 0)

    @property
    def lab_type(self):
        return self._lab_type

    @property
    def safety_level(self):
        return self._safety_level

    @property
    def workstations(self):
        return self._workstations

    @property
    def resource_type(self):
        return "LABORATORY"

    def is_bookable(self):
        return True

    def matches_capacity(self, attendees):
        """A laboratory is limited by its workstations as well as its seats."""
        attendees = int(attendees or 0)
        limit = min(self.capacity, self._workstations) if self._workstations else self.capacity
        return limit >= attendees

    def summary(self):
        return "%s laboratory | %d seats | %d workstations | %s safety" % (
            self._lab_type.title(), self.capacity, self._workstations,
            self._safety_level.lower())

    def to_dict(self):
        data = super().to_dict()
        data.update({"lab_type": self._lab_type, "safety_level": self._safety_level,
                     "workstations": self._workstations})
        return data


class ParkingArea(CampusResource):
    """Parking zone monitored by security through IoT parking sensors."""

    def __init__(self, *args, zone="A", total_slots=1, occupied_slots=0, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone = zone
        self._total_slots = int(total_slots or 0)
        self._occupied_slots = int(occupied_slots or 0)

    @property
    def zone(self):
        return self._zone

    @property
    def total_slots(self):
        return self._total_slots

    @property
    def occupied_slots(self):
        return self._occupied_slots

    @property
    def free_slots(self):
        return max(self._total_slots - self._occupied_slots, 0)

    @property
    def occupancy_rate(self):
        if not self._total_slots:
            return 0.0
        return round(self._occupied_slots / float(self._total_slots), 3)

    def update_occupancy(self, occupied_slots):
        occupied = int(occupied_slots)
        if occupied < 0 or occupied > self._total_slots:
            raise ValidationError(
                "Occupied slots must be between 0 and %d." % self._total_slots,
                {"field": "occupied_slots"})
        self._occupied_slots = occupied

    @property
    def resource_type(self):
        return "PARKING_AREA"

    def summary(self):
        return "Parking zone %s | %d/%d slots occupied" % (
            self._zone, self._occupied_slots, self._total_slots)

    def to_dict(self):
        data = super().to_dict()
        data.update({"zone": self._zone, "total_slots": self._total_slots,
                     "occupied_slots": self._occupied_slots,
                     "free_slots": self.free_slots,
                     "occupancy_rate": self.occupancy_rate})
        return data


class SmartDevice(CampusResource):
    """IoT endpoint that publishes readings for a monitored resource."""

    def __init__(self, *args, device_type="OCCUPANCY_SENSOR", firmware="1.0.0",
                 monitors_id=None, is_online=True, last_heartbeat=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_type = device_type
        self._firmware = firmware
        self._monitors_id = monitors_id
        self._is_online = bool(is_online)
        self._last_heartbeat = last_heartbeat

    @property
    def device_type(self):
        return self._device_type

    @property
    def firmware(self):
        return self._firmware

    @property
    def monitors_id(self):
        return self._monitors_id

    @property
    def is_online(self):
        return self._is_online

    @property
    def last_heartbeat(self):
        return self._last_heartbeat

    def is_operational(self):
        return self._is_online and self.status not in (STATUS_OFFLINE, STATUS_MAINTENANCE)

    @property
    def resource_type(self):
        return "SMART_DEVICE"

    def summary(self):
        return "%s | firmware %s | %s" % (
            self._device_type.replace("_", " ").title(), self._firmware,
            "online" if self.is_operational() else "offline")

    def to_dict(self):
        data = super().to_dict()
        data.update({"device_type": self._device_type, "firmware": self._firmware,
                     "monitors_id": self._monitors_id, "is_online": self._is_online,
                     "operational": self.is_operational(),
                     "last_heartbeat": self._last_heartbeat})
        return data


RESOURCE_CLASSES = {
    "CLASSROOM": Classroom,
    "LABORATORY": Laboratory,
    "PARKING_AREA": ParkingArea,
    "SMART_DEVICE": SmartDevice,
}

RESOURCE_LABELS = {
    "CLASSROOM": "Classroom",
    "LABORATORY": "Laboratory",
    "PARKING_AREA": "Parking area",
    "SMART_DEVICE": "Smart device",
}
