"""User hierarchy.

`User` is an abstract base class: it encapsulates the identity attributes that
every campus member shares and declares the operations that each concrete role
must supply.  The concrete roles differ only in behaviour (permissions,
dashboard composition, job title), which keeps the hierarchy cohesive and lets
the rest of the system depend on the abstraction instead of on role checks.
"""

from abc import ABC, abstractmethod

from ..exceptions import ValidationError


class Permission:
    """Named permissions used for role based access control."""

    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    VIEW_SCHEDULE = "VIEW_SCHEDULE"
    SEARCH_RESOURCES = "SEARCH_RESOURCES"
    VIEW_RECOMMENDATIONS = "VIEW_RECOMMENDATIONS"
    BOOK_RESOURCE = "BOOK_RESOURCE"
    APPROVE_BOOKING = "APPROVE_BOOKING"
    SUBMIT_REQUEST = "SUBMIT_REQUEST"
    TRACK_REQUEST = "TRACK_REQUEST"
    ASSIGN_REQUEST = "ASSIGN_REQUEST"
    UPDATE_REQUEST_STATUS = "UPDATE_REQUEST_STATUS"
    UPDATE_EQUIPMENT = "UPDATE_EQUIPMENT"
    RECORD_ATTENDANCE = "RECORD_ATTENDANCE"
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_RESOURCES = "MANAGE_RESOURCES"
    MANAGE_EVENTS = "MANAGE_EVENTS"
    VIEW_EVENTS = "VIEW_EVENTS"
    VIEW_ANALYTICS = "VIEW_ANALYTICS"
    VIEW_IOT = "VIEW_IOT"
    MONITOR_PARKING = "MONITOR_PARKING"
    ACKNOWLEDGE_ALERT = "ACKNOWLEDGE_ALERT"
    ACCESS_DIGITAL_SERVICES = "ACCESS_DIGITAL_SERVICES"


