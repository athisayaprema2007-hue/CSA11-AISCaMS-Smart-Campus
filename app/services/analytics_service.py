"""Campus utilisation analytics used by the administrator dashboard."""

from ..domain.users import Permission
from ..exceptions import PermissionDeniedError
from ..utils import now


class AnalyticsService:
    """Aggregates read models across repositories for reporting screens."""

    def __init__(self, resource_repository, booking_repository, request_repository,
                 user_repository, iot_repository, alert_repository, event_repository):
        self._resources = resource_repository
        self._bookings = booking_repository
        self._requests = request_repository
        self._users = user_repository
        self._iot = iot_repository
        self._alerts = alert_repository
        self._events = event_repository

    def campus_utilisation(self, user=None):
        if user is not None and not user.has_permission(Permission.VIEW_ANALYTICS):
            raise PermissionDeniedError("%s users cannot view campus analytics." % user.role)
        type_counts = self._resources.type_counts()
        status_counts = self._resources.status_counts()
        booking_status = self._bookings.status_counts()
        request_status = self._requests.status_counts()
        bookable = type_counts.get("CLASSROOM", 0) + type_counts.get("LABORATORY", 0)
        available = status_counts.get("AVAILABLE", 0)
        return {
            "resource_types": type_counts,
            "resource_status": status_counts,
            "bookable_resources": bookable,
            "available_resources": available,
            "availability_rate": round((available / float(sum(status_counts.values()) or 1)) * 100, 1),
            "average_utilisation": round(self._resources.average_utilisation() * 100, 1),
            "classroom_utilisation": round(
                self._resources.average_utilisation("CLASSROOM") * 100, 1),
            "laboratory_utilisation": round(
                self._resources.average_utilisation("LABORATORY") * 100, 1),
            "booking_status": booking_status,
            "confirmed_bookings": booking_status.get("CONFIRMED", 0),
            "pending_bookings": booking_status.get("PENDING", 0),
            "booked_hours": self._bookings.booked_hours(),
            "top_resources": self._bookings.top_resources(),
            "request_status": request_status,
            "open_requests": sum(request_status.get(key, 0)
                                 for key in ("NEW", "ASSIGNED", "IN_PROGRESS")),
            "request_categories": self._requests.category_counts(),
            "request_priorities": self._requests.priority_counts(),
            "breached_requests": len(self._requests.breached(now())),
            "user_counts": self._users.role_counts(),
            "iot_severity": self._iot.severity_counts(),
            "alert_counts": self._alerts.status_counts(),
            "upcoming_events": len(self._events.list_events(upcoming_only=True)),
        }
