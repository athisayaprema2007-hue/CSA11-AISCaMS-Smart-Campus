"""Booking entity: a time bounded reservation of a bookable campus resource."""

from ..exceptions import ValidationError
from ..utils import human_time, hours_between, parse_datetime, to_db

STATUS_PENDING = "PENDING"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELLED = "CANCELLED"
STATUS_COMPLETED = "COMPLETED"
BOOKING_STATUSES = (STATUS_PENDING, STATUS_CONFIRMED, STATUS_REJECTED,
                    STATUS_CANCELLED, STATUS_COMPLETED)

#: Statuses that still occupy the resource on the calendar.
BLOCKING_STATUSES = (STATUS_PENDING, STATUS_CONFIRMED)

MAX_DURATION_HOURS = 8


class Booking:
    """Reservation of a classroom or laboratory."""

    def __init__(self, booking_id, reference, resource_id, user_id, purpose,
                 start_time, end_time, attendees=1, status=STATUS_CONFIRMED,
                 approved_by=None, created_at=None, resource_code=None,
                 resource_name=None, user_name=None):
        self._id = booking_id
        self._reference = reference
        self._resource_id = resource_id
        self._user_id = user_id
        self._purpose = self._validate_purpose(purpose)
        self._start_time = parse_datetime(start_time, "start time")
        self._end_time = parse_datetime(end_time, "end time")
        self._validate_window()
        self._attendees = self._validate_attendees(attendees)
        if status not in BOOKING_STATUSES:
            raise ValidationError("Unknown booking status: %s" % status, {"field": "status"})
        self._status = status
        self._approved_by = approved_by
        self._created_at = created_at
        # Denormalised display context supplied by the repository.
        self.resource_code = resource_code
        self.resource_name = resource_name
        self.user_name = user_name

    # ------------------------------------------------------------ validation
    @staticmethod
    def _validate_purpose(purpose):
        text = (purpose or "").strip()
        if len(text) < 3:
            raise ValidationError("Purpose must be at least 3 characters.",
                                  {"field": "purpose"})
        return text

    @staticmethod
    def _validate_attendees(attendees):
        try:
            count = int(attendees)
        except (TypeError, ValueError):
            raise ValidationError("Attendees must be a whole number.",
                                  {"field": "attendees"})
        if count < 1:
            raise ValidationError("At least one attendee is required.",
                                  {"field": "attendees"})
        return count

    def _validate_window(self):
        if self._end_time <= self._start_time:
            raise ValidationError("End time must be after the start time.",
                                  {"field": "end_time"})
        if self.duration_hours > MAX_DURATION_HOURS:
            raise ValidationError(
                "A booking cannot exceed %d hours." % MAX_DURATION_HOURS,
                {"field": "end_time"})

    # ------------------------------------------------------------ properties
    @property
    def id(self):
        return self._id

    @property
    def reference(self):
        return self._reference

    @property
    def resource_id(self):
        return self._resource_id

    @property
    def user_id(self):
        return self._user_id

    @property
    def purpose(self):
        return self._purpose

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def attendees(self):
        return self._attendees

    @property
    def status(self):
        return self._status

    @property
    def approved_by(self):
        return self._approved_by

    @property
    def created_at(self):
        return self._created_at

    @property
    def duration_hours(self):
        return hours_between(self._start_time, self._end_time)

    # ------------------------------------------------------------- behaviour
    def overlaps(self, start, end):
        """True when the given window intersects this booking."""
        start = parse_datetime(start, "start time")
        end = parse_datetime(end, "end time")
        return self._start_time < end and start < self._end_time

    def blocks_calendar(self):
        return self._status in BLOCKING_STATUSES

    def confirm(self, approver_id=None):
        if self._status not in (STATUS_PENDING, STATUS_CONFIRMED):
            raise ValidationError("Only a pending booking can be confirmed.",
                                  {"field": "status"})
        self._status = STATUS_CONFIRMED
        self._approved_by = approver_id

    def reject(self, approver_id=None):
        if self._status != STATUS_PENDING:
            raise ValidationError("Only a pending booking can be rejected.",
                                  {"field": "status"})
        self._status = STATUS_REJECTED
        self._approved_by = approver_id

    def cancel(self):
        if self._status in (STATUS_CANCELLED, STATUS_COMPLETED, STATUS_REJECTED):
            raise ValidationError("This booking can no longer be cancelled.",
                                  {"field": "status"})
        self._status = STATUS_CANCELLED

    def complete(self):
        if self._status != STATUS_CONFIRMED:
            raise ValidationError("Only a confirmed booking can be completed.",
                                  {"field": "status"})
        self._status = STATUS_COMPLETED

    def to_dict(self):
        return {
            "id": self._id,
            "reference": self._reference,
            "resource_id": self._resource_id,
            "resource_code": self.resource_code,
            "resource_name": self.resource_name,
            "user_id": self._user_id,
            "user_name": self.user_name,
            "purpose": self._purpose,
            "start_time": to_db(self._start_time),
            "end_time": to_db(self._end_time),
            "start_display": human_time(self._start_time),
            "end_display": human_time(self._end_time),
            "duration_hours": self.duration_hours,
            "attendees": self._attendees,
            "status": self._status,
            "approved_by": self._approved_by,
            "created_at": self._created_at,
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<Booking %s %s>" % (self._reference, self._status)
