# Implementation handoff - AISCaMS

This document describes **exactly what the delivered implementation contains**, so
that the report, the UML models and the repository can be prepared directly from
it. Everything below was read off the working code, the running application and a
real test run. Nothing here is aspirational: if a feature is not implemented, it
is listed under *Assumptions and limitations*.

---

## 1. Final project title

**AI-Enabled Smart Campus Management System (AISCaMS)**
Object-Oriented Analysis and Design of a role-based smart campus platform with
IoT monitoring and an explainable resource-recommendation strategy.

* Course: CSA11 - Object Oriented Analysis and Design
* Student: Athisaya U
* Registration number: 192571001

---

## 2. Technology stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11 |
| Web framework | Flask 3.1.3 (Jinja2 3.1.6, Werkzeug 3.1.8) |
| Database | SQLite 3 (Python standard library `sqlite3`) |
| Front end | Server-rendered HTML (Jinja2), hand-written CSS, vanilla JavaScript (no framework, no build step) |
| Password hashing | `werkzeug.security` (scrypt) |
| Testing | Pytest 9.1.1 (170 tests) |
| Runtime | Local only - no paid services, API keys, cloud accounts or external databases |

Source size: 6,485 lines of application Python + 1,757 lines of test Python,
plus SQL schema, templates, CSS and JavaScript.

---

## 3. Complete project-file structure

```
AISCaMS/
├── app/
│   ├── __init__.py                    application factory, navigation, error handlers, CLI
│   ├── config.py                      BaseConfig / TestConfig
│   ├── database.py                    connection handling, schema bootstrap
│   ├── exceptions.py                  domain exception hierarchy
│   ├── schema.sql                     SQLite schema (tables, constraints, indexes)
│   ├── security.py                    session handling, permission decorators
│   ├── seed.py                        deterministic idempotent demo data
│   ├── utils.py                       time helpers and input validators
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── academics.py               Schedule, AttendanceRecord
│   │   ├── booking.py                 Booking
│   │   ├── events.py                  CampusEvent
│   │   ├── iot.py                     IoTReading + threshold rules
│   │   ├── notification.py            Notification
│   │   ├── resources.py               CampusResource hierarchy + Building
│   │   ├── service_request.py         ServiceRequest hierarchy + state machine
│   │   └── users.py                   User hierarchy + Permission constants
│   ├── patterns/
│   │   ├── __init__.py
│   │   ├── factory.py                 ServiceRequestFactory
│   │   ├── observer.py                Subject, Observer, three concrete observers
│   │   └── strategy.py                RecommendationStrategy hierarchy
│   ├── repositories/
│   │   ├── __init__.py                RepositoryRegistry
│   │   ├── base.py                    BaseRepository
│   │   ├── booking_repository.py
│   │   ├── event_repository.py        EventRepository, DigitalServiceRepository
│   │   ├── iot_repository.py          IoTRepository, AlertRepository
│   │   ├── notification_repository.py
│   │   ├── request_repository.py
│   │   ├── resource_repository.py
│   │   ├── schedule_repository.py
│   │   └── user_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics_service.py
│   │   ├── booking_service.py
│   │   ├── campus_facade.py           CampusFacade (Facade pattern)
│   │   ├── iot_service.py
│   │   ├── maintenance_service.py
│   │   └── recommendation_service.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py                     JSON API blueprint (/api)
│   │   ├── auth.py                    sign in, demo role selection, sign out
│   │   └── views.py                   HTML page blueprint
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/app.js
│   └── templates/
│       ├── _icons.html, _macros.html, base.html, login.html, error.html
│       ├── admin.html, bookings.html, events.html, facilities.html, iot.html
│       ├── maintenance.html, notifications.html, recommendations.html
│       ├── requests.html, schedule.html
│       └── dashboards/
│           ├── admin.html, faculty.html, maintenance.html,
│           ├── security.html, student.html
├── tests/
│   ├── conftest.py
│   ├── test_api_and_access.py             32 tests
│   ├── test_bookings.py                   18 tests
│   ├── test_iot_and_alerts.py             20 tests
│   ├── test_observer_and_dashboards.py    18 tests
│   ├── test_recommendations.py            16 tests
│   ├── test_repositories_and_database.py  21 tests
│   ├── test_resources.py                  12 tests
│   ├── test_service_requests.py           22 tests
│   └── test_users_and_roles.py            11 tests
├── docs/
│   ├── IMPLEMENTATION_HANDOFF.md      this document
│   ├── test_results.txt               captured output of a real test run
│   └── screenshots/                   01 ... 08 PNG files
├── instance/                          SQLite database, created at runtime
├── manage.py                          database CLI
├── run.py                             development entry point
├── run.bat                            one-click Windows setup and start
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 4. Installation and execution commands

```bat
:: 1. create an isolated environment
python -m venv .venv

:: 2. install the dependencies
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: 3. create and seed the database (idempotent)
.venv\Scripts\python.exe manage.py seed

