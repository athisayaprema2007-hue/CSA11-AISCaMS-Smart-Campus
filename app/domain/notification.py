"""Notification entity produced by the observer pattern."""

from ..exceptions import ValidationError
from ..utils import human_time, now, parse_datetime, to_db

CATEGORY_BOOKING = "BOOKING"
CATEGORY_REQUEST = "REQUEST"
CATEGORY_ALERT = "ALERT"
CATEGORY_EVENT = "EVENT"
CATEGORY_SYSTEM = "SYSTEM"
NOTIFICATION_CATEGORIES = (CATEGORY_BOOKING, CATEGORY_REQUEST, CATEGORY_ALERT,
                           CATEGORY_EVENT, CATEGORY_SYSTEM)


class Notification:
    """Message delivered to a single user's notification centre."""

    def __init__(self, notification_id, user_id, title, message, category,
                 entity_type=None, entity_id=None, is_read=False, created_at=None):
        if category not in NOTIFICATION_CATEGORIES:
            raise ValidationError("Unknown notification category: %s" % category,
                                  {"field": "category"})
        if not (title or "").strip():
            raise ValidationError("Notification title is required.", {"field": "title"})
        self._id = notification_id
        self._user_id = user_id
        self._title = title.strip()
        self._message = (message or "").strip()
        self._category = category
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._is_read = bool(is_read)
        self._created_at = parse_datetime(created_at) if created_at else now()

    @property
    def id(self):
        return self._id

    @property
    def user_id(self):
        return self._user_id

    @property
    def title(self):
        return self._title

    @property
    def message(self):
        return self._message

    @property
    def category(self):
        return self._category

    @property
    def entity_type(self):
        return self._entity_type

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def is_read(self):
        return self._is_read

    @property
    def created_at(self):
        return self._created_at

    def mark_read(self):
        self._is_read = True
        return self

    def to_dict(self):
        return {
            "id": self._id,
            "user_id": self._user_id,
            "title": self._title,
            "message": self._message,
            "category": self._category,
            "entity_type": self._entity_type,
            "entity_id": self._entity_id,
            "is_read": self._is_read,
            "created_at": to_db(self._created_at),
            "created_display": human_time(self._created_at),
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<Notification %s to user %s>" % (self._category, self._user_id)
