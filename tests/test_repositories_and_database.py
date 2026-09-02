"""Repository operations, database constraints and idempotent seeding."""

import sqlite3

import pytest

from app.exceptions import NotFoundError, ValidationError
from app.seed import seed_database, summary
from app.utils import now, to_db


# ------------------------------------------------------------ repositories
def test_user_repository_round_trip(repos):
    created = repos.users.add("new.student", "New Student", "new.student@aiscams.edu",
                              "campus123", "STUDENT", "Mechanical Engineering")
    fetched = repos.users.get(created.id)
    assert fetched.username == "new.student"
    assert fetched.role == "STUDENT"
    assert repos.users.get_by_username("new.student").id == created.id


def test_user_repository_rejects_duplicates(repos):
    with pytest.raises(ValidationError):
        repos.users.add("athisaya", "Duplicate", "dup@aiscams.edu", "campus123", "STUDENT")
    with pytest.raises(ValidationError):
        repos.users.add("unique.name", "Duplicate mail", "athisaya@aiscams.edu",
                        "campus123", "STUDENT")


def test_user_repository_authenticates(repos):
    user = repos.users.authenticate("athisaya", "campus123")
    assert user.full_name == "Athisaya U"
    from app.exceptions import AuthenticationError
    with pytest.raises(AuthenticationError):
        repos.users.authenticate("athisaya", "wrong-password")
    with pytest.raises(AuthenticationError):
        repos.users.authenticate("ghost", "campus123")


def test_user_repository_changes_roles(repos):
    user = repos.users.get_by_username("arjun.p")
    changed = repos.users.change_role(user.id, "FACULTY")
    assert changed.role == "FACULTY"
    assert changed.job_title.startswith("Faculty")


def test_resource_repository_filters(repos):
    classrooms = repos.resources.list_resources(resource_type="CLASSROOM")
    assert classrooms and all(item.resource_type == "CLASSROOM" for item in classrooms)
    large = repos.resources.list_resources(min_capacity=80)
    assert all(item.capacity >= 80 for item in large)
    projector_rooms = repos.resources.list_resources(bookable_only=True,
                                                     equipment=["PROJECTOR"])
    assert all("PROJECTOR" in item.equipment_codes for item in projector_rooms)
    searched = repos.resources.list_resources(search="Innovation")
    assert any(item.code == "IH-101" for item in searched)


def test_resource_repository_updates_status_and_equipment(repos):
    resource = repos.resources.get_by_code("CR-201")
    updated = repos.resources.update_status(resource.id, "MAINTENANCE")
    assert updated.status == "MAINTENANCE"
    with_faulty = repos.resources.set_equipment_condition(resource.id, "AC", "FAULTY")
    assert with_faulty.equipment["AC"] == "FAULTY"
    assert with_faulty.has_equipment("AC") is False
    with pytest.raises(ValidationError):
        repos.resources.update_status(resource.id, "EXPLODED")


def test_repository_raises_not_found_for_unknown_identifiers(repos):
    with pytest.raises(NotFoundError):
        repos.resources.require_resource(9999)
    with pytest.raises(NotFoundError):
        repos.bookings.require_booking(9999)
    with pytest.raises(NotFoundError):
        repos.requests.require_request(9999)
    with pytest.raises(NotFoundError):
        repos.users.require_user(9999)