:: 4. run the application
.venv\Scripts\python.exe run.py
```

Application URL: <http://127.0.0.1:5000> - demo password for every account:
`campus123`.

`run.bat` performs steps 1-4 in one double-click.

Other commands: `manage.py init-db`, `manage.py summary`, `manage.py reset`,
and the Flask CLI equivalents `flask --app app init-db` / `flask --app app seed`.

---

## 5. Test command and exact result

```bat
.venv\Scripts\python.exe -m pytest
```

Result of the run captured in `docs/test_results.txt` and in screenshot 08:

```
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collected 170 items
...
170 passed
```

**170 tests collected, 170 passed, 0 failed, 0 skipped.**
Typical duration: 20-25 seconds.

---

## 6. List of actors

| # | Actor | Type | Notes |
| --- | --- | --- | --- |
| 1 | Student | Primary human actor | `STUDENT` role |
| 2 | Faculty Member | Primary human actor | `FACULTY` role |
| 3 | Administrator | Primary human actor | `ADMIN` role |
| 4 | Security Personnel | Primary human actor | `SECURITY` role |
| 5 | Maintenance Staff | Primary human actor | `MAINTENANCE` role |
| 6 | IoT Device / IoT Gateway | External system actor | publishes readings through `POST /api/iot/readings`; owns no login of its own, the endpoint is exercised by the monitoring roles and by `IoTService.record_reading()` |

---

## 7. Implemented use cases for each actor

### Student (`Student`)
1. Sign in / select a demo role
2. View personal dashboard (classes today, attendance %, bookings, open requests)
3. View academic schedule (weekly timetable)
4. Search campus facilities (type, building, capacity, free-text)
5. Receive intelligent classroom/resource recommendations with scores and reasons
6. Book an available classroom or facility
7. Cancel own booking
8. View upcoming campus events and register for an event
9. Access digital-campus services catalogue
10. Submit a service/maintenance request
11. Track submitted request status and history
12. Receive booking and request notifications; mark them read

### Faculty Member (`Faculty`)
1. View and manage class schedules (weekly teaching timetable)
2. Record and review attendance per class session (present / late / absent)
3. Search and book classrooms
4. Specify capacity and equipment requirements when searching or booking
5. Receive intelligent classroom recommendations
6. Report classroom or equipment issues
7. Track own reported issues
8. View academic activities and campus events
9. Receive notifications

### Administrator (`Administrator`)
1. Manage users (create account, change role, activate/deactivate)
2. Manage campus resources (register classroom / laboratory / parking area /
   smart device, change resource status)
3. Review and approve or reject bookings that require approval
4. View campus utilisation analytics
5. Manage campus events (publish, cancel)
6. Assign service requests to maintenance staff
7. Monitor active requests and SLA status (on track / at risk / breached)
8. View IoT monitoring and acknowledge alerts
9. Update request status (e.g. close a resolved ticket)

### Security Personnel (`SecurityOfficer`)
1. Monitor parking occupancy per zone
2. View security and safety alerts
3. View relevant IoT readings (latest value per device)
4. Acknowledge infrastructure alerts
5. Raise a service request for something observed on patrol

### Maintenance Staff (`MaintenanceStaff`)
1. View assigned service requests (priority ordered)
2. Update request status through the legal state transitions
3. Update equipment condition (good / fair / faulty / out of service)
4. View priority and SLA information, including breach state
5. Mark work as in progress, resolved and closed
6. View critical IoT readings behind automatically raised tickets

### IoT Device / IoT Gateway (external system)
1. Publish a reading (occupancy, temperature, air quality, equipment status,
   parking occupancy, device status)
2. Trigger an automatic alert and a critical maintenance/safety ticket when a
   reading crosses a critical threshold
3. Update the parking area occupancy and device online state as a side effect

---

## 8. Complete domain-class list

Abstract classes are marked *(abstract)*.

| Class | Module |
| --- | --- |
| `User` *(abstract)* | `app/domain/users.py` |
| `Student` | `app/domain/users.py` |
| `Faculty` | `app/domain/users.py` |
| `Administrator` | `app/domain/users.py` |
| `SecurityOfficer` | `app/domain/users.py` |
| `MaintenanceStaff` | `app/domain/users.py` |
| `Permission` (constants) | `app/domain/users.py` |
| `CampusResource` *(abstract)* | `app/domain/resources.py` |
| `Classroom` | `app/domain/resources.py` |
| `Laboratory` | `app/domain/resources.py` |
| `ParkingArea` | `app/domain/resources.py` |
| `SmartDevice` | `app/domain/resources.py` |
| `Building` (value object) | `app/domain/resources.py` |
| `Booking` | `app/domain/booking.py` |
| `ServiceRequest` *(abstract)* | `app/domain/service_request.py` |
| `MaintenanceRequest` | `app/domain/service_request.py` |
| `SafetyRequest` | `app/domain/service_request.py` |
| `ITSupportRequest` | `app/domain/service_request.py` |
| `HousekeepingRequest` | `app/domain/service_request.py` |
| `IoTReading` | `app/domain/iot.py` |
| `CampusEvent` | `app/domain/events.py` |
| `Notification` | `app/domain/notification.py` |
| `Schedule` | `app/domain/academics.py` |
| `AttendanceRecord` | `app/domain/academics.py` |

Supporting (non-entity) classes that also belong on the class diagram:

| Class | Module | Role |
| --- | --- | --- |
| `RecommendationStrategy` *(abstract)* | `patterns/strategy.py` | Strategy |
| `WeightedRankingStrategy` | `patterns/strategy.py` | Strategy |
| `ProximityFirstStrategy` | `patterns/strategy.py` | Strategy |
| `UtilisationBalancingStrategy` | `patterns/strategy.py` | Strategy |
| `RecommendationCriteria`, `Candidate`, `ScoredRecommendation` | `patterns/strategy.py` | parameter/result objects |
| `ServiceRequestFactory` | `patterns/factory.py` | Factory |
| `Subject`, `Observer` *(abstract)*, `NotificationObserver`, `AlertObserver`, `AuditTrailObserver` | `patterns/observer.py` | Observer |
| `BaseRepository` + 10 concrete repositories, `RepositoryRegistry` | `repositories/` | Repository |
| `CampusFacade` | `services/campus_facade.py` | Facade |
| `BookingService`, `MaintenanceService`, `RecommendationService`, `IoTService`, `AnalyticsService` | `services/` | application services |

---

## 9. Important attributes and methods of every domain class

Attributes are private (`_name`) and exposed through read-only properties, which
is how encapsulation is demonstrated. Only the public surface is listed.

### `User` *(abstract)*
* Attributes: `id`, `username`, `full_name`, `email`, `department`, `phone`, `is_active`
* Abstract members: `role`, `job_title`, `permissions()`, `landing_page()`
* Concrete methods: `has_permission(permission)`, `dashboard_sections()`,
  `activate()`, `deactivate()`, `to_dict()`
* Validation: `_validate_username`, `_validate_name`, `_validate_email`

| Subclass | `role` | `permissions()` size | `landing_page()` |
| --- | --- | --- | --- |
| `Student` | `STUDENT` | 9 | `views.dashboard` |
| `Faculty` | `FACULTY` | 10 | `views.dashboard` |
| `Administrator` | `ADMIN` | 19 | `views.admin` |
| `SecurityOfficer` | `SECURITY` | 8 | `views.security` |
| `MaintenanceStaff` | `MAINTENANCE` | 6 | `views.maintenance` |

### `CampusResource` *(abstract)*
* Attributes: `id`, `code`, `name`, `building`, `floor`, `capacity`, `status`,
  `utilisation`, `equipment` (code -> condition), `walking_distance_m`
* Abstract members: `resource_type`, `summary()`
* Methods: `is_available()`, `is_bookable()`, `has_equipment(code)`,
  `missing_equipment(required)`, `matches_capacity(attendees)`,
  `set_status(status)`, `set_equipment_condition(code, condition)`, `to_dict()`

| Subclass | Extra attributes | Overridden behaviour |
| --- | --- | --- |
| `Classroom` | `seating_type`, `board_type` | `is_bookable() -> True`, `summary()` |
| `Laboratory` | `lab_type`, `safety_level`, `workstations` | `is_bookable() -> True`, `matches_capacity()` (limited by workstations), `summary()` |
| `ParkingArea` | `zone`, `total_slots`, `occupied_slots`, `free_slots`, `occupancy_rate` | `update_occupancy(n)`, `summary()` |
| `SmartDevice` | `device_type`, `firmware`, `monitors_id`, `is_online`, `last_heartbeat` | `is_operational()`, `summary()` |

### `Building` (value object)
* Attributes: `id`, `code`, `name`, `walking_distance_m`; method `to_dict()`

### `Booking`
* Attributes: `id`, `reference` (`BK-00007`), `resource_id`, `user_id`, `purpose`,
  `start_time`, `end_time`, `attendees`, `status`, `approved_by`, `created_at`,
  `duration_hours`
* Methods: `overlaps(start, end)`, `blocks_calendar()`, `confirm(approver_id)`,
  `reject(approver_id)`, `cancel()`, `complete()`, `to_dict()`
* Rules: end after start, maximum 8 hours, purpose >= 3 characters, attendees >= 1
* Statuses: `PENDING`, `CONFIRMED`, `REJECTED`, `CANCELLED`, `COMPLETED`

### `ServiceRequest` *(abstract)*
* Attributes: `id`, `ticket` (`SR-00008`), `resource_id`, `title`, `description`,
  `category`, `category_label`, `priority`, `status`, `raised_by`, `assigned_to`,
  `source` (`USER` / `IOT`), `sla_hours`, `sla_due_at`, `created_at`, `updated_at`,
  `resolved_at`, `closed_at`, `history`
* Class members: `CATEGORY`, `SLA_MATRIX`, `sla_hours_for(priority)`
* Abstract member: `handling_team()`
* Methods: `is_open()`, `can_transition_to(status)`, `transition_to(status)`,
  `assign(staff_id)`, `escalate()`, `sla_remaining_hours(ref)`, `sla_state(ref)`,
  `to_dict(ref)`
* Statuses: `NEW`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`, `REJECTED`
* Priorities: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

