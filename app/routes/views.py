"""HTML page routes. Every page is rendered from live database state."""

from datetime import timedelta

from flask import Blueprint, redirect, render_template, request, url_for

from ..domain.iot import METRIC_LABELS, METRICS
from ..domain.resources import RESOURCE_LABELS
from ..domain.service_request import PRIORITIES, REQUEST_STATUSES
from ..domain.users import Permission, ROLE_LABELS
from ..patterns.strategy import available_strategies
from ..security import current_user, get_facade, login_required, permission_required
from ..utils import day_code, now

bp = Blueprint("views", __name__)


@bp.route("/")
def index():
    if current_user() is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for("views.dashboard"))


@bp.route("/dashboard")
@login_required
def dashboard():
    facade = get_facade()
    user = current_user()
    data = facade.dashboard_for(user)
    template = {
        "STUDENT": "dashboards/student.html",
        "FACULTY": "dashboards/faculty.html",
        "ADMIN": "dashboards/admin.html",
        "SECURITY": "dashboards/security.html",
        "MAINTENANCE": "dashboards/maintenance.html",
    }[user.role]
    return render_template(template, data=data, today=day_code(), now=now())


@bp.route("/schedule")
@permission_required(Permission.VIEW_SCHEDULE)
def schedule():
    facade = get_facade()
    user = current_user()
    if user.role == "FACULTY":
        classes = facade.repos.schedules.for_faculty(user.id)
    elif user.role == "STUDENT":
        classes = facade.repos.schedules.for_student(user.id)
    else:
        classes = facade.repos.schedules.all_schedules()
    selected_id = request.args.get("schedule_id", type=int)
    session_date = request.args.get("session_date") or now().strftime("%Y-%m-%d")
    roster = []
    attendance = []
    selected = None
    if selected_id:
        selected = facade.repos.schedules.get(selected_id)
        roster = facade.repos.schedules.roster(selected_id)
        attendance = [item.to_dict() for item in
                      facade.repos.schedules.attendance_for_session(selected_id, session_date)]
    return render_template(
        "schedule.html", classes=[item.to_dict() for item in classes],
        today=day_code(), selected=selected.to_dict() if selected else None,
        roster=roster, attendance=attendance, session_date=session_date,
        attendance_summary=(facade.repos.schedules.attendance_summary(user.id)
                            if user.role == "STUDENT" else None))


@bp.route("/facilities")
@permission_required(Permission.SEARCH_RESOURCES)
def facilities():
    facade = get_facade()
    query = request.args.get("q", "").strip()
    resource_type = request.args.get("type") or None
    capacity = request.args.get("capacity", type=int)
    building = request.args.get("building") or None
    resources = facade.repos.resources.list_resources(
        resource_type=resource_type, search=query or None, min_capacity=capacity,
        building=building)
    return render_template(
        "facilities.html", resources=[item.to_dict() for item in resources],
        query=query, resource_type=resource_type, capacity=capacity,
        building=building, buildings=[b.to_dict() for b in facade.repos.resources.buildings()],
        resource_labels=RESOURCE_LABELS)


@bp.route("/recommendations")
@permission_required(Permission.VIEW_RECOMMENDATIONS)
def recommendations():
    facade = get_facade()
    default_start = now().replace(minute=0, second=0) + timedelta(hours=1)
    default_end = default_start + timedelta(hours=1)
    return render_template(
        "recommendations.html",
        equipment=facade.repos.resources.equipment_catalog(),
        buildings=[b.to_dict() for b in facade.repos.resources.buildings()],
        strategies=available_strategies(),
        default_start=default_start.strftime("%Y-%m-%dT%H:%M"),
        default_end=default_end.strftime("%Y-%m-%dT%H:%M"))


@bp.route("/bookings")
@permission_required(Permission.BOOK_RESOURCE)
def bookings():
    facade = get_facade()
    user = current_user()
    mine = facade.repos.bookings.list_bookings(user_id=user.id)
    bookable = facade.repos.resources.list_resources(bookable_only=True)
    return render_template(
        "bookings.html", bookings=[item.to_dict() for item in mine],
        resources=[item.to_dict() for item in bookable],
        equipment=facade.repos.resources.equipment_catalog())


@bp.route("/requests")
@permission_required(Permission.TRACK_REQUEST)
def requests_page():
    facade = get_facade()
    user = current_user()
    mine = facade.repos.requests.list_requests(raised_by=user.id, with_history=True)
    resources = facade.repos.resources.list_resources()
    return render_template(
        "requests.html", requests=[item.to_dict() for item in mine],
        resources=[item.to_dict() for item in resources],
        can_submit=user.has_permission(Permission.SUBMIT_REQUEST),
        statuses=REQUEST_STATUSES, priorities=PRIORITIES)


@bp.route("/iot")
@permission_required(Permission.VIEW_IOT)
def iot():
    facade = get_facade()
    user = current_user()
    snapshot = facade.iot.monitoring_snapshot(user)
    return render_template("iot.html", snapshot=snapshot, metrics=METRICS,
                           metric_labels=METRIC_LABELS,
                           devices=snapshot["devices"],
                           can_acknowledge=user.has_permission(Permission.ACKNOWLEDGE_ALERT))


@bp.route("/events")
@permission_required(Permission.VIEW_EVENTS)
def events():
    facade = get_facade()
    user = current_user()
    upcoming = facade.repos.events.list_events(user_id=user.id)
    return render_template(
        "events.html", events=[item.to_dict() for item in upcoming],
        can_manage=user.has_permission(Permission.MANAGE_EVENTS),
        venues=[item.to_dict() for item in
                facade.repos.resources.list_resources(bookable_only=True)])


@bp.route("/maintenance")
@permission_required(Permission.UPDATE_REQUEST_STATUS)
def maintenance():
    facade = get_facade()
    user = current_user()
    if user.role == "MAINTENANCE":
        queue = facade.repos.requests.list_requests(assigned_to=user.id, with_history=True)
    else:
        queue = facade.repos.requests.list_requests(open_only=True, with_history=True)
    reference = now()
    resources = facade.repos.resources.list_resources()
    return render_template(
        "maintenance.html", queue=[item.to_dict(reference) for item in queue],
        resources=[item.to_dict() for item in resources if item.equipment_codes],
        can_update_equipment=user.has_permission(Permission.UPDATE_EQUIPMENT))


@bp.route("/security")
@permission_required(Permission.MONITOR_PARKING)
def security():
    facade = get_facade()
    user = current_user()
    return render_template("dashboards/security.html", data=facade.dashboard_for(user))


@bp.route("/admin")
@permission_required(Permission.VIEW_ANALYTICS)
def admin():
    facade = get_facade()
    user = current_user()
    data = facade.dashboard_for(user)
    return render_template(
        "admin.html", data=data, role_labels=ROLE_LABELS,
        resources=[item.to_dict() for item in facade.repos.resources.list_resources()],
        buildings=[b.to_dict() for b in facade.repos.resources.buildings()],
        all_requests=[item.to_dict() for item in
                      facade.repos.requests.list_requests(limit=30)])


@bp.route("/notifications")
@login_required
def notifications():
    facade = get_facade()
    user = current_user()
    items = facade.repos.notifications.for_user(user.id, limit=50)
    return render_template("notifications.html",
                           notifications=[item.to_dict() for item in items])
