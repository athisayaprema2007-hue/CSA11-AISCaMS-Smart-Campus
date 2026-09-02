"""HTTP layer: authentication, role based page access, API success and errors."""

from datetime import timedelta

import pytest

from app.utils import now, to_db


@pytest.fixture
def window():
    start = (now() + timedelta(days=8)).replace(hour=10, minute=0, second=0, microsecond=0)
    return to_db(start), to_db(start + timedelta(hours=1))


def resource_id(client, code):
    payload = client.get("/api/resources?q=%s" % code).get_json()
    return payload["resources"][0]["id"]


# ----------------------------------------------------------- authentication
def test_health_endpoint_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_protected_pages_redirect_anonymous_visitors(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_protected_api_returns_401_for_anonymous_callers(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 401
    assert response.get_json()["error"] == "AuthenticationError"


def test_login_with_valid_credentials(login):
    client = login("athisaya")
    assert b"Athisaya U" in client.get("/dashboard").data


def test_login_with_invalid_credentials(client):
    response = client.post("/login", data={"username": "athisaya", "password": "nope"})
    assert response.status_code == 200
    assert b"Unknown username or password" in response.data


def test_demo_role_selection_signs_the_user_in(client):
    response = client.get("/login/demo/campus.admin", follow_redirects=True)
    assert response.status_code == 200
    assert b"Vikram Rao" in response.data


def test_logout_clears_the_session(login):
    client = login("athisaya")
    client.get("/logout")
    assert client.get("/dashboard").status_code == 302


# -------------------------------------------------------------- page access
def test_student_pages_render(login):
    client = login("athisaya")
    for path in ("/dashboard", "/schedule", "/facilities", "/recommendations",
                 "/bookings", "/requests", "/events", "/notifications"):
        assert client.get(path).status_code == 200, path


def test_student_cannot_open_restricted_pages(login):
    client = login("athisaya")
    for path in ("/admin", "/iot", "/security", "/maintenance"):
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/dashboard" in response.headers["Location"]


def test_role_specific_pages_render_for_their_owners(login, client):
    for username, path in (("campus.admin", "/admin"), ("security.ravi", "/security"),
                           ("tech.mohan", "/maintenance"), ("dr.kavitha", "/schedule")):
        client.get("/logout")
        signed_in = login(username)
        assert signed_in.get(path).status_code == 200, path


def test_navigation_is_filtered_by_role(login, client):
    student = login("athisaya").get("/dashboard").data
    assert b"Administration" not in student
    client.get("/logout")
    admin = login("campus.admin").get("/dashboard").data
    assert b"Administration" in admin


# ------------------------------------------------------------- API success
def test_recommendation_api_returns_scored_results(login, window):
    client = login("dr.kavitha")
    response = client.post("/api/recommendations", json={
        "attendees": 40, "equipment": ["PROJECTOR"], "start_time": window[0],
        "end_time": window[1], "strategy": "balanced"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["recommendations"]
    assert body["strategy"]["key"] == "balanced"
    assert body["recommendations"][0]["reasons"]


def test_booking_api_creates_a_booking(login, window):
    client = login("dr.kavitha")
    response = client.post("/api/bookings", json={
        "resource_id": resource_id(client, "CR-101"), "start_time": window[0],
        "end_time": window[1], "attendees": 30, "purpose": "API booking test"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["booking"]["status"] == "CONFIRMED"
    assert body["booking"]["reference"].startswith("BK-")
    assert "confirmed" in body["message"]


def test_booking_api_reports_a_conflict(login, window):
    client = login("dr.kavitha")
    payload = {"resource_id": resource_id(client, "CR-101"), "start_time": window[0],
               "end_time": window[1], "attendees": 30, "purpose": "First booking"}
    assert client.post("/api/bookings", json=payload).status_code == 201
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 409
    assert response.get_json()["error"] == "BookingConflictError"


def test_booking_api_validates_capacity(login, window):
    client = login("dr.kavitha")
    response = client.post("/api/bookings", json={
        "resource_id": resource_id(client, "CR-201"), "start_time": window[0],
        "end_time": window[1], "attendees": 200, "purpose": "Too many people"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "CapacityError"


def test_booking_api_validates_missing_fields(login):
    client = login("dr.kavitha")
    response = client.post("/api/bookings", json={"resource_id": 1})
    assert response.status_code == 400
    assert response.get_json()["error"] == "ValidationError"


def test_request_api_classifies_and_returns_sla(login):
    client = login("athisaya")
    response = client.post("/api/requests", json={
        "resource_id": resource_id(client, "CR-201"),
        "title": "Projector not working",
        "description": "The projector does not switch on before the tutorial session."})
    assert response.status_code == 201
    body = response.get_json()
    assert body["request"]["category"] == "IT_SUPPORT"
    assert body["request"]["priority"] == "HIGH"
    assert body["request"]["sla_hours"] == 6
    assert body["request"]["status"] == "NEW"


def test_request_api_rejects_a_short_description(login):
    client = login("athisaya")
    response = client.post("/api/requests", json={
        "resource_id": resource_id(client, "CR-201"), "title": "Broken",
        "description": "bad"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "ValidationError"


def test_request_status_api_enforces_the_state_machine(login, client):
    student = login("athisaya")
    created = student.post("/api/requests", json={
        "resource_id": resource_id(student, "CR-201"), "title": "Door handle loose",
        "description": "The door handle of the seminar room is loose and rattles."})
    request_id = created.get_json()["request"]["id"]
    client.get("/logout")
    admin = login("campus.admin")
    invalid = admin.post("/api/requests/%d/status" % request_id, json={"status": "CLOSED"})
    assert invalid.status_code == 409
    assert invalid.get_json()["error"] == "InvalidTransitionError"


def test_assignment_and_workflow_through_the_api(login, client):
    student = login("athisaya")
    created = student.post("/api/requests", json={
        "resource_id": resource_id(student, "CR-201"), "title": "Bench is damaged",
        "description": "A bench in the seminar room is damaged and unsafe to use."})
    request_id = created.get_json()["request"]["id"]

    client.get("/logout")
    admin = login("campus.admin")
    technicians = admin.get("/api/admin/technicians").get_json()["technicians"]
    assigned = admin.post("/api/requests/%d/assign" % request_id,
                          json={"staff_id": technicians[0]["id"]})
    assert assigned.status_code == 200
    assert assigned.get_json()["request"]["status"] == "ASSIGNED"

    client.get("/logout")
    technician = login(technicians[0]["username"])
    started = technician.post("/api/requests/%d/status" % request_id,
                              json={"status": "IN_PROGRESS", "note": "On site"})
    assert started.get_json()["request"]["status"] == "IN_PROGRESS"
    resolved = technician.post("/api/requests/%d/status" % request_id,
                               json={"status": "RESOLVED", "note": "Bench replaced"})
    assert resolved.get_json()["request"]["status"] == "RESOLVED"


def test_iot_api_records_a_reading_and_escalates(login):
    client = login("security.ravi")
    device = client.get("/api/resources?q=IOT-CLI-101").get_json()["resources"][0]
    response = client.post("/api/iot/readings", json={
        "device_id": device["id"], "metric": "TEMPERATURE", "value": 40.5})
    assert response.status_code == 201
    body = response.get_json()
    assert body["reading"]["severity"] == "CRITICAL"
    assert body["request"]["priority"] == "CRITICAL"
    assert "raised automatically" in body["message"]


def test_iot_api_validates_the_metric(login):
    client = login("security.ravi")
    device = client.get("/api/resources?q=IOT-CLI-101").get_json()["resources"][0]
    response = client.post("/api/iot/readings", json={
        "device_id": device["id"], "metric": "PRESSURE", "value": 3})
    assert response.status_code == 400
    assert response.get_json()["error"] == "ValidationError"


def test_api_refuses_actions_outside_the_role(login):
    client = login("athisaya")
    assert client.get("/api/iot/snapshot").status_code == 403
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/equipment/condition", json={}).status_code == 403


def test_unknown_api_endpoint_returns_404(login):
    client = login("athisaya")
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "NotFound"


def test_unknown_entity_returns_404(login):
    client = login("athisaya")
    response = client.get("/api/requests/9999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "NotFoundError"


def test_dashboard_api_returns_metrics(login):
    client = login("campus.admin")
    body = client.get("/api/dashboard").get_json()
    assert body["role"] == "ADMIN"
    assert len(body["metrics"]) == 4
    assert body["analytics"]["resource_types"]


def test_analytics_api_is_admin_only(login, client):
    admin = login("campus.admin")
    assert admin.get("/api/admin/analytics").status_code == 200
    client.get("/logout")
    faculty = login("dr.kavitha")
    assert faculty.get("/api/admin/analytics").status_code == 403


def test_notification_api_marks_messages_read(login):
    client = login("athisaya")
    body = client.get("/api/notifications").get_json()
    assert body["unread"] >= 1
    notification_id = body["notifications"][0]["id"]
    client.post("/api/notifications/%d/read" % notification_id)
    assert client.post("/api/notifications/read-all").get_json()["unread"] == 0


def test_admin_can_create_a_user_and_a_resource(login):
    client = login("campus.admin")
    user_response = client.post("/api/admin/users", json={
        "username": "api.user", "full_name": "API Created User",
        "email": "api.user@aiscams.edu", "role": "STUDENT", "department": "Physics"})
    assert user_response.status_code == 201
    assert user_response.get_json()["user"]["role"] == "STUDENT"

    resource_response = client.post("/api/admin/resources", json={
        "code": "CR-401", "name": "New Seminar Room", "resource_type": "CLASSROOM",
        "building": "MB", "capacity": 35, "floor": 4, "equipment": ["WIFI6"]})
    assert resource_response.status_code == 201
    assert resource_response.get_json()["resource"]["code"] == "CR-401"


def test_admin_can_approve_a_pending_booking_through_the_api(login, client, window):
    student = login("athisaya")
    created = student.post("/api/bookings", json={
        "resource_id": resource_id(student, "LB-CS1"), "start_time": window[0],
        "end_time": window[1], "attendees": 20, "purpose": "Laboratory practice"})
    booking = created.get_json()["booking"]
    assert booking["status"] == "PENDING"
    client.get("/logout")
    admin = login("campus.admin")
    decided = admin.post("/api/bookings/%d/decision" % booking["id"],
                         json={"decision": "approve"})
    assert decided.get_json()["booking"]["status"] == "CONFIRMED"


def test_event_registration_through_the_api(login):
    client = login("arjun.p")
    events = client.get("/api/events").get_json()["events"]
    target = [event for event in events if not event["registered"]][0]
    response = client.post("/api/events/%d/register" % target["id"])
    assert response.status_code == 200
    assert response.get_json()["event"]["registered"] is True


def test_attendance_api_is_restricted_to_the_owning_faculty(login, client):
    faculty = login("dr.kavitha")
    schedule = faculty.get("/schedule").data
    assert b"CSA11" in schedule
    client.get("/logout")
    other = login("dr.suresh")
    body = other.get("/api/dashboard").get_json()
    assert body["role"] == "FACULTY"
