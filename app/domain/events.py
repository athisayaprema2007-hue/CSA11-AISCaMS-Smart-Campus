"""Campus event entity."""

from ..exceptions import ValidationError
from ..utils import human_time, now, parse_datetime, to_db

STATUS_SCHEDULED = "SCHEDULED"
STATUS_ONGOING = "ONGOING"
STATUS_COMPLETED = "COMPLETED"
STATUS_CANCELLED = "CANCELLED"
EVENT_STATUSES = (STATUS_SCHEDULED, STATUS_ONGOING, STATUS_COMPLETED, STATUS_CANCELLED)


class CampusEvent:
    """An event organised on campus, optionally hosted by a campus resource."""

    def __init__(self, event_id, title, description, category, start_time, end_time,
                 capacity, organiser_id, venue_id=None, status=STATUS_SCHEDULED,
                 venue_code=None, venue_name=None, organiser_name=None,
                 registrations=0, registered=False):
        title = (title or "").strip()
        if len(title) < 3:
            raise ValidationError("Event title must be at least 3 characters.",
                                  {"field": "title"})
        if int(capacity) < 1:
            raise ValidationError("Event capacity must be positive.", {"field": "capacity"})
        if status not in EVENT_STATUSES:
            raise ValidationError("Unknown event status: %s" % status, {"field": "status"})
        self._id = event_id
        self._title = title
        self._description = (description or "").strip()
        self._category = category
        self._start_time = parse_datetime(start_time, "start time")
        self._end_time = parse_datetime(end_time, "end time")
        if self._end_time <= self._start_time:
            raise ValidationError("Event end time must be after the start time.",
                                  {"field": "end_time"})
        self._capacity = int(capacity)
        self._organiser_id = organiser_id
        self._venue_id = venue_id
        self._status = status
        self.venue_code = venue_code
        self.venue_name = venue_name
        self.organiser_name = organiser_name
        self.registrations = int(registrations or 0)
        self.registered = bool(registered)

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def category(self):
        return self._category

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def capacity(self):
        return self._capacity

    @property
    def organiser_id(self):
        return self._organiser_id

    @property
    def venue_id(self):
        return self._venue_id

    @property
    def status(self):
        return self._status

    @property
    def seats_left(self):
        return max(self._capacity - self.registrations, 0)

    def is_upcoming(self, reference=None):
        return self._start_time > (reference or now()) and self._status == STATUS_SCHEDULED

    def is_full(self):
        return self.seats_left <= 0

    def cancel(self):
        if self._status in (STATUS_COMPLETED, STATUS_CANCELLED):
            raise ValidationError("This event can no longer be cancelled.", {"field": "status"})
        self._status = STATUS_CANCELLED

    def to_dict(self):
        return {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "category": self._category,
            "venue_id": self._venue_id,
            "venue_code": self.venue_code,
            "venue_name": self.venue_name,
            "organiser_id": self._organiser_id,
            "organiser_name": self.organiser_name,
            "start_time": to_db(self._start_time),
            "end_time": to_db(self._end_time),
            "start_display": human_time(self._start_time),
            "end_display": human_time(self._end_time),
            "capacity": self._capacity,
            "registrations": self.registrations,
            "seats_left": self.seats_left,
            "registered": self.registered,
            "status": self._status,
            "upcoming": self.is_upcoming(),
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<CampusEvent %s>" % self._title