class User(ABC):
    """Abstract campus user."""

    def __init__(self, user_id, username, full_name, email, department=None,
                 phone=None, is_active=True):
        self._id = user_id
        self._username = self._validate_username(username)
        self._full_name = self._validate_name(full_name)
        self._email = self._validate_email(email)
        self._department = department
        self._phone = phone
        self._is_active = bool(is_active)

    # ------------------------------------------------------------ validation
    @staticmethod
    def _validate_username(username):
        text = (username or "").strip()
        if len(text) < 3:
            raise ValidationError("Username must be at least 3 characters.",
                                  {"field": "username"})
        return text

    @staticmethod
    def _validate_name(full_name):
        text = (full_name or "").strip()
        if not text:
            raise ValidationError("Full name is required.", {"field": "full_name"})
        return text

    @staticmethod
    def _validate_email(email):
        text = (email or "").strip().lower()
        if "@" not in text or "." not in text.split("@")[-1]:
            raise ValidationError("A valid email address is required.", {"field": "email"})
        return text

    # ------------------------------------------------------------ properties
    @property
    def id(self):
        return self._id

    @property
    def username(self):
        return self._username

    @property
    def full_name(self):
        return self._full_name

    @property
    def email(self):
        return self._email

    @property
    def department(self):
        return self._department

    @property
    def phone(self):
        return self._phone

    @property
    def is_active(self):
        return self._is_active

    # --------------------------------------------------------- polymorphism
    @property
    @abstractmethod
    def role(self):
        """Role code stored in the `roles` table."""

    @property
    @abstractmethod
    def job_title(self):
        """Human readable title shown in the interface."""

    @abstractmethod
    def permissions(self):
        """Set of permissions granted to this role."""

    @abstractmethod
    def landing_page(self):
        """Endpoint the user is redirected to after signing in."""

    def dashboard_sections(self):
        """Ordered list of dashboard section keys for this role."""
        return ["overview"]

    def has_permission(self, permission):
        return permission in self.permissions()

    def deactivate(self):
        self._is_active = False

    def activate(self):
        self._is_active = True

    def to_dict(self):
        return {
            "id": self._id,
            "username": self._username,
            "full_name": self._full_name,
            "email": self._email,
            "department": self._department,
            "phone": self._phone,
            "is_active": self._is_active,
            "role": self.role,
            "job_title": self.job_title,
            "permissions": sorted(self.permissions()),
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<%s id=%s username=%s>" % (self.__class__.__name__, self._id, self._username)


class Student(User):
    """Learner: books resources, raises requests and follows a timetable."""

    @property
    def role(self):
        return "STUDENT"

    @property
    def job_title(self):
        return "Student - %s" % (self.department or "Campus")

    def permissions(self):
        return frozenset({
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_SCHEDULE,
            Permission.SEARCH_RESOURCES,
            Permission.VIEW_RECOMMENDATIONS,
            Permission.BOOK_RESOURCE,
            Permission.SUBMIT_REQUEST,
            Permission.TRACK_REQUEST,
            Permission.VIEW_EVENTS,
            Permission.ACCESS_DIGITAL_SERVICES,
        })

    def landing_page(self):
        return "views.dashboard"

    def dashboard_sections(self):
        return ["today_classes", "my_bookings", "my_requests", "upcoming_events",
                "digital_services", "notifications"]


class Faculty(User):
    """Teaching staff: manages classes, attendance and classroom bookings."""

    @property
    def role(self):
        return "FACULTY"

    @property
    def job_title(self):
        return "Faculty - %s" % (self.department or "Campus")

    def permissions(self):
        return frozenset({
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_SCHEDULE,
            Permission.SEARCH_RESOURCES,
            Permission.VIEW_RECOMMENDATIONS,
            Permission.BOOK_RESOURCE,
            Permission.SUBMIT_REQUEST,
            Permission.TRACK_REQUEST,
            Permission.RECORD_ATTENDANCE,
            Permission.VIEW_EVENTS,
            Permission.ACCESS_DIGITAL_SERVICES,
        })

    def landing_page(self):
        return "views.dashboard"

    def dashboard_sections(self):
        return ["teaching_load", "today_classes", "attendance", "my_bookings",
                "my_requests", "notifications"]


class Administrator(User):
    """Campus administrator: full oversight of users, resources and requests."""

    @property
    def role(self):
        return "ADMIN"

    @property
    def job_title(self):
        return "Campus Administrator"

    def permissions(self):
        return frozenset({
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_SCHEDULE,
            Permission.SEARCH_RESOURCES,
            Permission.VIEW_RECOMMENDATIONS,
            Permission.BOOK_RESOURCE,
            Permission.APPROVE_BOOKING,
            Permission.SUBMIT_REQUEST,
            Permission.TRACK_REQUEST,
            Permission.ASSIGN_REQUEST,
            Permission.UPDATE_REQUEST_STATUS,
            Permission.MANAGE_USERS,
            Permission.MANAGE_RESOURCES,
            Permission.MANAGE_EVENTS,
            Permission.VIEW_EVENTS,
            Permission.VIEW_ANALYTICS,
            Permission.VIEW_IOT,
            Permission.MONITOR_PARKING,
            Permission.ACKNOWLEDGE_ALERT,
            Permission.ACCESS_DIGITAL_SERVICES,
        })

    def landing_page(self):
        return "views.admin"

    def dashboard_sections(self):
        return ["utilisation", "pending_approvals", "open_requests", "sla",
                "events", "users"]


class SecurityOfficer(User):
    """Security personnel: parking occupancy, alerts and IoT safety readings."""

    @property
    def role(self):
        return "SECURITY"

    @property
    def job_title(self):
        return "Security Officer"

    def permissions(self):
        return frozenset({
            Permission.VIEW_DASHBOARD,
            Permission.SEARCH_RESOURCES,
            Permission.SUBMIT_REQUEST,
            Permission.TRACK_REQUEST,
            Permission.VIEW_EVENTS,
            Permission.VIEW_IOT,
            Permission.MONITOR_PARKING,
            Permission.ACKNOWLEDGE_ALERT,
        })

    def landing_page(self):
        return "views.security"

    def dashboard_sections(self):
        return ["parking", "alerts", "iot_readings"]


class MaintenanceStaff(User):
    """Maintenance technician: works the assigned service request queue."""

    @property
    def role(self):
        return "MAINTENANCE"

    @property
    def job_title(self):
        return "Maintenance Technician - %s" % (self.department or "Facilities")

    def permissions(self):
        return frozenset({
            Permission.VIEW_DASHBOARD,
            Permission.SEARCH_RESOURCES,
            Permission.TRACK_REQUEST,
            Permission.UPDATE_REQUEST_STATUS,
            Permission.UPDATE_EQUIPMENT,
            Permission.VIEW_IOT,
        })

    def landing_page(self):
        return "views.maintenance"

    def dashboard_sections(self):
        return ["assigned_requests", "sla", "equipment"]


ROLE_CLASSES = {
    "STUDENT": Student,
    "FACULTY": Faculty,
    "ADMIN": Administrator,
    "SECURITY": SecurityOfficer,
    "MAINTENANCE": MaintenanceStaff,
}

ROLE_LABELS = {
    "STUDENT": "Student",
    "FACULTY": "Faculty Member",
    "ADMIN": "Administrator",
    "SECURITY": "Security Personnel",
    "MAINTENANCE": "Maintenance Staff",
}


def build_user(role, **kwargs):
    """Instantiate the concrete `User` subclass matching a role code."""
    try:
        cls = ROLE_CLASSES[str(role).upper()]
    except KeyError:
        raise ValidationError("Unknown role: %s" % role, {"field": "role"})
    return cls(**kwargs)
