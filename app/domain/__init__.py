"""Domain layer: entities and business rules, independent of Flask and SQLite."""

from .academics import AttendanceRecord, Schedule
from .booking import Booking
from .events import CampusEvent
from .iot import IoTReading
from .notification import Notification
from .resources import (Building, CampusResource, Classroom, Laboratory,
                        ParkingArea, SmartDevice)
from .service_request import (HousekeepingRequest, ITSupportRequest,
                              MaintenanceRequest, SafetyRequest, ServiceRequest)
from .users import (Administrator, Faculty, MaintenanceStaff, Permission,
                    SecurityOfficer, Student, User, build_user)

__all__ = [
    "AttendanceRecord", "Schedule", "Booking", "CampusEvent", "IoTReading",
    "Notification", "Building", "CampusResource", "Classroom", "Laboratory",
    "ParkingArea", "SmartDevice", "ServiceRequest", "MaintenanceRequest",
    "SafetyRequest", "ITSupportRequest", "HousekeepingRequest", "User", "Student",
    "Faculty", "Administrator", "SecurityOfficer", "MaintenanceStaff",
    "Permission", "build_user",
]
