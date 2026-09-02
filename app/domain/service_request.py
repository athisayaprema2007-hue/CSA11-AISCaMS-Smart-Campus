"""Service request hierarchy and its state machine.

`ServiceRequest` is abstract; each concrete category owns its own SLA matrix,
which is the polymorphic behaviour the maintenance workflow depends on.  The
objects are created by `ServiceRequestFactory` (see `app.patterns.factory`).
"""

from abc import ABC, abstractmethod

from ..exceptions import InvalidTransitionError, ValidationError
from ..utils import add_hours, human_time, now, parse_datetime, to_db

STATUS_NEW = "NEW"
STATUS_ASSIGNED = "ASSIGNED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_RESOLVED = "RESOLVED"
STATUS_CLOSED = "CLOSED"
STATUS_REJECTED = "REJECTED"
REQUEST_STATUSES = (STATUS_NEW, STATUS_ASSIGNED, STATUS_IN_PROGRESS,
                    STATUS_RESOLVED, STATUS_CLOSED, STATUS_REJECTED)

#: Legal state transitions of the service request lifecycle.
ALLOWED_TRANSITIONS = {
    STATUS_NEW: (STATUS_ASSIGNED, STATUS_REJECTED),
    STATUS_ASSIGNED: (STATUS_IN_PROGRESS, STATUS_REJECTED),
    STATUS_IN_PROGRESS: (STATUS_RESOLVED,),
    STATUS_RESOLVED: (STATUS_CLOSED, STATUS_IN_PROGRESS),
    STATUS_CLOSED: (),
    STATUS_REJECTED: (),
}

OPEN_STATUSES = (STATUS_NEW, STATUS_ASSIGNED, STATUS_IN_PROGRESS)

PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"
PRIORITY_CRITICAL = "CRITICAL"
PRIORITIES = (PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL)
PRIORITY_ORDER = {PRIORITY_LOW: 0, PRIORITY_MEDIUM: 1, PRIORITY_HIGH: 2, PRIORITY_CRITICAL: 3}

#: Human readable category names used across the interface.
CATEGORY_LABELS = {
    "MAINTENANCE": "Maintenance",
    "SAFETY": "Safety",
    "IT_SUPPORT": "IT support",
    "HOUSEKEEPING": "Housekeeping",
}


