"""Inheritance, polymorphism and role based permissions of the user hierarchy."""

import pytest

from app.domain.users import (Administrator, Faculty, MaintenanceStaff, Permission,
                              SecurityOfficer, Student, User, build_user)
from app.exceptions import ValidationError


def make(cls, **kwargs):
    defaults = dict(user_id=1, username="demo.user", full_name="Demo User",
                    email="demo@aiscams.edu", department="Testing")
    defaults.update(kwargs)
    return cls(**defaults)


def test_user_is_abstract_and_cannot_be_instantiated():
    with pytest.raises(TypeError):
        User(1, "demo.user", "Demo User", "demo@aiscams.edu")


def test_every_role_class_inherits_from_user():
    for cls in (Student, Faculty, Administrator, SecurityOfficer, MaintenanceStaff):
        assert issubclass(cls, User)
        assert isinstance(make(cls), User)


def test_role_and_job_title_are_polymorphic():
    titles = {make(cls).role: make(cls).job_title
              for cls in (Student, Faculty, Administrator, SecurityOfficer, MaintenanceStaff)}
    assert titles["STUDENT"].startswith("Student")
    assert titles["FACULTY"].startswith("Faculty")
    assert titles["ADMIN"] == "Campus Administrator"
    assert titles["SECURITY"] == "Security Officer"
    assert titles["MAINTENANCE"].startswith("Maintenance Technician")


def test_permissions_differ_per_role():
    student = make(Student)
    admin = make(Administrator)
    technician = make(MaintenanceStaff)
    assert student.has_permission(Permission.BOOK_RESOURCE)
    assert not student.has_permission(Permission.VIEW_ANALYTICS)
    assert admin.has_permission(Permission.VIEW_ANALYTICS)
    assert admin.has_permission(Permission.MANAGE_USERS)
    assert technician.has_permission(Permission.UPDATE_REQUEST_STATUS)
    assert not technician.has_permission(Permission.BOOK_RESOURCE)


def test_security_officer_can_acknowledge_alerts_only_within_its_scope():
    officer = make(SecurityOfficer)
    assert officer.has_permission(Permission.ACKNOWLEDGE_ALERT)
    assert officer.has_permission(Permission.MONITOR_PARKING)
    assert not officer.has_permission(Permission.RECORD_ATTENDANCE)
    assert not officer.has_permission(Permission.APPROVE_BOOKING)


def test_dashboard_sections_are_role_specific():
    assert "today_classes" in make(Student).dashboard_sections()
    assert "teaching_load" in make(Faculty).dashboard_sections()
    assert "utilisation" in make(Administrator).dashboard_sections()
    assert "parking" in make(SecurityOfficer).dashboard_sections()
    assert "assigned_requests" in make(MaintenanceStaff).dashboard_sections()


def test_build_user_factory_returns_the_matching_subclass():
    user = build_user("FACULTY", user_id=9, username="dr.demo", full_name="Dr Demo",
                      email="dr@aiscams.edu")
    assert isinstance(user, Faculty)
    with pytest.raises(ValidationError):
        build_user("PRINCIPAL", user_id=9, username="x.y", full_name="X Y",
                   email="x@aiscams.edu")


def test_user_input_validation_rejects_bad_values():
    with pytest.raises(ValidationError):
        make(Student, username="ab")
    with pytest.raises(ValidationError):
        make(Student, full_name="   ")
    with pytest.raises(ValidationError):
        make(Student, email="not-an-email")


def test_encapsulated_state_is_exposed_read_only():
    student = make(Student)
    assert student.username == "demo.user"
    with pytest.raises(AttributeError):
        student.username = "hacker"
    student.deactivate()
    assert student.is_active is False
    student.activate()
    assert student.is_active is True


def test_seeded_users_are_loaded_as_concrete_subclasses(users):
    assert isinstance(users["athisaya"], Student)
    assert isinstance(users["dr.kavitha"], Faculty)
    assert isinstance(users["campus.admin"], Administrator)
    assert isinstance(users["security.ravi"], SecurityOfficer)
    assert isinstance(users["tech.mohan"], MaintenanceStaff)


def test_to_dict_exposes_role_metadata(users):
    data = users["athisaya"].to_dict()
    assert data["role"] == "STUDENT"
    assert Permission.BOOK_RESOURCE in data["permissions"]
    assert "password" not in data