| Subclass | `CATEGORY` | SLA hours (critical/high/medium/low) | `handling_team()` |
| --- | --- | --- | --- |
| `MaintenanceRequest` | `MAINTENANCE` | 2 / 8 / 24 / 72 | Facilities maintenance |
| `SafetyRequest` | `SAFETY` | 1 / 4 / 12 / 24 | Campus safety and security |
| `ITSupportRequest` | `IT_SUPPORT` | 2 / 6 / 16 / 48 | Campus IT support |
| `HousekeepingRequest` | `HOUSEKEEPING` | 2 / 8 / 12 / 36 | Housekeeping services |

### `IoTReading`
* Attributes: `id`, `device_id`, `resource_id`, `metric`, `metric_label`, `value`,
  `unit`, `severity`, `recorded_at`
* Static rule: `classify(metric, value) -> NORMAL | WARNING | CRITICAL`
* Methods: `is_critical()`, `is_normal()`, `requires_intervention()`,
  `display_value()`, `describe()`, `to_dict()`
* Metrics and thresholds:

| Metric | Warning | Critical |
| --- | --- | --- |
| `OCCUPANCY` (%) | >= 90 | >= 100 |
| `TEMPERATURE` (C) | >= 30 or <= 16 | >= 35 or <= 10 |
| `AIR_QUALITY` (AQI) | >= 150 | >= 250 |
| `PARKING_OCCUPANCY` (%) | >= 85 | >= 97 |
| `EQUIPMENT_STATUS` (1 / 0.5 / 0) | < 1 | <= 0 |
| `DEVICE_STATUS` (1 / 0) | < 1 | <= 0 |

### `CampusEvent`
* Attributes: `id`, `title`, `description`, `category`, `venue_id`, `organiser_id`,
  `start_time`, `end_time`, `capacity`, `status`, `registrations`, `seats_left`
* Methods: `is_upcoming(ref)`, `is_full()`, `cancel()`, `to_dict()`

### `Notification`
* Attributes: `id`, `user_id`, `title`, `message`, `category`, `entity_type`,
  `entity_id`, `is_read`, `created_at`
* Methods: `mark_read()`, `to_dict()`
* Categories: `BOOKING`, `REQUEST`, `ALERT`, `EVENT`, `SYSTEM`

### `Schedule`
* Attributes: `id`, `course_code`, `course_title`, `faculty_id`, `resource_id`,
  `day_of_week`, `start_time`, `end_time`, `semester`, `enrolled`, `time_range`
* Methods: `is_today(day_code)`, `to_dict()`

### `AttendanceRecord`
* Attributes: `id`, `schedule_id`, `student_id`, `session_date`, `status`,
  `recorded_by`
* Methods: `is_present()`, `to_dict()`

---

## 10. Inheritance relationships

```
User (abstract)
├── Student
├── Faculty
├── Administrator
├── SecurityOfficer
└── MaintenanceStaff

CampusResource (abstract)
├── Classroom
├── Laboratory
├── ParkingArea
└── SmartDevice

ServiceRequest (abstract)
├── MaintenanceRequest
├── SafetyRequest
├── ITSupportRequest
└── HousekeepingRequest

RecommendationStrategy (abstract)
└── WeightedRankingStrategy
    ├── ProximityFirstStrategy
    └── UtilisationBalancingStrategy

Observer (abstract)
├── NotificationObserver
├── AlertObserver
└── AuditTrailObserver

BaseRepository
├── UserRepository, ResourceRepository, BookingRepository,
├── ServiceRequestRepository, ScheduleRepository, IoTRepository,
├── AlertRepository, EventRepository, NotificationRepository,
└── DigitalServiceRepository

AiscamsError (exception root)
├── ValidationError → CapacityError, EquipmentError
├── NotFoundError, PermissionDeniedError, AuthenticationError
├── BookingConflictError, ResourceUnavailableError
└── InvalidTransitionError
```

Polymorphism actually exercised at runtime:
`User.permissions()` / `job_title` / `landing_page()` / `dashboard_sections()`,
`CampusResource.resource_type` / `summary()` / `is_bookable()` / `matches_capacity()`,
`ServiceRequest.CATEGORY` / `SLA_MATRIX` / `handling_team()`,
`RecommendationStrategy.score()`, `Observer.update()`.

---

## 11. Associations, aggregations, compositions and dependencies

**Associations**