class ServiceRequest(ABC):
    """Abstract campus service ticket."""

    #: Category discriminator stored in the database.
    CATEGORY = None
    #: Resolution time promised for each priority, in hours.
    SLA_MATRIX = {PRIORITY_CRITICAL: 2, PRIORITY_HIGH: 8, PRIORITY_MEDIUM: 24, PRIORITY_LOW: 72}

    def __init__(self, request_id, ticket, resource_id, title, description,
                 priority=PRIORITY_MEDIUM, status=STATUS_NEW, raised_by=None,
                 assigned_to=None, source="USER", sla_hours=None, sla_due_at=None,
                 created_at=None, updated_at=None, resolved_at=None, closed_at=None,
                 resource_code=None, resource_name=None, raised_by_name=None,
                 assigned_to_name=None):
        if priority not in PRIORITIES:
            raise ValidationError("Unknown priority: %s" % priority, {"field": "priority"})
        if status not in REQUEST_STATUSES:
            raise ValidationError("Unknown status: %s" % status, {"field": "status"})
        if source not in ("USER", "IOT"):
            raise ValidationError("Unknown source: %s" % source, {"field": "source"})
        self._id = request_id
        self._ticket = ticket
        self._resource_id = resource_id
        self._title = self._validate_title(title)
        self._description = self._validate_description(description)
        self._priority = priority
        self._status = status
        self._raised_by = raised_by
        self._assigned_to = assigned_to
        self._source = source
        self._created_at = parse_datetime(created_at) if created_at else now()
        self._sla_hours = int(sla_hours) if sla_hours else self.sla_hours_for(priority)
        self._sla_due_at = (parse_datetime(sla_due_at) if sla_due_at
                            else add_hours(self._created_at, self._sla_hours))
        self._updated_at = parse_datetime(updated_at) if updated_at else self._created_at
        self._resolved_at = parse_datetime(resolved_at) if resolved_at else None
        self._closed_at = parse_datetime(closed_at) if closed_at else None
        # Denormalised display context supplied by the repository.
        self.resource_code = resource_code
        self.resource_name = resource_name
        self.raised_by_name = raised_by_name
        self.assigned_to_name = assigned_to_name
        self.history = []

    # ------------------------------------------------------------ validation
    @staticmethod
    def _validate_title(title):
        text = (title or "").strip()
        if len(text) < 3:
            raise ValidationError("Title must be at least 3 characters.", {"field": "title"})
        return text

    @staticmethod
    def _validate_description(description):
        text = (description or "").strip()
        if len(text) < 5:
            raise ValidationError("Description must be at least 5 characters.",
                                  {"field": "description"})
        return text

    # -------------------------------------------------------- polymorphism
    @property
    def category(self):
        return self.CATEGORY

    @property
    def category_label(self):
        return CATEGORY_LABELS.get(self.CATEGORY, self.CATEGORY)

    @classmethod
    def sla_hours_for(cls, priority):
        """SLA promised by this request category for a given priority."""
        if priority not in PRIORITIES:
            raise ValidationError("Unknown priority: %s" % priority, {"field": "priority"})
        return cls.SLA_MATRIX[priority]

    @abstractmethod
    def handling_team(self):
        """Team responsible for resolving this category of request."""

    # ------------------------------------------------------------ properties
    @property
    def id(self):
        return self._id

    @property
    def ticket(self):
        return self._ticket

    @property
    def resource_id(self):
        return self._resource_id

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def priority(self):
        return self._priority

    @property
    def status(self):
        return self._status

    @property
    def raised_by(self):
        return self._raised_by

    @property
    def assigned_to(self):
        return self._assigned_to

    @property
    def source(self):
        return self._source

    @property
    def sla_hours(self):
        return self._sla_hours

    @property
    def sla_due_at(self):
        return self._sla_due_at

    @property
    def created_at(self):
        return self._created_at

    @property
    def updated_at(self):
        return self._updated_at

    @property
    def resolved_at(self):
        return self._resolved_at

    @property
    def closed_at(self):
        return self._closed_at

    # ------------------------------------------------------------- behaviour
    def is_open(self):
        return self._status in OPEN_STATUSES

    def can_transition_to(self, new_status):
        return new_status in ALLOWED_TRANSITIONS.get(self._status, ())

    def transition_to(self, new_status, timestamp=None):
        """Move the ticket along its lifecycle, refusing illegal jumps."""
        if new_status not in REQUEST_STATUSES:
            raise ValidationError("Unknown status: %s" % new_status, {"field": "status"})
        if new_status == self._status:
            raise InvalidTransitionError(
                "Request %s is already %s." % (self._ticket, new_status),
                {"from": self._status, "to": new_status})
        if not self.can_transition_to(new_status):
            raise InvalidTransitionError(
                "Cannot move request %s from %s to %s." % (self._ticket, self._status, new_status),
                {"from": self._status, "to": new_status,
                 "allowed": list(ALLOWED_TRANSITIONS.get(self._status, ()))})
        if new_status == STATUS_ASSIGNED and not self._assigned_to:
            raise InvalidTransitionError(
                "A request must have an assignee before it can be marked assigned.",
                {"field": "assigned_to"})
        previous = self._status
        stamp = parse_datetime(timestamp) if timestamp else now()
        self._status = new_status
        self._updated_at = stamp
        if new_status == STATUS_RESOLVED:
            self._resolved_at = stamp
        elif new_status == STATUS_CLOSED:
            self._closed_at = stamp
        elif new_status == STATUS_IN_PROGRESS:
            self._resolved_at = None
        return previous

    def assign(self, staff_id):
        if not staff_id:
            raise ValidationError("An assignee is required.", {"field": "assigned_to"})
        if self._status not in (STATUS_NEW, STATUS_ASSIGNED):
            raise InvalidTransitionError(
                "Only a new or assigned request can be (re)assigned.",
                {"from": self._status})
        self._assigned_to = staff_id
        if self._status == STATUS_NEW:
            self.transition_to(STATUS_ASSIGNED)
        return self

    def escalate(self):
        """Raise the priority one level and shorten the SLA accordingly."""
        order = PRIORITY_ORDER[self._priority]
        if order >= PRIORITY_ORDER[PRIORITY_CRITICAL]:
            return self
        self._priority = PRIORITIES[order + 1]
        self._sla_hours = self.sla_hours_for(self._priority)
        self._sla_due_at = add_hours(self._created_at, self._sla_hours)
        return self

    def sla_remaining_hours(self, reference=None):
        reference = reference or now()
        return round((self._sla_due_at - reference).total_seconds() / 3600.0, 2)

    def sla_state(self, reference=None):
        """ON_TRACK / AT_RISK / BREACHED for open tickets, MET / MISSED once done."""
        reference = reference or now()
        if self._status in (STATUS_RESOLVED, STATUS_CLOSED):
            finished = self._resolved_at or self._closed_at or reference
            return "MET" if finished <= self._sla_due_at else "MISSED"
        if self._status == STATUS_REJECTED:
            return "NOT_APPLICABLE"
        remaining = self.sla_remaining_hours(reference)
        if remaining < 0:
            return "BREACHED"
        if remaining <= max(self._sla_hours * 0.25, 1):
            return "AT_RISK"
        return "ON_TRACK"

    def to_dict(self, reference=None):
        return {
            "id": self._id,
            "ticket": self._ticket,
            "resource_id": self._resource_id,
            "resource_code": self.resource_code,
            "resource_name": self.resource_name,
            "title": self._title,
            "description": self._description,
            "category": self.category,
            "category_label": self.category_label,
            "handling_team": self.handling_team(),
            "priority": self._priority,
            "status": self._status,
            "source": self._source,
            "raised_by": self._raised_by,
            "raised_by_name": self.raised_by_name,
            "assigned_to": self._assigned_to,
            "assigned_to_name": self.assigned_to_name,
            "sla_hours": self._sla_hours,
            "sla_due_at": to_db(self._sla_due_at),
            "sla_due_display": human_time(self._sla_due_at),
            "sla_state": self.sla_state(reference),
            "sla_remaining_hours": self.sla_remaining_hours(reference),
            "created_at": to_db(self._created_at),
            "created_display": human_time(self._created_at),
            "updated_at": to_db(self._updated_at),
            "resolved_at": to_db(self._resolved_at),
            "closed_at": to_db(self._closed_at),
            "is_open": self.is_open(),
            "next_states": list(ALLOWED_TRANSITIONS.get(self._status, ())),
            "history": list(self.history),
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<%s %s %s/%s>" % (self.__class__.__name__, self._ticket,
                                  self._priority, self._status)


