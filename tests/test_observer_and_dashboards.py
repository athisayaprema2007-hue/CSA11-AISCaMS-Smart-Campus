"""Observer notifications, facade coordination and dashboard calculations."""

from datetime import timedelta

import pytest

from app.patterns.observer import (AuditTrailObserver, BOOKING_CREATED,
                                   IOT_CRITICAL_ALERT, Observer,
                                   REQUEST_STATUS_CHANGED, Subject)
from app.utils import now, to_db


class RecordingObserver(Observer):
    def __init__(self, interests=()):
        self.interests = interests
        self.seen = []

    def update(self, event_name, payload):
        self.seen.append(event_name)


@pytest.fixture
def window():
    start = (now() + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
    return to_db(start), to_db(start + timedelta(hours=1))


def test_subject_attaches_notifies_and_detaches():
    subject = Subject()
    observer = RecordingObserver()
    subject.attach(observer)
    subject.attach(observer)  # attaching twice must not duplicate
    assert len(subject.observers) == 1
    subject.notify("ANY_EVENT", {})
    subject.detach(observer)
    subject.notify("ANY_EVENT", {})
    assert observer.seen == ["ANY_EVENT"]


def test_observers_only_receive_the_events_they_care_about():
    subject = Subject()
    picky = RecordingObserver(interests=(BOOKING_CREATED,))
    subject.attach(picky)
    subject.notify(BOOKING_CREATED, {})
    subject.notify(REQUEST_STATUS_CHANGED, {})
    assert picky.seen == [BOOKING_CREATED]


def test_subject_rejects_non_observers():
    with pytest.raises(TypeError):
        Subject().attach(object())


def test_booking_creates_a_notification_for_the_owner(facade, users, resources, window):
    student = users["athisaya"]
    before = facade.repos.notifications.unread_count(student.id)
    booking = facade.book_resource(student, resources["CR-201"].id, window[0], window[1],
                                   8, "Team meeting")
    after = facade.repos.notifications.for_user(student.id, unread_only=True)
    assert facade.repos.notifications.unread_count(student.id) == before + 1
    assert booking.reference in after[0].message
    assert after[0].category == "BOOKING"


def test_pending_booking_notifies_the_administrator(facade, users, resources, window):
    admin = users["campus.admin"]
    before = facade.repos.notifications.unread_count(admin.id)
    facade.book_resource(users["athisaya"], resources["LB-CS1"].id, window[0], window[1],
                         20, "Laboratory practice")
    assert facade.repos.notifications.unread_count(admin.id) == before + 1


def test_status_change_notifies_the_reporter(facade, users, resources):
    student = users["athisaya"]
    request = facade.submit_service_request(student, resources["CR-201"].id,
                                            "Socket not working",
                                            "The power socket near the door is dead.")
    facade.assign_request(users["campus.admin"], request.id, users["tech.mohan"].id)
    before = facade.repos.notifications.unread_count(student.id)
    facade.advance_request(users["tech.mohan"], request.id, "IN_PROGRESS")
    messages = facade.repos.notifications.for_user(student.id, unread_only=True)
    assert facade.repos.notifications.unread_count(student.id) == before + 1
    assert request.ticket in messages[0].message


def test_critical_reading_notifies_security_and_raises_an_alert(facade, users, resources):
    officer = users["security.ravi"]
    before = facade.repos.notifications.unread_count(officer.id)
    alerts_before = len(facade.repos.alerts.list_alerts())
    facade.ingest_reading(resources["IOT-AIR-101"].id, "AIR_QUALITY", 300.0)
    assert facade.repos.notifications.unread_count(officer.id) == before + 1
    assert len(facade.repos.alerts.list_alerts()) == alerts_before + 1


def test_audit_trail_observer_records_the_workflow(facade, users, resources, window):
    facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, window[0],
                         window[1], 30, "Audit trail check")
    entries = facade.audit_observer.events_of(BOOKING_CREATED)
    assert entries and entries[-1]["entity_type"] == "BOOKING"


def test_audit_trail_observer_limits_its_buffer():
    observer = AuditTrailObserver(limit=3)
    for index in range(5):
        observer.update("EVENT", {"entity_id": index})
    assert len(observer.entries) == 3
    assert observer.entries[0]["entity_id"] == 2


def test_iot_alert_event_carries_the_reading(facade, resources):
    recorder = RecordingObserver(interests=(IOT_CRITICAL_ALERT,))
    facade.bus.attach(recorder)
    facade.ingest_reading(resources["IOT-CLI-CS1"].id, "TEMPERATURE", 41.0)
    assert recorder.seen == [IOT_CRITICAL_ALERT]


# ------------------------------------------------------------- dashboards
def test_student_dashboard_metrics(facade, users):
    data = facade.dashboard_for(users["athisaya"])
    labels = [metric["label"] for metric in data["metrics"]]
    assert labels == ["Classes today", "Attendance", "Upcoming bookings", "Open requests"]
    assert data["role"] == "STUDENT"
    assert data["attendance"]["sessions"] > 0
    assert isinstance(data["digital_services"], list) and data["digital_services"]


def test_faculty_dashboard_counts_students(facade, users):
    data = facade.dashboard_for(users["dr.kavitha"])
    students = [metric for metric in data["metrics"] if metric["label"] == "Students taught"]
    assert students and students[0]["value"] > 0
    assert data["week_classes"]


def test_admin_dashboard_reports_operational_metrics(facade, users):
    data = facade.dashboard_for(users["campus.admin"])
    analytics = data["analytics"]
    assert analytics["resource_types"]["CLASSROOM"] == 8
    assert analytics["resource_types"]["LABORATORY"] == 4
    assert analytics["open_requests"] == data["sla"]["total_open"]
    assert analytics["user_counts"]["STUDENT"] == 4
    assert data["technicians"]


def test_security_dashboard_reports_parking_and_alerts(facade, users):
    data = facade.dashboard_for(users["security.ravi"])
    assert data["parking"]["total_slots"] == 220
    assert "alerts" in data
    labels = [metric["label"] for metric in data["metrics"]]
    assert "Parking occupancy" in labels


def test_maintenance_dashboard_shows_the_personal_queue(facade, users):
    data = facade.dashboard_for(users["tech.mohan"])
    assert all(item["assigned_to"] == users["tech.mohan"].id for item in data["queue"])
    labels = [metric["label"] for metric in data["metrics"]]
    assert labels[0] == "Assigned to me"


def test_sla_overview_totals_match_the_open_requests(facade):
    overview = facade.maintenance.sla_overview()
    assert overview["total_open"] == (overview["on_track"] + overview["at_risk"]
                                      + overview["breached"])


def test_facade_wires_every_observer(facade):
    assert len(facade.bus.observers) == 3
    assert facade.notification_observer in facade.bus.observers
    assert facade.alert_observer in facade.bus.observers
    assert facade.audit_observer in facade.bus.observers


def test_recommend_and_book_is_a_single_workflow(facade, users, window):
    outcome = facade.recommend_and_book(
        users["dr.kavitha"],
        {"attendees": 30, "required_equipment": ["PROJECTOR"],
         "start_time": window[0], "end_time": window[1]},
        "Combined workflow check")
    assert outcome["booking"] is not None
    assert outcome["booking"].status == "CONFIRMED"
    assert outcome["result"]["recommendations"][0]["id"] == outcome["booking"].resource_id
