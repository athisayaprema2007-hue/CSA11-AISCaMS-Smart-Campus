"""Service request factory, SLA rules and lifecycle state machine."""

import pytest

from app.domain.service_request import (HousekeepingRequest, ITSupportRequest,
                                        MaintenanceRequest, SafetyRequest,
                                        ServiceRequest)
from app.exceptions import (InvalidTransitionError, PermissionDeniedError,
                            ValidationError)
from app.patterns.factory import ServiceRequestFactory
from app.utils import now


def build(title, description, **kwargs):
    return ServiceRequestFactory.create(resource_id=1, title=title,
                                        description=description, **kwargs)


def test_service_request_is_abstract():
    with pytest.raises(TypeError):
        ServiceRequest(None, "SR-1", 1, "Title", "Description text")


def test_factory_classifies_safety_issues():
    request = build("Smoke in the corridor",
                    "There is smoke and a burning smell near the laboratory entrance.")
    assert isinstance(request, SafetyRequest)
    assert request.category == "SAFETY"
    assert request.handling_team() == "Campus safety and security"


def test_factory_classifies_it_issues():
    request = build("Projector problem",
                    "The projector in the seminar room does not display anything.")
    assert isinstance(request, ITSupportRequest)
    assert request.category == "IT_SUPPORT"


def test_factory_classifies_housekeeping_issues():
    request = build("Cleaning needed",
                    "The classroom floor needs cleaning after the workshop.")
    assert isinstance(request, HousekeepingRequest)
    assert request.priority == "LOW"


def test_factory_falls_back_to_maintenance():
    request = build("Ceiling fan wobbles",
                    "The fan above the third bench wobbles during class.")
    assert isinstance(request, MaintenanceRequest)
    assert request.category == "MAINTENANCE"


def test_escalation_keywords_raise_the_priority():
    calm = build("Air conditioning noise",
                 "The air conditioning unit makes a humming sound in the seminar room.")
    urgent = build("Air conditioning failure",
                   "The air conditioning is not working and the room is unusable. Urgent.")
    assert calm.priority == "MEDIUM"
    assert urgent.priority == "HIGH"


def test_safety_issues_with_escalation_become_critical():
    request = build("Exposed wire near the door",
                    "An exposed wire is sparking near the entrance, this is dangerous.")
    assert request.priority == "CRITICAL"


def test_sla_matrix_is_polymorphic():
    assert SafetyRequest.sla_hours_for("CRITICAL") == 1
    assert MaintenanceRequest.sla_hours_for("CRITICAL") == 2
    assert ITSupportRequest.sla_hours_for("HIGH") == 6
    assert HousekeepingRequest.sla_hours_for("LOW") == 36


def test_sla_due_date_follows_the_priority():
    request = build("Water leak in the corridor",
                    "Water is leaking from the ceiling in the main corridor.")
    delta = (request.sla_due_at - request.created_at).total_seconds() / 3600
    assert round(delta) == request.sla_hours


def test_explicit_category_and_priority_override_the_rules():
    request = build("Chair repair", "One chair needs a small repair.",
                    category="SAFETY", priority="CRITICAL")
    assert isinstance(request, SafetyRequest)
    assert request.priority == "CRITICAL"
    assert request.sla_hours == 1


def test_factory_validates_its_input():
    with pytest.raises(ValidationError):
        build("ab", "Description long enough")
    with pytest.raises(ValidationError):
        build("Valid title", "tiny")
    with pytest.raises(ValidationError):
        build("Valid title", "Description long enough", category="UNKNOWN")
    with pytest.raises(ValidationError):
        build("Valid title", "Description long enough", priority="URGENT")


def test_valid_state_transitions(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Bench is loose",
        "The bench in the second row is loose and moves during class.")
    assert request.status == "NEW"
    assigned = facade.assign_request(users["campus.admin"], request.id,
                                     users["tech.arun"].id)
    assert assigned.status == "ASSIGNED"
    started = facade.advance_request(users["tech.arun"], request.id, "IN_PROGRESS")
    assert started.status == "IN_PROGRESS"
    resolved = facade.advance_request(users["tech.arun"], request.id, "RESOLVED")
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None
    closed = facade.advance_request(users["campus.admin"], request.id, "CLOSED")
    assert closed.status == "CLOSED"
    assert closed.is_open() is False