| From | To | Multiplicity | Meaning |
| --- | --- | --- | --- |
| `User` | `Booking` | 1 .. * | a user makes bookings (`bookings.user_id`) |
| `CampusResource` | `Booking` | 1 .. * | a resource is reserved by bookings |
| `User` | `ServiceRequest` | 1 .. * | a user raises requests (`raised_by`) |
| `MaintenanceStaff` | `ServiceRequest` | 1 .. * | a technician is assigned requests (`assigned_to`) |
| `CampusResource` | `ServiceRequest` | 1 .. * | a request targets one resource |
| `Faculty` | `Schedule` | 1 .. * | faculty teaches scheduled classes |
| `Student` | `Schedule` | * .. * | enrolment (association class `enrollments`) |
| `Schedule` | `AttendanceRecord` | 1 .. * | attendance per session |
| `Student` | `AttendanceRecord` | 1 .. * | attendance of a student |
| `SmartDevice` | `CampusResource` | * .. 1 | a device monitors a resource (`monitors_id`) |
| `SmartDevice` | `IoTReading` | 1 .. * | a device publishes readings |
| `Administrator` | `CampusEvent` | 1 .. * | organiser |
| `User` | `CampusEvent` | * .. * | event registrations |
| `User` | `Notification` | 1 .. * | a notification is addressed to one user |

**Aggregations** (whole/part, parts survive the whole)

* `Building` aggregates `CampusResource` - resources belong to a building but a
  building is not deleted with them (`ON DELETE RESTRICT`).
* `CampusResource` aggregates `Equipment` through `resource_equipment` (with the
  condition of each installed item).
* `Subject` aggregates its `Observer`s - observers exist independently and can be
  attached and detached at runtime.

**Compositions** (parts do not outlive the whole, enforced by `ON DELETE CASCADE`)

* `ServiceRequest` composes its status-history entries (`request_history`).
* `CampusResource` composes its sub-type record (`classrooms`, `laboratories`,
  `parking_areas`, `smart_devices`) and its equipment links.
* `CampusEvent` composes its registrations (`event_registrations`).
* `Schedule` composes its enrolments and attendance records.

**Dependencies** (uses, does not own)

* `RecommendationService` depends on `RecommendationStrategy`,
  `ResourceRepository`, `BookingRepository`, `IoTRepository`.
* `MaintenanceService` depends on `ServiceRequestFactory` and the event bus.
* `IoTService` depends on `MaintenanceService`, `AlertRepository`, `IoTRepository`.
* `BookingService` depends on `BookingRepository`, `ResourceRepository`,
  `UserRepository` and the event bus.
* `CampusFacade` depends on every service, the repositories and the observers.
* Route modules depend only on `CampusFacade` and the permission decorators.

---

## 12. Database tables and relationships

SQLite with `PRAGMA foreign_keys = ON`, CHECK constraints, UNIQUE keys and 16
indexes across 22 tables (`app/schema.sql`).

| Table | Key columns | Relationships |
| --- | --- | --- |
| `roles` | `id`, `name` UNIQUE | referenced by `users.role_id` |
| `users` | `id`, `username` UNIQUE, `email` UNIQUE | -> `roles` (RESTRICT) |
| `buildings` | `id`, `code` UNIQUE | referenced by `campus_resources` |
| `campus_resources` | `id`, `code` UNIQUE, `resource_type` | -> `buildings` (RESTRICT) |
| `classrooms` | `resource_id` PK/FK | -> `campus_resources` (CASCADE) |
| `laboratories` | `resource_id` PK/FK | -> `campus_resources` (CASCADE) |
| `parking_areas` | `resource_id` PK/FK | -> `campus_resources` (CASCADE) |
| `smart_devices` | `resource_id` PK/FK, `monitors_id` | -> `campus_resources` twice (CASCADE / SET NULL) |
| `equipment` | `id`, `code` UNIQUE | referenced by `resource_equipment` |
| `resource_equipment` | PK (`resource_id`, `equipment_id`), `condition` | -> `campus_resources`, `equipment` (CASCADE) |
| `bookings` | `id`, `reference` UNIQUE | -> `campus_resources`, `users`, `users` (approver) |
| `schedules` | `id`, UNIQUE(course, day, start, semester) | -> `users` (faculty), `campus_resources` |
| `enrollments` | UNIQUE(`student_id`, `schedule_id`) | -> `users`, `schedules` (CASCADE) |
| `attendance` | UNIQUE(`schedule_id`, `student_id`, `session_date`) | -> `schedules`, `users`, `users` (recorder) |
| `service_requests` | `id`, `ticket` UNIQUE | -> `campus_resources`, `users` (raiser, assignee) |
| `request_history` | `id`, `request_id` | -> `service_requests` (CASCADE), `users` |
| `iot_readings` | `id`, UNIQUE(`device_id`, `metric`, `recorded_at`) | -> `campus_resources` (device and monitored resource) |
| `alerts` | `id`, `status` | -> `iot_readings`, `campus_resources`, `service_requests`, `users` |
| `events` | `id`, `title` UNIQUE | -> `campus_resources` (venue), `users` (organiser) |
| `event_registrations` | UNIQUE(`event_id`, `user_id`) | -> `events`, `users` (CASCADE) |
| `notifications` | `id`, index on (`user_id`, `is_read`) | -> `users` (CASCADE) |
| `digital_services` | `id`, `code` UNIQUE | standalone catalogue |

Indexes: `idx_users_role`, `idx_resources_type`, `idx_resources_status`,
`idx_devices_monitors`, `idx_bookings_resource`, `idx_bookings_user`,
`idx_schedules_faculty`, `idx_attendance_student`, `idx_requests_status`,
`idx_requests_assignee`, `idx_requests_resource`, `idx_history_request`,
`idx_readings_device`, `idx_readings_metric`, `idx_alerts_status`,
`idx_notifications_user`.

Seeded demo campus (row counts after `manage.py seed`): 5 roles, 12 users,
4 buildings, 27 campus resources (8 classrooms, 4 laboratories, 3 parking areas,
12 smart devices), 10 equipment types, 43 equipment links, 6 bookings,
12 schedules, 33 enrolments, 99 attendance records, 7 service requests,
16 history entries, 35 IoT readings, 2 alerts, 5 events, 2 event registrations,
46 notifications, 6 digital services - **370 rows in total**.

---

## 13. API endpoint list

Page routes (HTML): `/`, `/login`, `/login/demo/<username>`, `/logout`,
`/dashboard`, `/schedule`, `/facilities`, `/recommendations`, `/bookings`,
`/requests`, `/maintenance`, `/iot`, `/security`, `/events`, `/admin`,
`/notifications`.