def test_booking_repository_conflict_query(facade, repos, users, resources):
    from datetime import timedelta
    start = (now() + timedelta(days=6)).replace(hour=11, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    assert repos.bookings.conflicts(resources["CR-101"].id, start, end) == []
    facade.book_resource(users["dr.kavitha"], resources["CR-101"].id, to_db(start),
                         to_db(end), 20, "Repository conflict check")
    assert len(repos.bookings.conflicts(resources["CR-101"].id, start, end)) == 1


def test_notification_repository_marks_messages_as_read(repos, users):
    user = users["athisaya"]
    repos.notifications.add(user.id, "Test", "A test notification", "SYSTEM")
    unread_before = repos.notifications.unread_count(user.id)
    assert unread_before >= 1
    newest = repos.notifications.for_user(user.id, unread_only=True)[0]
    repos.notifications.mark_read(newest.id, user.id)
    assert repos.notifications.unread_count(user.id) == unread_before - 1
    repos.notifications.mark_all_read(user.id)
    assert repos.notifications.unread_count(user.id) == 0


def test_schedule_repository_reads_timetables_and_attendance(repos, users):
    student = users["athisaya"]
    classes = repos.schedules.for_student(student.id)
    assert classes
    summary_data = repos.schedules.attendance_summary(student.id)
    assert summary_data["sessions"] > 0
    assert 0 <= summary_data["percentage"] <= 100
    faculty_classes = repos.schedules.for_faculty(users["dr.kavitha"].id)
    assert all(item.faculty_id == users["dr.kavitha"].id for item in faculty_classes)


def test_attendance_recording_is_validated(repos, users):
    schedule = repos.schedules.for_faculty(users["dr.kavitha"].id)[0]
    records = repos.schedules.record_attendance(schedule.id, users["athisaya"].id,
                                                "2026-01-05", "PRESENT",
                                                users["dr.kavitha"].id)
    assert any(record.student_id == users["athisaya"].id for record in records)
    with pytest.raises(ValidationError):
        repos.schedules.record_attendance(schedule.id, users["security.ravi"].id,
                                          "2026-01-05", "PRESENT")
    with pytest.raises(ValidationError):
        repos.schedules.record_attendance(schedule.id, users["athisaya"].id,
                                          "2026-01-05", "MAYBE")


def test_event_repository_registration_rules(repos, users):
    event = repos.events.list_events(upcoming_only=True)[0]
    registered = repos.events.register(event.id, users["arjun.p"].id)
    assert registered.registered is True
    again = repos.events.register(event.id, users["arjun.p"].id)
    assert again.registrations == registered.registrations


# -------------------------------------------------------------- constraints
def test_foreign_keys_are_enforced(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO bookings (reference, resource_id, user_id, purpose,"
                       " start_time, end_time, attendees) VALUES"
                       " ('BK-X', 9999, 1, 'Ghost', '2026-01-01 10:00:00',"
                       " '2026-01-01 11:00:00', 5)")


def test_check_constraints_reject_invalid_rows(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO campus_resources (code, name, resource_type,"
                       " building_id, capacity) VALUES ('X-1', 'Bad', 'SWIMMING_POOL', 1, 10)")
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO service_requests (ticket, resource_id, category,"
                       " priority, title, description, sla_hours, sla_due_at) VALUES"
                       " ('SR-X', 1, 'MAINTENANCE', 'SUPER', 'Title', 'Description',"
                       " 4, '2026-01-01 10:00:00')")


def test_unique_constraints_are_enforced(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO roles (name, description) VALUES ('STUDENT', 'dup')")
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO buildings (code, name, walking_distance_m)"
                       " VALUES ('MB', 'Duplicate block', 10)")


def test_booking_window_check_constraint(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO bookings (reference, resource_id, user_id, purpose,"
                       " start_time, end_time, attendees) VALUES"
                       " ('BK-Y', 1, 1, 'Reversed', '2026-01-01 12:00:00',"
                       " '2026-01-01 10:00:00', 5)")


def test_attendance_is_unique_per_student_and_session(seeded, repos, users):
    schedule = repos.schedules.for_faculty(users["dr.kavitha"].id)[0]
    seeded.execute("INSERT INTO attendance (schedule_id, student_id, session_date, status)"
                   " VALUES (?,?,?,?)", (schedule.id, users["athisaya"].id,
                                         "2026-02-02", "PRESENT"))
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("INSERT INTO attendance (schedule_id, student_id, session_date,"
                       " status) VALUES (?,?,?,?)",
                       (schedule.id, users["athisaya"].id, "2026-02-02", "ABSENT"))


# ------------------------------------------------------------------- seed
def test_seed_builds_the_campus_from_an_empty_file(empty_db_path):
    from app.database import connect, init_schema

    connection = connect(empty_db_path)
    init_schema(connection)
    assert summary(connection)["users"] == 0
    seed_database(connection)
    counts = summary(connection)
    assert counts["users"] == 12
    assert counts["campus_resources"] == 27
    connection.close()


def test_seed_is_idempotent(seeded):
    before = summary(seeded)
    seed_database(seeded)
    seed_database(seeded)
    after = summary(seeded)
    assert before == after


def test_seed_creates_the_expected_campus(seeded):
    counts = summary(seeded)
    assert counts["roles"] == 5
    assert counts["users"] == 12
    assert counts["campus_resources"] == 27
    assert counts["schedules"] == 12
    assert counts["service_requests"] >= 7
    assert counts["iot_readings"] >= 30
    assert counts["events"] == 5
    assert counts["digital_services"] == 6


def test_indexes_exist_for_the_hot_queries(seeded):
    rows = seeded.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    names = {row["name"] for row in rows}
    for index in ("idx_bookings_resource", "idx_requests_status", "idx_readings_device",
                  "idx_notifications_user", "idx_users_role"):
        assert index in names