def test_invalid_transition_is_refused(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Loose door handle",
        "The door handle of the seminar room is loose.")
    with pytest.raises(InvalidTransitionError):
        facade.advance_request(users["campus.admin"], request.id, "RESOLVED")
    with pytest.raises(InvalidTransitionError):
        facade.advance_request(users["campus.admin"], request.id, "CLOSED")


def test_a_closed_request_cannot_be_reopened(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Window latch broken",
        "The window latch does not close properly in the seminar room.")
    facade.assign_request(users["campus.admin"], request.id, users["tech.arun"].id)
    facade.advance_request(users["tech.arun"], request.id, "IN_PROGRESS")
    facade.advance_request(users["tech.arun"], request.id, "RESOLVED")
    facade.advance_request(users["campus.admin"], request.id, "CLOSED")
    with pytest.raises(InvalidTransitionError):
        facade.advance_request(users["campus.admin"], request.id, "IN_PROGRESS")


def test_a_resolved_request_can_be_reopened_for_more_work(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Light flickers",
        "The tube light in the seminar room flickers during the evening.")
    facade.assign_request(users["campus.admin"], request.id, users["tech.mohan"].id)
    facade.advance_request(users["tech.mohan"], request.id, "IN_PROGRESS")
    facade.advance_request(users["tech.mohan"], request.id, "RESOLVED")
    reopened = facade.advance_request(users["tech.mohan"], request.id, "IN_PROGRESS")
    assert reopened.status == "IN_PROGRESS"
    assert reopened.resolved_at is None


def test_status_cannot_be_set_to_the_same_value(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Notice board damaged",
        "The notice board in the seminar room is coming off the wall.")
    facade.assign_request(users["campus.admin"], request.id, users["tech.arun"].id)
    facade.advance_request(users["tech.arun"], request.id, "IN_PROGRESS")
    with pytest.raises(InvalidTransitionError):
        facade.advance_request(users["tech.arun"], request.id, "IN_PROGRESS")


def test_only_the_assigned_technician_can_update_a_request(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Fan speed regulator broken",
        "The fan regulator in the seminar room does not change the speed.")
    facade.assign_request(users["campus.admin"], request.id, users["tech.arun"].id)
    with pytest.raises(PermissionDeniedError):
        facade.advance_request(users["tech.mohan"], request.id, "IN_PROGRESS")


def test_students_cannot_update_request_status(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Chair missing",
        "One chair is missing from the seminar room.")
    with pytest.raises(PermissionDeniedError):
        facade.advance_request(users["athisaya"], request.id, "ASSIGNED")


def test_requests_can_only_be_assigned_to_maintenance_staff(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Speaker not audible",
        "The speaker in the seminar room is not audible at the back.")
    with pytest.raises(ValidationError):
        facade.assign_request(users["campus.admin"], request.id, users["dr.kavitha"].id)


def test_history_records_every_transition(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Projector remote missing",
        "The projector remote control is missing from the seminar room.")
    facade.assign_request(users["campus.admin"], request.id, users["tech.mohan"].id)
    facade.advance_request(users["tech.mohan"], request.id, "IN_PROGRESS",
                           "Ordered a replacement remote")
    stored = facade.repos.requests.get(request.id)
    statuses = [entry["to_status"] for entry in stored.history]
    assert statuses == ["NEW", "ASSIGNED", "IN_PROGRESS"]
    assert "replacement remote" in stored.history[-1]["note"]


def test_sla_state_reports_on_track_and_breached(facade, users, resources):
    request = facade.submit_service_request(
        users["athisaya"], resources["CR-201"].id, "Table wobbles",
        "The demonstration table in the seminar room wobbles.")
    assert request.sla_state(now()) in ("ON_TRACK", "AT_RISK")
    assert request.sla_state(request.sla_due_at.replace(year=request.sla_due_at.year + 1)) \
        == "BREACHED"


def test_escalation_shortens_the_sla():
    request = build("Ceiling fan wobbles", "The fan above the bench wobbles during class.")
    original = request.sla_hours
    request.escalate()
    assert request.priority == "HIGH"
    assert request.sla_hours < original
