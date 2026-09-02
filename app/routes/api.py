"""JSON API used by the browser interface and by the external IoT gateway."""

from flask import Blueprint, jsonify, request

from ..domain.users import Permission
from ..exceptions import NotFoundError, ValidationError
from ..patterns.strategy import available_strategies
from ..security import (current_user, get_facade, login_required,
                        permission_required, roles_required)
from ..utils import now, require_int, require_text

bp = Blueprint("api", __name__, url_prefix="/api")


def payload():
    """Accept both JSON bodies and classic form posts."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict(flat=True)
    return data or {}


def listify(data, key):
    if hasattr(data, "getlist"):
        values = data.getlist(key)
        if values:
            return values
    value = data.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


# ------------------------------------------------------------------ system
@bp.get("/health")
def health():
    facade = get_facade()
    return jsonify({
        "status": "ok",
        "time": now().isoformat(timespec="seconds"),
        "resources": sum(facade.repos.resources.type_counts().values()),
        "users": sum(facade.repos.users.role_counts().values()),
    })


@bp.get("/strategies")
@login_required
def strategies():
    return jsonify({"strategies": available_strategies()})


@bp.get("/dashboard")
@login_required
def dashboard():
    return jsonify(get_facade().dashboard_for(current_user()))


# ----------------------------------------------------------------- search
@bp.get("/resources")
@permission_required(Permission.SEARCH_RESOURCES)
def resources():
    facade = get_facade()
    items = facade.repos.resources.list_resources(
        resource_type=request.args.get("type") or None,
        status=request.args.get("status") or None,
        search=request.args.get("q") or None,
        min_capacity=request.args.get("capacity", type=int),
        building=request.args.get("building") or None,
        equipment=listify(request.args, "equipment"),
        bookable_only=request.args.get("bookable") == "1")
    return jsonify({"count": len(items), "resources": [item.to_dict() for item in items]})


@bp.get("/resources/<int:resource_id>")
@permission_required(Permission.SEARCH_RESOURCES)
def resource_detail(resource_id):
    facade = get_facade()
    resource = facade.repos.resources.require_resource(resource_id)
    data = resource.to_dict()
    data["bookings"] = [item.to_dict() for item in
                        facade.bookings.calendar_for_resource(resource_id)]
    data["requests"] = [item.to_dict() for item in
                        facade.repos.requests.list_requests(resource_id=resource_id)]
    return jsonify(data)


# -------------------------------------------------------- recommendations
@bp.post("/recommendations")
@permission_required(Permission.VIEW_RECOMMENDATIONS)
def recommend():
    data = payload()
    result = get_facade().recommend_resources(
        current_user(),
        attendees=require_int(data.get("attendees", 1), "attendees", minimum=1,
                              maximum=1000),
        required_equipment=listify(data, "equipment"),
        preferred_building=data.get("building") or None,
        start_time=data.get("start_time") or None,
        end_time=data.get("end_time") or None,
        resource_type=(data.get("resource_type") or "CLASSROOM").upper(),
        strategy_key=data.get("strategy"),
        limit=int(data.get("limit", 5)))
    return jsonify(result)


# --------------------------------------------------------------- bookings
@bp.get("/bookings")
@permission_required(Permission.BOOK_RESOURCE)
def list_bookings():
    facade = get_facade()
    user = current_user()
    scope = request.args.get("scope", "mine")
    if scope == "all" and user.has_permission(Permission.APPROVE_BOOKING):
        items = facade.repos.bookings.list_bookings(status=request.args.get("status") or None)
    else:
        items = facade.repos.bookings.list_bookings(user_id=user.id)
    return jsonify({"count": len(items), "bookings": [item.to_dict() for item in items]})


@bp.post("/bookings")
@permission_required(Permission.BOOK_RESOURCE)
def create_booking():
    data = payload()
    booking = get_facade().book_resource(
        current_user(),
        resource_id=require_int(data.get("resource_id"), "resource", minimum=1),
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        attendees=require_int(data.get("attendees", 1), "attendees", minimum=1,
                              maximum=1000),
        purpose=require_text(data.get("purpose"), "purpose", minimum=3, maximum=200),
        required_equipment=listify(data, "equipment"))
    return jsonify({"message": "Booking %s %s." % (
        booking.reference,
        "created and awaiting approval" if booking.status == "PENDING" else "confirmed"),
        "booking": booking.to_dict()}), 201


@bp.post("/bookings/<int:booking_id>/cancel")
@permission_required(Permission.BOOK_RESOURCE)
def cancel_booking(booking_id):
    booking = get_facade().bookings.cancel_booking(current_user(), booking_id)
    return jsonify({"message": "Booking %s cancelled." % booking.reference,
                    "booking": booking.to_dict()})


@bp.post("/bookings/<int:booking_id>/decision")
@permission_required(Permission.APPROVE_BOOKING)
def decide_booking(booking_id):
    approve = str(payload().get("decision", "approve")).lower() != "reject"
    booking = get_facade().bookings.approve_booking(current_user(), booking_id, approve)
    return jsonify({"message": "Booking %s %s." % (booking.reference, booking.status.lower()),
                    "booking": booking.to_dict()})


# -------------------------------------------------------- service requests
@bp.get("/requests")
@permission_required(Permission.TRACK_REQUEST)
def list_requests():
    facade = get_facade()
    user = current_user()
    scope = request.args.get("scope", "mine")
    if scope == "assigned":
        items = facade.repos.requests.list_requests(assigned_to=user.id)
    elif scope == "all" and user.has_permission(Permission.ASSIGN_REQUEST):
        items = facade.repos.requests.list_requests(status=request.args.get("status") or None)
    else:
        items = facade.repos.requests.list_requests(raised_by=user.id)
    return jsonify({"count": len(items), "requests": [item.to_dict() for item in items]})


@bp.get("/requests/<int:request_id>")
@permission_required(Permission.TRACK_REQUEST)
def request_detail(request_id):
    item = get_facade().repos.requests.require_request(request_id)
    return jsonify(item.to_dict())


@bp.post("/requests")
@permission_required(Permission.SUBMIT_REQUEST)
def create_request():
    data = payload()
    item = get_facade().submit_service_request(
        current_user(),
        resource_id=require_int(data.get("resource_id"), "resource", minimum=1),
        title=data.get("title"),
        description=data.get("description"),
        category=data.get("category") or None,
        priority=data.get("priority") or None)
    return jsonify({
        "message": "Request %s created and classified as %s / %s (SLA %d hours)."
                   % (item.ticket, item.category_label, item.priority, item.sla_hours),
        "request": item.to_dict()}), 201


@bp.post("/requests/<int:request_id>/status")
@permission_required(Permission.UPDATE_REQUEST_STATUS)
def update_request_status(request_id):
    data = payload()
    item = get_facade().advance_request(current_user(), request_id,
                                        data.get("status"), data.get("note"))
    return jsonify({"message": "Request %s is now %s." % (item.ticket, item.status),
                    "request": item.to_dict()})


@bp.post("/requests/<int:request_id>/assign")
@permission_required(Permission.ASSIGN_REQUEST)
def assign_request(request_id):
    data = payload()
    item = get_facade().assign_request(
        current_user(), request_id,
        require_int(data.get("staff_id"), "technician", minimum=1))
    return jsonify({"message": "Request %s assigned to %s." % (item.ticket,
                                                               item.assigned_to_name),
                    "request": item.to_dict()})


@bp.post("/equipment/condition")
@permission_required(Permission.UPDATE_EQUIPMENT)
def update_equipment():
    data = payload()
    resource = get_facade().maintenance.update_equipment_condition(
        current_user(),
        require_int(data.get("resource_id"), "resource", minimum=1),
        require_text(data.get("equipment_code"), "equipment code", minimum=2, maximum=40),
        data.get("condition"))
    return jsonify({"message": "%s equipment updated." % resource.code,
                    "resource": resource.to_dict()})


# -------------------------------------------------------------------- IoT
@bp.get("/iot/snapshot")
@permission_required(Permission.VIEW_IOT)
def iot_snapshot():
    return jsonify(get_facade().iot.monitoring_snapshot(current_user()))


@bp.get("/iot/readings")
@permission_required(Permission.VIEW_IOT)
def iot_readings():
    items = get_facade().repos.iot.list_readings(
        metric=request.args.get("metric") or None,
        severity=request.args.get("severity") or None,
        limit=int(request.args.get("limit", 40)))
    return jsonify({"count": len(items), "readings": [item.to_dict() for item in items]})


@bp.post("/iot/readings")
@permission_required(Permission.VIEW_IOT)
def ingest_reading():
    """Entry point of the IoT gateway (external system actor)."""
    data = payload()
    result = get_facade().ingest_reading(
        device_id=require_int(data.get("device_id"), "device", minimum=1),
        metric=data.get("metric"),
        value=data.get("value"),
        recorded_at=data.get("recorded_at") or None)
    reading = result["reading"]
    response = {
        "reading": reading.to_dict(),
        "alert": result["alert"],
        "request": result["request"].to_dict() if result["request"] else None,
        "duplicate_suppressed": result["duplicate_suppressed"],
    }
    if result["request"] is not None:
        response["message"] = (
            "%s reading recorded as %s. Ticket %s was raised automatically with %s "
            "priority." % (reading.metric_label, reading.severity,
                           result["request"].ticket, result["request"].priority))
    elif result["duplicate_suppressed"]:
        response["message"] = ("%s reading recorded as %s. An alert is already open for "
                               "this resource, so no duplicate ticket was created."
                               % (reading.metric_label, reading.severity))
    else:
        response["message"] = "%s reading recorded as %s." % (reading.metric_label,
                                                              reading.severity)
    return jsonify(response), 201


@bp.post("/alerts/<int:alert_id>/acknowledge")
@permission_required(Permission.ACKNOWLEDGE_ALERT)
def acknowledge_alert(alert_id):
    alert = get_facade().iot.acknowledge_alert(current_user(), alert_id)
    return jsonify({"message": "Alert #%d acknowledged." % alert_id, "alert": alert})


@bp.get("/parking")
@permission_required(Permission.MONITOR_PARKING)
def parking():
    return jsonify(get_facade().iot.parking_overview(current_user()))


# ----------------------------------------------------------------- events
@bp.get("/events")
@permission_required(Permission.VIEW_EVENTS)
def list_events():
    items = get_facade().repos.events.list_events(user_id=current_user().id)
    return jsonify({"count": len(items), "events": [item.to_dict() for item in items]})


@bp.post("/events/<int:event_id>/register")
@permission_required(Permission.VIEW_EVENTS)
def register_event(event_id):
    event = get_facade().repos.events.register(event_id, current_user().id)
    return jsonify({"message": "Registered for %s." % event.title,
                    "event": event.to_dict()})


@bp.post("/events")
@permission_required(Permission.MANAGE_EVENTS)
def create_event():
    data = payload()
    event = get_facade().repos.events.add(
        title=require_text(data.get("title"), "title", minimum=3, maximum=120),
        description=require_text(data.get("description"), "description", minimum=5,
                                 maximum=500),
        category=require_text(data.get("category"), "category", minimum=3, maximum=40),
        start_time=data.get("start_time"), end_time=data.get("end_time"),
        capacity=require_int(data.get("capacity", 50), "capacity", minimum=1,
                             maximum=5000),
        organiser_id=current_user().id,
        venue_id=int(data["venue_id"]) if data.get("venue_id") else None)
    return jsonify({"message": "Event '%s' published." % event.title,
                    "event": event.to_dict()}), 201


@bp.post("/events/<int:event_id>/cancel")
@permission_required(Permission.MANAGE_EVENTS)
def cancel_event(event_id):
    event = get_facade().repos.events.cancel(event_id)
    return jsonify({"message": "Event '%s' cancelled." % event.title,
                    "event": event.to_dict()})


# ------------------------------------------------------------- attendance
@bp.post("/attendance")
@permission_required(Permission.RECORD_ATTENDANCE)
def record_attendance():
    data = payload()
    facade = get_facade()
    schedule_id = require_int(data.get("schedule_id"), "class", minimum=1)
    schedule = facade.repos.schedules.require_schedule(schedule_id)
    if schedule.faculty_id != current_user().id:
        raise ValidationError("You can only record attendance for your own classes.",
                              {"field": "schedule_id"})
    records = facade.repos.schedules.record_attendance(
        schedule_id=schedule_id,
        student_id=require_int(data.get("student_id"), "student", minimum=1),
        session_date=require_text(data.get("session_date"), "session date", minimum=8,
                                  maximum=10),
        status=data.get("status"), recorded_by=current_user().id)
    return jsonify({"message": "Attendance saved for %s." % schedule.course_code,
                    "attendance": [item.to_dict() for item in records]})


# ---------------------------------------------------------- notifications
@bp.get("/notifications")
@login_required
def list_notifications():
    facade = get_facade()
    user = current_user()
    items = facade.repos.notifications.for_user(
        user.id, unread_only=request.args.get("unread") == "1", limit=50)
    return jsonify({"unread": facade.repos.notifications.unread_count(user.id),
                    "notifications": [item.to_dict() for item in items]})


@bp.post("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id):
    facade = get_facade()
    facade.repos.notifications.mark_read(notification_id, current_user().id)
    return jsonify({"message": "Notification marked as read.",
                    "unread": facade.repos.notifications.unread_count(current_user().id)})


@bp.post("/notifications/read-all")
@login_required
def read_all_notifications():
    facade = get_facade()
    facade.repos.notifications.mark_all_read(current_user().id)
    return jsonify({"message": "All notifications marked as read.", "unread": 0})


# ---------------------------------------------------------- administration
@bp.get("/admin/analytics")
@permission_required(Permission.VIEW_ANALYTICS)
def analytics():
    return jsonify(get_facade().analytics.campus_utilisation(current_user()))


@bp.get("/admin/users")
@permission_required(Permission.MANAGE_USERS)
def list_users():
    items = get_facade().repos.users.list_users()
    return jsonify({"count": len(items), "users": [item.to_dict() for item in items]})


@bp.post("/admin/users")
@permission_required(Permission.MANAGE_USERS)
def create_user():
    data = payload()
    user = get_facade().repos.users.add(
        username=data.get("username"), full_name=data.get("full_name"),
        email=data.get("email"), password=data.get("password") or "campus123",
        role=data.get("role"), department=data.get("department"),
        phone=data.get("phone"))
    return jsonify({"message": "User %s created as %s." % (user.username, user.role),
                    "user": user.to_dict()}), 201


@bp.post("/admin/users/<int:user_id>/role")
@permission_required(Permission.MANAGE_USERS)
def change_role(user_id):
    user = get_facade().repos.users.change_role(user_id, payload().get("role"))
    return jsonify({"message": "%s is now a %s." % (user.full_name, user.role),
                    "user": user.to_dict()})


@bp.post("/admin/users/<int:user_id>/active")
@permission_required(Permission.MANAGE_USERS)
def set_user_active(user_id):
    active = str(payload().get("is_active", "1")) in ("1", "true", "True", "on")
    user = get_facade().repos.users.set_active(user_id, active)
    return jsonify({"message": "%s is now %s." % (user.full_name,
                                                  "active" if active else "inactive"),
                    "user": user.to_dict()})


@bp.post("/admin/resources")
@permission_required(Permission.MANAGE_RESOURCES)
def create_resource():
    data = payload()
    equipment = {code: "GOOD" for code in listify(data, "equipment")}
    resource = get_facade().repos.resources.add_resource(
        code=data.get("code"), name=data.get("name"),
        resource_type=data.get("resource_type"), building=data.get("building"),
        capacity=require_int(data.get("capacity", 0), "capacity", minimum=0,
                             maximum=2000),
        floor=int(data.get("floor", 0) or 0), equipment=equipment,
        seating_type=data.get("seating_type", "FIXED"),
        lab_type=data.get("lab_type", "COMPUTING"),
        workstations=int(data.get("workstations", 0) or 0),
        zone=data.get("zone", "A"),
        total_slots=int(data.get("total_slots", 1) or 1),
        device_type=data.get("device_type", "OCCUPANCY_SENSOR"))
    return jsonify({"message": "Resource %s registered." % resource.code,
                    "resource": resource.to_dict()}), 201


@bp.post("/admin/resources/<int:resource_id>/status")
@permission_required(Permission.MANAGE_RESOURCES)
def update_resource_status(resource_id):
    resource = get_facade().repos.resources.update_status(resource_id,
                                                          payload().get("status"))
    return jsonify({"message": "%s marked as %s." % (resource.code, resource.status),
                    "resource": resource.to_dict()})


@bp.get("/admin/technicians")
@permission_required(Permission.ASSIGN_REQUEST)
def technicians():
    staff = get_facade().repos.users.maintenance_staff()
    return jsonify({"technicians": [member.to_dict() for member in staff]})


@bp.get("/admin/seed-summary")
@roles_required("ADMIN")
def seed_summary():
    from ..seed import summary
    return jsonify(summary(get_facade().repos.connection))