JSON API (all under `/api`):

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/api/health` | public | service check |
| GET | `/api/strategies` | any signed-in user | available ranking strategies |
| GET | `/api/dashboard` | any signed-in user | role dashboard payload |
| GET | `/api/resources` | SEARCH_RESOURCES | search resources |
| GET | `/api/resources/<id>` | SEARCH_RESOURCES | resource detail + calendar |
| POST | `/api/recommendations` | VIEW_RECOMMENDATIONS | ranked, explained suggestions |
| GET | `/api/bookings` | BOOK_RESOURCE | list bookings |
| POST | `/api/bookings` | BOOK_RESOURCE | create a booking |
| POST | `/api/bookings/<id>/cancel` | BOOK_RESOURCE | cancel a booking |
| POST | `/api/bookings/<id>/decision` | APPROVE_BOOKING | approve or reject |
| GET | `/api/requests` | TRACK_REQUEST | list requests (mine/assigned/all) |
| GET | `/api/requests/<id>` | TRACK_REQUEST | request detail with history |
| POST | `/api/requests` | SUBMIT_REQUEST | raise a request (auto-classified) |
| POST | `/api/requests/<id>/status` | UPDATE_REQUEST_STATUS | state transition |
| POST | `/api/requests/<id>/assign` | ASSIGN_REQUEST | assign to a technician |
| POST | `/api/equipment/condition` | UPDATE_EQUIPMENT | set equipment condition |
| GET | `/api/iot/snapshot` | VIEW_IOT | monitoring read model |
| GET | `/api/iot/readings` | VIEW_IOT | recent readings |
| POST | `/api/iot/readings` | VIEW_IOT | gateway ingestion endpoint |
| POST | `/api/alerts/<id>/acknowledge` | ACKNOWLEDGE_ALERT | acknowledge an alert |
| GET | `/api/parking` | MONITOR_PARKING | parking occupancy |
| GET | `/api/events` | VIEW_EVENTS | list events |
| POST | `/api/events` | MANAGE_EVENTS | publish an event |
| POST | `/api/events/<id>/register` | VIEW_EVENTS | register for an event |
| POST | `/api/events/<id>/cancel` | MANAGE_EVENTS | cancel an event |
| POST | `/api/attendance` | RECORD_ATTENDANCE | record attendance |
| GET | `/api/notifications` | any signed-in user | notification list |
| POST | `/api/notifications/<id>/read` | any signed-in user | mark one read |
| POST | `/api/notifications/read-all` | any signed-in user | mark all read |
| GET | `/api/admin/analytics` | VIEW_ANALYTICS | campus utilisation |
| GET/POST | `/api/admin/users` | MANAGE_USERS | list / create users |
| POST | `/api/admin/users/<id>/role` | MANAGE_USERS | change role |
| POST | `/api/admin/users/<id>/active` | MANAGE_USERS | activate / deactivate |
| POST | `/api/admin/resources` | MANAGE_RESOURCES | register a resource |
| POST | `/api/admin/resources/<id>/status` | MANAGE_RESOURCES | change resource status |
| GET | `/api/admin/technicians` | ASSIGN_REQUEST | assignable staff |
| GET | `/api/admin/seed-summary` | ADMIN role | row counts per table |

Errors are returned as `{"error": "<ExceptionName>", "message": "...", "details": {...}}`
with HTTP 400 (validation/capacity/equipment), 401 (authentication),
403 (permission), 404 (not found) or 409 (booking conflict, resource
unavailable, illegal state transition).

---

## 14. Step-by-step classroom recommendation and booking interaction

Sequence-diagram participants: `Student/Faculty` -> `Browser (recommendations.html)`
-> `api.recommend` -> `CampusFacade` -> `RecommendationService` ->
`ResourceRepository` / `BookingRepository` / `IoTRepository` ->
`WeightedRankingStrategy` -> back to the browser -> `api.create_booking` ->
`BookingService` -> `BookingRepository` -> `Subject` -> `NotificationObserver`.

1. The user opens **Smart recommendations** and enters attendees, time window,
   resource type, preferred building, required equipment and a ranking strategy.
2. The browser posts the criteria to `POST /api/recommendations`.
3. `CampusFacade.recommend_resources()` forwards to
   `RecommendationService.recommend()`, which first checks
   `VIEW_RECOMMENDATIONS` and validates the time window.
4. `RecommendationService.filter_candidates()` loads all bookable resources and
   applies the **hard constraints**, keeping a reason for every rejection:
   * resource status is not `AVAILABLE` -> rejected ("Not available - current status is maintenance")
   * `matches_capacity(attendees)` is false -> rejected ("Insufficient capacity - seats 30, 35 attendees requested")
   * `missing_equipment(required)` is non-empty -> rejected ("Missing required equipment: PROJECTOR")
   * an overlapping `PENDING`/`CONFIRMED` booking exists -> rejected ("Already booked during the requested slot (16:00-17:30)")
5. The surviving candidates are decorated with the latest IoT occupancy ratio.
6. The selected `RecommendationStrategy` scores each candidate on six normalised
   factors (capacity fit, equipment match, live occupancy, previous utilisation,
   walking distance, preferred building), each contributing `weight x value x 100`
   points. The score is the sum (0-100).
7. Results are sorted by score (ties broken by capacity, then code) and returned
   with `score`, `factors[]` (label, weight, value, points, explanation) and
   `reasons[]`.
8. The interface renders ranked cards with the score, the factor bars, the
   generated reasons, the capacity/equipment chips and a **Book** button, plus a
   panel listing every filtered-out resource and why.
9. Pressing **Book** posts to `POST /api/bookings` with the chosen resource and
   the same criteria.
10. `BookingService.create_booking()` re-validates everything server side:
    permission, resource exists, is bookable, is available, capacity, equipment,
    no time conflict, not in the past, purpose length, maximum 8 hours.
11. A student booking a laboratory or more than 30 attendees is stored as
    `PENDING` (administrator approval); every other booking is `CONFIRMED`.
12. `BookingRepository.add()` persists the row and assigns the reference `BK-#####`.
13. `Subject.notify(BOOKING_CREATED, ...)` reaches `NotificationObserver`, which
    writes a `Notification` for the booker (and for administrators when approval
    is required), and `AuditTrailObserver`, which records the event.
14. The browser shows a confirmation panel with the reference, resource, slot,
    attendees and status, and re-runs the search so the freshly booked room now
    appears in the *filtered out* list as a time conflict.

---

## 15. Step-by-step service-request workflow

1. A student, faculty member, administrator or security officer opens **Service
   requests**, picks the resource and describes the problem. Category and
   priority may be left on *detect automatically*.
