"""Observer pattern - campus wide event notifications.

Services publish domain events to a `Subject` (the campus event bus).  Observers
decide independently what to do: persist a notification, raise an alert, or keep
an audit trail.  Publishers stay decoupled from every consumer.
"""

from abc import ABC, abstractmethod

# Domain event names published by the services.
BOOKING_CREATED = "BOOKING_CREATED"
BOOKING_CANCELLED = "BOOKING_CANCELLED"
BOOKING_APPROVED = "BOOKING_APPROVED"
BOOKING_REJECTED = "BOOKING_REJECTED"
REQUEST_CREATED = "REQUEST_CREATED"
REQUEST_ASSIGNED = "REQUEST_ASSIGNED"
REQUEST_STATUS_CHANGED = "REQUEST_STATUS_CHANGED"
IOT_READING_RECORDED = "IOT_READING_RECORDED"
IOT_CRITICAL_ALERT = "IOT_CRITICAL_ALERT"
ALERT_ACKNOWLEDGED = "ALERT_ACKNOWLEDGED"
EVENT_PUBLISHED = "EVENT_PUBLISHED"


class Observer(ABC):
    """Anything that reacts to a campus domain event."""

    #: Event names this observer cares about; empty tuple means "all events".
    interests = ()

    def handles(self, event_name):
        return not self.interests or event_name in self.interests

    @abstractmethod
    def update(self, event_name, payload):
        """React to a published event."""


class Subject:
    """The observable campus event bus."""

    def __init__(self):
        self._observers = []

    @property
    def observers(self):
        return tuple(self._observers)

    def attach(self, observer):
        if not isinstance(observer, Observer):
            raise TypeError("Only Observer instances can be attached.")
        if observer not in self._observers:
            self._observers.append(observer)
        return observer

    def detach(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)
        return observer

    def notify(self, event_name, payload=None):
        """Publish an event and return the observers that reacted."""
        payload = payload or {}
        reacted = []
        for observer in list(self._observers):
            if observer.handles(event_name):
                observer.update(event_name, payload)
                reacted.append(observer)
        return reacted


class NotificationObserver(Observer):
    """Persists a `Notification` for every recipient carried by the event."""

    CATEGORY_BY_EVENT = {
        BOOKING_CREATED: "BOOKING",
        BOOKING_CANCELLED: "BOOKING",
        BOOKING_APPROVED: "BOOKING",
        BOOKING_REJECTED: "BOOKING",
        REQUEST_CREATED: "REQUEST",
        REQUEST_ASSIGNED: "REQUEST",
        REQUEST_STATUS_CHANGED: "REQUEST",
        IOT_CRITICAL_ALERT: "ALERT",
        ALERT_ACKNOWLEDGED: "ALERT",
        EVENT_PUBLISHED: "EVENT",
    }

    interests = tuple(CATEGORY_BY_EVENT.keys())

    def __init__(self, notification_repository):
        self._notifications = notification_repository
        self.delivered = 0

    def update(self, event_name, payload):
        recipients = [user_id for user_id in payload.get("recipients", []) if user_id]
        if not recipients:
            return
        category = self.CATEGORY_BY_EVENT.get(event_name, "SYSTEM")
        title = payload.get("title") or event_name.replace("_", " ").title()
        message = payload.get("message") or ""
        for user_id in dict.fromkeys(recipients):
            self._notifications.add(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                entity_type=payload.get("entity_type"),
                entity_id=payload.get("entity_id"),
            )
            self.delivered += 1


class AlertObserver(Observer):
    """Registers an infrastructure alert whenever a critical reading arrives."""

    interests = (IOT_CRITICAL_ALERT,)

    def __init__(self, alert_repository):
        self._alerts = alert_repository
        self.raised = 0

    def update(self, event_name, payload):
        reading = payload.get("reading")
        if reading is None:
            return
        alert_id = self._alerts.add(
            reading_id=reading.id,
            resource_id=reading.resource_id or reading.device_id,
            request_id=payload.get("request_id"),
            alert_type=reading.metric,
            severity=reading.severity if reading.severity != "NORMAL" else "WARNING",
            message=payload.get("message") or reading.describe(),
        )
        payload["alert_id"] = alert_id
        self.raised += 1


class AuditTrailObserver(Observer):
    """In-memory audit trail; used by the tests and the admin activity feed."""

    def __init__(self, limit=200):
        self.entries = []
        self._limit = limit

    def update(self, event_name, payload):
        self.entries.append({
            "event": event_name,
            "entity_type": payload.get("entity_type"),
            "entity_id": payload.get("entity_id"),
            "message": payload.get("message", ""),
        })
        if len(self.entries) > self._limit:
            self.entries.pop(0)

    def events_of(self, event_name):
        return [entry for entry in self.entries if entry["event"] == event_name]
