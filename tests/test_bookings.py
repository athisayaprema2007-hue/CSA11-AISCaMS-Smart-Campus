"""Booking workflow: validation, conflicts, capacity, equipment and approval."""

from datetime import timedelta

import pytest

from app.exceptions import (BookingConflictError, CapacityError, EquipmentError,
                            PermissionDeniedError, ResourceUnavailableError,
                            ValidationError)
from app.utils import now, to_db


@pytest.fixture
def window():
    start = (now() + timedelta(days=5)).replace(hour=14, minute=0, second=0, microsecond=0)
    return to_db(start), to_db(start + timedelta(hours=2))


def test_booking_is_created_and_confirmed(facade, users, resources, window):
    booking = facade.book_resource(users["dr.kavitha"], resources["CR-101"].id,
                                   window[0], window[1], 40, "Guest lecture")
    assert booking.status == "CONFIRMED"
    assert booking.reference.startswith("BK-")
    assert booking.duration_hours == 2.0
    assert booking.resource_code == "CR-101"


def test_booking_is_persisted_and_retrievable(facade, users, resources, window):
    booking = facade.book_resource(users["athisaya"], resources["CR-201"].id,
                                   window[0], window[1], 10, "Project meeting")
    stored = facade.repos.bookings.get_by_reference(booking.reference)
    assert stored is not None
    assert stored.user_id == users["athisaya"].id
    assert stored.purpose == "Project meeting"


def test_overlapping_booking_is_rejected(facade, users, resources, window):
    facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, window[0],
                         window[1], 30, "Lecture")
    with pytest.raises(BookingConflictError):
        facade.book_resource(users["dr.suresh"], resources["CR-101"].id, window[0],
                             window[1], 20, "Another lecture")


def test_partially_overlapping_booking_is_rejected(facade, users, resources, window):
    facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, window[0],
                         window[1], 30, "Lecture")
    start = (now() + timedelta(days=5)).replace(hour=15, minute=0, second=0, microsecond=0)
    with pytest.raises(BookingConflictError):
        facade.book_resource(users["dr.suresh"], resources["CR-101"].id, to_db(start),
                             to_db(start + timedelta(hours=1)), 20, "Overlap")


def test_adjacent_bookings_are_allowed(facade, users, resources, window):
    facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, window[0],
                         window[1], 30, "Lecture")
    start = (now() + timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0)
    second = facade.book_resource(users["dr.suresh"], resources["CR-101"].id,
                                  to_db(start), to_db(start + timedelta(hours=1)),
                                  20, "Follow up")
    assert second.status == "CONFIRMED"


def test_capacity_is_validated(facade, users, resources, window):
    with pytest.raises(CapacityError):
        facade.book_resource(users["dr.kavitha"], resources["CR-201"].id, window[0],
                             window[1], 45, "Too many people")


def test_required_equipment_is_validated(facade, users, resources, window):
    with pytest.raises(EquipmentError):
        facade.book_resource(users["dr.kavitha"], resources["CR-202"].id, window[0],
                             window[1], 15, "Needs a projector",
                             required_equipment=["PROJECTOR"])


def test_unavailable_resource_cannot_be_booked(facade, users, resources, window):
    with pytest.raises(ResourceUnavailableError):
        facade.book_resource(users["dr.kavitha"], resources["CR-102"].id, window[0],
                             window[1], 20, "Room under maintenance")


def test_parking_area_is_not_bookable(facade, users, resources, window):
    with pytest.raises(ResourceUnavailableError):
        facade.book_resource(users["dr.kavitha"], resources["PK-A"].id, window[0],
                             window[1], 1, "Parking slot")


def test_booking_in_the_past_is_rejected(facade, users, resources):
    start = now() - timedelta(days=2)
    with pytest.raises(ValidationError):
        facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, to_db(start),
                             to_db(start + timedelta(hours=1)), 10, "Yesterday")


def test_end_time_must_follow_start_time(facade, users, resources, window):
    with pytest.raises(ValidationError):
        facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, window[1],
                             window[0], 10, "Reversed window")


def test_purpose_is_validated(facade, users, resources, window):
    with pytest.raises(ValidationError):
        facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, window[0],
                             window[1], 10, "x")


def test_maintenance_staff_cannot_book_resources(facade, users, resources, window):
    with pytest.raises(PermissionDeniedError):
        facade.book_resource(users["tech.mohan"], resources["CR-101"].id, window[0],
                             window[1], 5, "Not allowed")


def test_student_laboratory_booking_requires_approval(facade, users, resources, window):
    booking = facade.book_resource(users["athisaya"], resources["LB-CS1"].id, window[0],
                                   window[1], 20, "Practice session")
    assert booking.status == "PENDING"
    approved = facade.bookings.approve_booking(users["campus.admin"], booking.id, True)
    assert approved.status == "CONFIRMED"
    assert approved.approved_by == users["campus.admin"].id


def test_administrator_can_reject_a_pending_booking(facade, users, resources, window):
    booking = facade.book_resource(users["athisaya"], resources["LB-CS1"].id, window[0],
                                   window[1], 20, "Practice session")
    rejected = facade.bookings.approve_booking(users["campus.admin"], booking.id, False)
    assert rejected.status == "REJECTED"


def test_only_an_administrator_can_approve(facade, users, resources, window):
    booking = facade.book_resource(users["athisaya"], resources["LB-CS1"].id, window[0],
                                   window[1], 20, "Practice session")
    with pytest.raises(PermissionDeniedError):
        facade.bookings.approve_booking(users["dr.kavitha"], booking.id, True)


def test_owner_can_cancel_and_the_slot_is_released(facade, users, resources, window):
    booking = facade.book_resource(users["dr.kavitha"], resources["CR-101"].id,
                                   window[0], window[1], 30, "Lecture")
    cancelled = facade.bookings.cancel_booking(users["dr.kavitha"], booking.id)
    assert cancelled.status == "CANCELLED"
    reused = facade.book_resource(users["dr.suresh"], resources["CR-101"].id, window[0],
                                  window[1], 25, "Reuses the released slot")
    assert reused.status == "CONFIRMED"


def test_a_user_cannot_cancel_someone_elses_booking(facade, users, resources, window):
    booking = facade.book_resource(users["dr.kavitha"], resources["CR-101"].id,
                                   window[0], window[1], 30, "Lecture")
    with pytest.raises(PermissionDeniedError):
        facade.bookings.cancel_booking(users["athisaya"], booking.id)