class MaintenanceRequest(ServiceRequest):
    """Physical infrastructure faults: air-conditioning, lighting, furniture."""

    CATEGORY = "MAINTENANCE"
    SLA_MATRIX = {PRIORITY_CRITICAL: 2, PRIORITY_HIGH: 8, PRIORITY_MEDIUM: 24, PRIORITY_LOW: 72}

    def handling_team(self):
        return "Facilities maintenance"


class SafetyRequest(ServiceRequest):
    """Safety or security hazards; the tightest SLA of all categories."""

    CATEGORY = "SAFETY"
    SLA_MATRIX = {PRIORITY_CRITICAL: 1, PRIORITY_HIGH: 4, PRIORITY_MEDIUM: 12, PRIORITY_LOW: 24}

    def handling_team(self):
        return "Campus safety and security"


class ITSupportRequest(ServiceRequest):
    """Projectors, network, laboratory computers and other IT equipment."""

    CATEGORY = "IT_SUPPORT"
    SLA_MATRIX = {PRIORITY_CRITICAL: 2, PRIORITY_HIGH: 6, PRIORITY_MEDIUM: 16, PRIORITY_LOW: 48}

    def handling_team(self):
        return "Campus IT support"


class HousekeepingRequest(ServiceRequest):
    """Cleaning, waste removal and hygiene tasks."""

    CATEGORY = "HOUSEKEEPING"
    SLA_MATRIX = {PRIORITY_CRITICAL: 2, PRIORITY_HIGH: 8, PRIORITY_MEDIUM: 12, PRIORITY_LOW: 36}

    def handling_team(self):
        return "Housekeeping services"


REQUEST_CLASSES = {
    "MAINTENANCE": MaintenanceRequest,
    "SAFETY": SafetyRequest,
    "IT_SUPPORT": ITSupportRequest,
    "HOUSEKEEPING": HousekeepingRequest,
}
