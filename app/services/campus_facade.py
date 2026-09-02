"""Facade pattern - one entry point for every campus workflow.

The web layer never talks to a repository or to a pattern directly: it asks the
`CampusFacade`, which wires the repositories, the observer bus and the services
together and exposes coarse grained operations such as "recommend and explain",
"book a resource" or "ingest an IoT reading".
"""

from ..domain.users import Permission
from ..exceptions import PermissionDeniedError
from ..patterns.observer import (AlertObserver, AuditTrailObserver,
                                 NotificationObserver, Subject)
from ..repositories import RepositoryRegistry
from ..utils import day_code, now, to_db
from .analytics_service import AnalyticsService
from .booking_service import BookingService
from .iot_service import IoTService
from .maintenance_service import MaintenanceService
from .recommendation_service import RecommendationService


class CampusFacade:
    """Coordinates the AISCaMS subsystems behind a single interface."""

    def __init__(self, connection):
        self.repos = RepositoryRegistry(connection)

        # Observer pattern: one bus, three independent observers.
        self.bus = Subject()
        self.notification_observer = self.bus.attach(
            NotificationObserver(self.repos.notifications))
        self.alert_observer = self.bus.attach(AlertObserver(self.repos.alerts))
        self.audit_observer = self.bus.attach(AuditTrailObserver())

        self.bookings = BookingService(self.repos.bookings, self.repos.resources,
                                       self.repos.users, self.bus)
        self.maintenance = MaintenanceService(self.repos.requests, self.repos.resources,
                                              self.repos.users, self.bus)
        self.recommendations = RecommendationService(self.repos.resources,
                                                     self.repos.bookings, self.repos.iot)
        self.iot = IoTService(self.repos.iot, self.repos.alerts, self.repos.resources,
                              self.repos.users, self.maintenance, self.bus)
        self.analytics = AnalyticsService(self.repos.resources, self.repos.bookings,
                                          self.repos.requests, self.repos.users,
                                          self.repos.iot, self.repos.alerts,
                                          self.repos.events)

    # ------------------------------------------------------------ identity
    def authenticate(self, username, password):
        return self.repos.users.authenticate(username, password)

    def user(self, user_id):
        return self.repos.users.get(user_id)

    # ----------------------------------------------------- workflow: rooms
    def recommend_resources(self, user, **criteria):
        return self.recommendations.recommend(user, **criteria)

    def book_resource(self, user, resource_id, start_time, end_time, attendees,
                      purpose, required_equipment=None):
        return self.bookings.create_booking(user, resource_id, start_time, end_time,
                                            attendees, purpose, required_equipment)

    def recommend_and_book(self, user, criteria, purpose):
        """Convenience workflow: take the top recommendation and reserve it."""
        result = self.recommend_resources(user, **criteria)
        if not result["recommendations"]:
            return {"result": result, "booking": None}
        best = result["recommendations"][0]
        booking = self.book_resource(
            user, best["id"], criteria.get("start_time"), criteria.get("end_time"),
            criteria.get("attendees", 1), purpose,
            criteria.get("required_equipment"))
        return {"result": result, "booking": booking}

    # -------------------------------------------------- workflow: requests
    def submit_service_request(self, user, resource_id, title, description,
                               category=None, priority=None):
        return self.maintenance.submit_request(user, resource_id, title, description,
                                               category, priority)

    def advance_request(self, user, request_id, new_status, note=None):
        return self.maintenance.update_status(user, request_id, new_status, note)

    def assign_request(self, admin, request_id, staff_id):
        return self.maintenance.assign_request(admin, request_id, staff_id)

    # ------------------------------------------------------ workflow: IoT
    def ingest_reading(self, device_id, metric, value, recorded_at=None):
        return self.iot.record_reading(device_id, metric, value, recorded_at)

    # -------------------------------------------------------- dashboards
    def dashboard_for(self, user):
        """Compose the dashboard payload for any role (polymorphic sections)."""
        builder = {
            "STUDENT": self._student_dashboard,
            "FACULTY": self._faculty_dashboard,
            "ADMIN": self._admin_dashboard,
            "SECURITY": self._security_dashboard,
            "MAINTENANCE": self._maintenance_dashboard,
        }[user.role]
        data = builder(user)
        data.update({
            "role": user.role,
            "sections": user.dashboard_sections(),
            "user": user.to_dict(),
            "unread_notifications": self.repos.notifications.unread_count(user.id),
            "notifications": [n.to_dict() for n in
                              self.repos.notifications.for_user(user.id, limit=6)],
            "generated_at": to_db(now()),
        })
        return data

    # ------------------------------------------------------------ builders
    def _student_dashboard(self, user):
        today = day_code()
        classes = self.repos.schedules.for_student(user.id)
        today_classes = [item.to_dict() for item in classes if item.is_today(today)]
        bookings = self.repos.bookings.list_bookings(user_id=user.id,
                                                     upcoming_from=now())
        requests = self.repos.requests.list_requests(raised_by=user.id)
        attendance = self.repos.schedules.attendance_summary(user.id)
        events = self.repos.events.list_events(upcoming_only=True, user_id=user.id,
                                               limit=4)
        return {
            "metrics": [
                {"label": "Classes today", "value": len(today_classes),
                 "hint": "%d enrolled courses" % len(classes), "tone": "primary"},
                {"label": "Attendance", "value": "%.0f%%" % attendance["percentage"],
                 "hint": "%d of %d sessions" % (attendance["present"], attendance["sessions"]),
                 "tone": "success" if attendance["percentage"] >= 75 else "warning"},
                {"label": "Upcoming bookings", "value": len(bookings),
                 "hint": "Confirmed and pending", "tone": "info"},
                {"label": "Open requests", "value": len([r for r in requests if r.is_open()]),
                 "hint": "%d raised in total" % len(requests), "tone": "warning"},
            ],
            "today_classes": today_classes,
            "week_classes": [item.to_dict() for item in classes],
            "bookings": [item.to_dict() for item in bookings],
            "requests": [item.to_dict() for item in requests[:5]],
            "events": [item.to_dict() for item in events],
            "digital_services": self.repos.digital_services.list_services(),
            "attendance": attendance,
        }

    def _faculty_dashboard(self, user):
        today = day_code()
        classes = self.repos.schedules.for_faculty(user.id)
        today_classes = [item.to_dict() for item in classes if item.is_today(today)]
        bookings = self.repos.bookings.list_bookings(user_id=user.id, upcoming_from=now())
        requests = self.repos.requests.list_requests(raised_by=user.id)
        students = sum(item.enrolled for item in classes)
        return {
            "metrics": [
                {"label": "Classes today", "value": len(today_classes),
                 "hint": "%d weekly sessions" % len(classes), "tone": "primary"},
                {"label": "Students taught", "value": students,
                 "hint": "Across all enrolled courses", "tone": "info"},
                {"label": "Upcoming bookings", "value": len(bookings),
                 "hint": "Rooms reserved by you", "tone": "success"},
                {"label": "Open reports", "value": len([r for r in requests if r.is_open()]),
                 "hint": "Issues you reported", "tone": "warning"},
            ],
            "today_classes": today_classes,
            "week_classes": [item.to_dict() for item in classes],
            "bookings": [item.to_dict() for item in bookings],
            "requests": [item.to_dict() for item in requests[:5]],
            "events": [item.to_dict() for item in
                       self.repos.events.list_events(upcoming_only=True, limit=4)],
        }

    def _admin_dashboard(self, user):
        analytics = self.analytics.campus_utilisation(user)
        sla = self.maintenance.sla_overview()
        pending = self.repos.bookings.list_bookings(status="PENDING")
        open_requests = self.repos.requests.list_requests(open_only=True, limit=8)
        return {
            "metrics": [
                {"label": "Campus resources", "value": sum(analytics["resource_types"].values()),
                 "hint": "%d bookable spaces" % analytics["bookable_resources"],
                 "tone": "primary"},
                {"label": "Average utilisation", "value": "%.0f%%" % analytics["average_utilisation"],
                 "hint": "Classrooms %.0f%% / labs %.0f%%" % (
                     analytics["classroom_utilisation"], analytics["laboratory_utilisation"]),
                 "tone": "info"},
                {"label": "Pending approvals", "value": len(pending),
                 "hint": "Bookings awaiting review", "tone": "warning"},
                {"label": "Open requests", "value": sla["total_open"],
                 "hint": "%d breaching SLA" % sla["breached"],
                 "tone": "danger" if sla["breached"] else "success"},
            ],
            "analytics": analytics,
            "sla": sla,
            "pending_bookings": [item.to_dict() for item in pending],
            "open_requests": [item.to_dict() for item in open_requests],
            "recent_bookings": [item.to_dict() for item in
                                self.repos.bookings.list_bookings(limit=6)],
            "events": [item.to_dict() for item in
                       self.repos.events.list_events(upcoming_only=True, limit=5)],
            "users": [item.to_dict() for item in self.repos.users.list_users()],
            "alerts": self.repos.alerts.list_alerts(status=["OPEN", "ACKNOWLEDGED"], limit=6),
            "technicians": [item.to_dict() for item in self.repos.users.maintenance_staff()],
        }

    def _security_dashboard(self, user):
        parking = self.iot.parking_overview(user)
        alerts = self.repos.alerts.list_alerts(status=["OPEN", "ACKNOWLEDGED"])
        readings = self.repos.iot.latest_per_device()
        critical = [r for r in readings if r.severity == "CRITICAL"]
        return {
            "metrics": [
                {"label": "Parking occupancy", "value": "%.0f%%" % parking["occupancy_rate"],
                 "hint": "%d of %d slots used" % (parking["occupied_slots"],
                                                  parking["total_slots"]),
                 "tone": "warning" if parking["occupancy_rate"] > 85 else "success"},
                {"label": "Free slots", "value": parking["free_slots"],
                 "hint": "%d parking zones" % len(parking["areas"]), "tone": "info"},
                {"label": "Open alerts", "value": len([a for a in alerts if a["status"] == "OPEN"]),
                 "hint": "%d acknowledged" % len([a for a in alerts
                                                  if a["status"] == "ACKNOWLEDGED"]),
                 "tone": "danger" if any(a["status"] == "OPEN" for a in alerts) else "success"},
                {"label": "Critical readings", "value": len(critical),
                 "hint": "Latest value per device", "tone": "danger" if critical else "success"},
            ],
            "parking": parking,
            "alerts": alerts,
            "readings": [item.to_dict() for item in readings],
            "critical_readings": [item.to_dict() for item in critical],
        }

    def _maintenance_dashboard(self, user):
        queue = self.repos.requests.list_requests(assigned_to=user.id)
        open_queue = [item for item in queue if item.is_open()]
        reference = now()
        breached = [item for item in open_queue if item.sla_state(reference) == "BREACHED"]
        in_progress = [item for item in open_queue if item.status == "IN_PROGRESS"]
        resolved = [item for item in queue if item.status in ("RESOLVED", "CLOSED")]
        return {
            "metrics": [
                {"label": "Assigned to me", "value": len(open_queue),
                 "hint": "%d ticket(s) in total" % len(queue), "tone": "primary"},
                {"label": "In progress", "value": len(in_progress),
                 "hint": "Currently being worked on", "tone": "info"},
                {"label": "SLA breached", "value": len(breached),
                 "hint": "Past the promised resolution time",
                 "tone": "danger" if breached else "success"},
                {"label": "Completed", "value": len(resolved),
                 "hint": "Resolved or closed by you", "tone": "success"},
            ],
            "queue": [item.to_dict(reference) for item in queue],
            "open_queue": [item.to_dict(reference) for item in open_queue],
            "critical_readings": [item.to_dict() for item in
                                  self.repos.iot.list_readings(severity="CRITICAL", limit=6)],
        }

    # ------------------------------------------------------------- guards
    @staticmethod
    def require_permission(user, permission):
        if user is None or not user.has_permission(permission):
            raise PermissionDeniedError(
                "This action requires the %s permission." % permission)
        return True

    #: Re-exported so the routes can reference permissions through the facade.
    Permission = Permission