2. `POST /api/requests` -> `CampusFacade.submit_service_request()` ->
   `MaintenanceService.submit_request()` checks `SUBMIT_REQUEST` and loads the
   resource.
3. `ServiceRequestFactory.create()` classifies the text:
   * safety keywords (fire, smoke, gas, spark, hazard, ...) -> `SafetyRequest`
   * IT keywords (projector, network, computer, printer, ...) -> `ITSupportRequest`
   * cleaning keywords (clean, waste, spill, ...) -> `HousekeepingRequest`
   * otherwise -> `MaintenanceRequest`
   Base priority comes from the category (safety HIGH, IT/maintenance MEDIUM,
   housekeeping LOW) and is raised one level by escalation words
   ("urgent", "not working", "broken", "danger", ...); an escalated safety issue
   becomes `CRITICAL`. The SLA hours come from the concrete subclass's
   `SLA_MATRIX`, and `sla_due_at = created_at + sla_hours`.
4. `ServiceRequestRepository.add()` stores the ticket (`SR-#####`) and the first
   history entry (`NEW`).
5. `Subject.notify(REQUEST_CREATED, ...)` notifies the reporter and every
   administrator.
6. The administrator assigns the ticket:
   `POST /api/requests/<id>/assign` -> `MaintenanceService.assign_request()`
   validates that the assignee is maintenance staff, calls
   `ServiceRequest.assign()` (which performs `NEW -> ASSIGNED`), writes a history
   entry and notifies the technician and the reporter.
7. The technician works the queue on **Maintenance workspace**. Only transitions
   allowed by `ALLOWED_TRANSITIONS` are offered as buttons:
   `NEW -> ASSIGNED | REJECTED`, `ASSIGNED -> IN_PROGRESS | REJECTED`,
   `IN_PROGRESS -> RESOLVED`, `RESOLVED -> CLOSED | IN_PROGRESS` (reopen),
   `CLOSED`/`REJECTED` are terminal. An illegal transition raises
   `InvalidTransitionError` (HTTP 409).
8. Every transition writes a `request_history` row (from-status, to-status, note,
   actor, timestamp) and notifies the reporter and the assignee.
9. `sla_state()` reports `ON_TRACK`, `AT_RISK` (within the last 25 % of the SLA),
   `BREACHED`, or `MET` / `MISSED` once the ticket is resolved or closed; the
   administrator dashboard aggregates these counts.

---

## 16. Step-by-step IoT-alert workflow

1. The IoT gateway posts a reading to `POST /api/iot/readings`
   (`device_id`, `metric`, `value`, optional `recorded_at`). The IoT monitoring
   screen contains a gateway simulator that uses the same endpoint.
2. `IoTService.record_reading()` validates the metric and value, confirms the
   device is a `SmartDevice`, and resolves the monitored resource through
   `SmartDevice.monitors_id`.
3. An `IoTReading` is constructed; its constructor calls
   `IoTReading.classify(metric, value)` to derive `NORMAL`, `WARNING` or
   `CRITICAL` from the threshold table.
4. `IoTRepository.add_reading()` stores the reading (the UNIQUE
   `(device_id, metric, recorded_at)` triple makes re-ingestion idempotent).
5. Side effects: a parking reading updates `parking_areas.occupied_slots`; a
   device-status reading of 0 marks the device offline.
6. `IOT_READING_RECORDED` is published to the observer bus.
7. If the reading is **not** critical, processing stops here.
8. If it **is** critical, the service first checks `AlertRepository.open_for()`:
   when an alert for the same resource and metric is still open, the duplicate is
   suppressed (`duplicate_suppressed: true`) so one physical fault produces one
   ticket.
9. Otherwise `MaintenanceService.create_automatic_request()` calls
   `ServiceRequestFactory.create_from_reading()`, which maps the metric to a
   category (air quality/occupancy -> `SAFETY`, temperature -> `MAINTENANCE`,
   equipment/device status -> `IT_SUPPORT`), forces `CRITICAL` priority, sets
   `source = IOT` and writes a descriptive title and description.
10. The ticket is auto-assigned to the maintenance technician with the fewest open
    tickets, moving it to `ASSIGNED`.
11. `Subject.notify(IOT_CRITICAL_ALERT, ...)` reaches `AlertObserver`, which
    inserts the alert row, and `NotificationObserver`, which notifies every
    security officer, every administrator and the assigned technician. The alert
    is then linked to the ticket.
12. Security personnel see the alert on **Security operations** / **IoT
    monitoring** and acknowledge it (`POST /api/alerts/<id>/acknowledge`), which
    records the acknowledging officer and the timestamp.

---

## 17. Application packages/modules and their dependencies

```
routes  ──▶ services ──▶ repositories ──▶ sqlite3
   │           │   │            │
   │           │   └──▶ patterns │
   │           └──▶ domain ◀─────┘
   └──▶ security ──▶ services
templates/static ◀── routes
```

| Package | Depends on | Never depends on |
| --- | --- | --- |
| `app.domain` | `app.exceptions`, `app.utils` | Flask, sqlite3, repositories |
| `app.patterns` | `app.domain`, `app.exceptions`, `app.utils` | Flask, sqlite3 |
| `app.repositories` | `app.domain`, `app.exceptions`, `sqlite3` | Flask, services |
| `app.services` | `app.domain`, `app.patterns`, `app.repositories` | Flask request context |
| `app.routes` | `app.services` (via `CampusFacade`), `app.security` | repositories directly for writes |
| `app.security` | `app.services`, `app.database`, Flask | domain internals |

This layering is the package diagram: **Presentation → Application services →
Domain ← Patterns**, with **Repositories** as the only bridge to persistence.

---

## 18. Runtime components

| Component | Description |
| --- | --- |
| Flask application (`create_app`) | HTTP server, blueprints `auth`, `views`, `api` |
| Jinja2 template engine | server-side rendering of 20 templates |
| Static assets | `styles.css` (single stylesheet), `app.js` (fetch helpers, toasts, generic JSON forms) |
| `CampusFacade` | per-request coordinator wired to one SQLite connection |
| Observer bus (`Subject`) | in-process publish/subscribe with three observers |
| Repository layer | ten repositories over one `sqlite3.Connection` |
| SQLite database file | `instance/aiscams.db`, created and seeded automatically |
| Pytest suite | 170 tests using an isolated copy of a seeded template database |

---

## 19. Deployment architecture

Single-node local deployment:

```
┌────────────────────────── Client device ──────────────────────────┐
│  Web browser (Chrome/Edge/Firefox) - HTML + CSS + vanilla JS      │
└───────────────────────────────┬───────────────────────────────────┘
                                │ HTTP (127.0.0.1:5000)
┌───────────────────────────────▼───────────────────────────────────┐
│  Windows/Linux host - Python 3.11 virtual environment             │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Flask application (Werkzeug development server, run.py)      │  │
│  │  routes → services → repositories → sqlite3                 │  │
│  └──────────────────────────────┬──────────────────────────────┘  │
│                                 │ file I/O                        │
│                    instance/aiscams.db (SQLite file)              │
└───────────────────────────────────────────────────────────────────┘
        ▲
        │ HTTP POST /api/iot/readings
┌───────┴────────────────────────────────────────────────────────────┐
│  IoT gateway / smart devices (external system actor)               │
└────────────────────────────────────────────────────────────────────┘
```

For a production deployment the same artefact would run behind a WSGI server
(e.g. Waitress or Gunicorn) with the SQLite file replaced by a networked
database; nothing in the domain or service layer would change, because
persistence is isolated in the repository layer.

---

## 20. Design patterns genuinely implemented

| Pattern | Classes involved | Where it is used at runtime |
| --- | --- | --- |
| **Strategy** | `RecommendationStrategy` (abstract), `WeightedRankingStrategy`, `ProximityFirstStrategy`, `UtilisationBalancingStrategy`, `RecommendationCriteria`, `Candidate`, `ScoredRecommendation`, `get_strategy()` | `RecommendationService.recommend()` selects a strategy by key; the user can switch strategy in the interface and the ranking changes without touching the service |
| **Factory** | `ServiceRequestFactory` with `create()`, `create_from_reading()`, `classify_category()`, `classify_priority()`, `rebuild()`; products `MaintenanceRequest`, `SafetyRequest`, `ITSupportRequest`, `HousekeepingRequest` | every user-submitted request and every automatic IoT ticket |
| **Observer** | `Subject`, `Observer` (abstract), `NotificationObserver`, `AlertObserver`, `AuditTrailObserver`; events `BOOKING_CREATED`, `BOOKING_APPROVED`, `BOOKING_REJECTED`, `BOOKING_CANCELLED`, `REQUEST_CREATED`, `REQUEST_ASSIGNED`, `REQUEST_STATUS_CHANGED`, `IOT_READING_RECORDED`, `IOT_CRITICAL_ALERT` | booking confirmations, request-status updates, critical IoT alerts |
| **Repository** | `BaseRepository` + `UserRepository`, `ResourceRepository`, `BookingRepository`, `ServiceRequestRepository`, `ScheduleRepository`, `IoTRepository`, `AlertRepository`, `EventRepository`, `NotificationRepository`, `DigitalServiceRepository`, aggregated by `RepositoryRegistry` | all persistence; the domain layer contains no SQL |
| **Facade** | `CampusFacade` | the single entry point used by every route: `recommend_resources`, `book_resource`, `recommend_and_book`, `submit_service_request`, `assign_request`, `advance_request`, `ingest_reading`, `dashboard_for` |

Supporting OOAD qualities:

* **Encapsulation** - domain attributes are private with read-only properties;
  mutation happens only through intention-revealing methods
  (`transition_to`, `update_occupancy`, `set_equipment_condition`).
* **Abstraction** - `User`, `CampusResource`, `ServiceRequest`,
  `RecommendationStrategy` and `Observer` are ABCs; instantiating them raises
  `TypeError` (covered by tests).
* **Inheritance / polymorphism** - see sections 9 and 10.
* **High cohesion** - one aggregate per repository, one workflow per service.
* **Low coupling** - the domain layer imports neither Flask nor sqlite3.
* **Responsibility assignment** - validation lives in the entity that owns the
  rule; cross-entity rules live in the services; the facade only coordinates.
* **Input validation** - `app/utils.py` validators plus entity constructors plus
  SQL CHECK constraints (three layers).
* **Exception handling** - `AiscamsError` hierarchy carries HTTP status codes and
  is translated centrally in `app/__init__.py`.

---

## 21. Assumptions and limitations

1. The recommendation engine is an **explainable weighted-ranking strategy**, not
   a trained machine-learning model. Weights are fixed constants defined in code.
2. "Live occupancy" comes from the most recent stored `OCCUPANCY` reading; when a
   room has no reading, a neutral value of 0.5 is used and the reason text says so.
3. Historical utilisation is a seeded per-resource attribute; it is not recomputed
   from booking history.
4. The IoT gateway is simulated: readings arrive through the same REST endpoint a
   real gateway would use, either from seeding or from the simulator panel on the
   IoT monitoring screen. No physical hardware or MQTT broker is involved.
5. Authentication is session-cookie based with hashed passwords. There is no
   password reset, e-mail delivery, two-factor authentication or account lockout.
6. Notifications are stored in the database and shown in the notification centre;
   no e-mail, SMS or push delivery exists.
7. Bookings are limited to 8 hours and cannot start before today; recurring
   bookings are not supported.
8. Attendance is recorded per student per session date; bulk import and
   biometric capture are out of scope.
9. Times are naive local timestamps (`YYYY-MM-DD HH:MM:SS`); the system is
   single-campus and single-timezone.
10. The application runs on the Flask development server for the demonstration;
    it is not hardened for production traffic (no HTTPS, CSRF tokens or rate
    limiting).
11. SQLite is single-writer; the design targets a demonstration workload, not
    concurrent campus-wide load.
12. Demo passwords are deliberately simple and identical across seeded accounts.

---

## 22. Requirement-to-feature mapping

| Requirement (assignment brief) | Implemented feature | Where |
| --- | --- | --- |
| Role-based interfaces for five actors | five `User` subclasses, permission-filtered navigation, five dashboards | `domain/users.py`, `security.py`, `templates/dashboards/` |
| Student: dashboard, schedule, facilities, recommendations, booking, events, digital services, requests, tracking, notifications | all implemented | `routes/views.py`, `routes/api.py` |
| Faculty: schedules, attendance, classroom search/booking, capacity & equipment requirements, recommendations, issue reporting, academic activities | all implemented | `schedule.html`, `api.record_attendance`, `recommendations.html` |
| Administrator: users/roles, resources, approvals, analytics, events, assignment, SLA monitoring | all implemented | `admin.html`, `dashboards/admin.html`, `AnalyticsService` |
| Security: parking occupancy, alerts, IoT readings, acknowledgement | all implemented | `dashboards/security.html`, `IoTService` |
| Maintenance: assigned queue, status updates, equipment condition, priority/SLA, in-progress/resolved/closed | all implemented | `maintenance.html`, `MaintenanceService` |
| IoT monitoring of occupancy, temperature, air quality, equipment status, parking, device status | six metrics with thresholds, stored in `iot_readings` | `domain/iot.py`, `iot.html` |
| Critical reading raises a high-priority/critical request automatically | `IoTService.record_reading()` -> `ServiceRequestFactory.create_from_reading()` | section 16 |
| Intelligent recommendations using availability, capacity, equipment, occupancy, utilisation, preferred building, walking distance | six scoring factors + four hard filters | `patterns/strategy.py`, `services/recommendation_service.py` |
| Interface shows ranked results, score, reasons, capacity/equipment, working booking action | recommendation cards with factor bars and Book button | `templates/recommendations.html` |
| Unavailable / undersized / unequipped / conflicting resources filtered or rejected | `filter_candidates()` + server-side re-validation in `BookingService` | sections 14 and 21 |
| Encapsulation, abstraction, inheritance, polymorphism, cohesion, coupling, responsibility assignment, validation, exception handling | see section 20 | whole codebase |
| Strategy, Factory, Observer, Repository, Facade patterns | see section 20 | `patterns/`, `repositories/`, `services/` |
| SQLite with constraints, relationships, indexes, idempotent seed | 22 tables, foreign keys, CHECK constraints, 16 indexes, idempotent `seed_database()` | `app/schema.sql`, `app/seed.py` |
| Polished responsive UI with metric cards, badges, confirmations, empty states | single stylesheet with a documented palette, responsive down to mobile widths | `app/static/css/styles.css` |
| At least 30 meaningful Pytest tests | 170 tests | `tests/` |

---

## 23. Screenshot index

All screenshots were taken from the running application (Chromium at a
1440x1000 viewport) and from a real terminal session; none of them is edited.

| File | Caption |
| --- | --- |
| `docs/screenshots/01_student_dashboard.png` | Student dashboard of Athisaya U showing the seeded campus data: classes today, 85 % attendance, upcoming booking BK-00004, open service request SR-00004, upcoming events, digital services and recent notifications. |
| `docs/screenshots/02_smart_resource_recommendations.png` | Smart resource recommendation screen: five of eight resources satisfy the constraints, each ranked card shows its score out of 100, the six weighted factors and the generated reasons, while the right-hand panel lists every filtered-out room with the reason (maintenance status, insufficient capacity, missing projector, booking clash). |
| `docs/screenshots/03_successful_booking.png` | Successful booking confirmation after pressing "Book" on the top recommendation: reference BK-00007 with status CONFIRMED, resource SB-202, the reserved slot, the attendee count, and the re-ranked list in which SB-202 is now filtered out because of the new time conflict. |
| `docs/screenshots/04_service_request_created.png` | Service request SR-00008 created from a free-text report and classified automatically as IT support / HIGH priority with a 6-hour SLA, a due timestamp and status NEW, together with the tracking table below. |
| `docs/screenshots/05_iot_monitoring.png` | IoT campus monitoring showing 12 of 12 devices online and live readings grouped by metric: room occupancy, temperature (warning at 31.5 C), air quality index (critical 268 AQI in the chemistry laboratory) and equipment status (failed monitor in EB-301). |
| `docs/screenshots/06_maintenance_workflow.png` | Maintenance workspace of technician Mohan Das after moving a ticket to In progress: the queue shows priority, status, SLA state and the expanded status history (New → Assigned → In progress) with actor and timestamp, plus the only legal next transition. |
| `docs/screenshots/07_administrator_dashboard.png` | Administrator dashboard with operational metrics (27 campus resources, 21 % average utilisation, pending approvals, 7 open requests of which 2 breach the SLA) above the full service-request table with category, priority, status, SLA state, assignee and the assignment control. |
| `docs/screenshots/08_all_tests_passed.png` | Terminal session in the project folder running `.venv\Scripts\python.exe -m pytest`: 170 items collected, every test file green, and the final summary `170 passed in 21.07s`. |

---

## 24. Exact number of passing tests

**170 tests, 170 passing, 0 failing.**

| Test module | Tests | Coverage area |
| --- | --- | --- |
| `test_api_and_access.py` | 32 | authentication, role-based page access, API success responses, API validation errors, 401/403/404/409 handling |
| `test_service_requests.py` | 22 | factory classification, priority rules, SLA matrix, valid and invalid state transitions, assignment rules, history |
| `test_repositories_and_database.py` | 21 | repository operations, foreign keys, CHECK/UNIQUE constraints, indexes, idempotent seeding |
| `test_iot_and_alerts.py` | 20 | threshold classification, normal/warning/critical readings, automatic ticket creation, duplicate suppression, parking side effects, acknowledgement |
| `test_bookings.py` | 18 | booking creation, conflict prevention, capacity, equipment, unavailable resources, approval workflow, cancellation |
| `test_observer_and_dashboards.py` | 18 | observer attach/detach/notify, notification delivery, audit trail, dashboard calculations per role |
| `test_recommendations.py` | 16 | hard filtering, scoring, ranking order, strategy swapping, weight validation |
| `test_resources.py` | 12 | resource abstraction, polymorphic behaviour, capacity and equipment rules, validation |
| `test_users_and_roles.py` | 11 | abstract base class, inheritance, polymorphic permissions, encapsulation, validation |

The captured console output of a real run is `docs/test_results.txt`.

---

## 25. Commands required to reproduce the screenshots

```bat
:: fresh state
.venv\Scripts\python.exe manage.py reset
.venv\Scripts\python.exe run.py
```

Then, in a browser window sized to 1440x1000, at <http://127.0.0.1:5000>:

| Screenshot | Steps |
| --- | --- |
| 01 | Sign in as `athisaya` / `campus123` - the student dashboard is the landing page. |
| 02 | Open **Smart recommendations**. The page runs the search on load with 35 attendees, a one-hour slot and PROJECTOR required; scroll to the ranked results. |
| 03 | On the same page set attendees to 24, press **Get recommendations**, then press **Book <code>** on the first card. |
| 04 | Open **Service requests**, keep the pre-filled projector fault (or type your own), leave category and priority on *detect automatically* and press **Submit request**. |
| 05 | Sign out, sign in as `security.ravi` / `campus123` and open **IoT monitoring**. |
| 06 | Sign in as `tech.mohan` / `campus123`, open **Maintenance workspace**, press **Start work** on an assigned ticket and expand the **History** sections. |
| 07 | Sign in as `campus.admin` / `campus123` - the administrator dashboard is the landing page. |
| 08 | In a terminal in the project folder run `.venv\Scripts\python.exe -m pytest`. |
