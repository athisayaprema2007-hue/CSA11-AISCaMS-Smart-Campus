# AISCaMS - AI-Enabled Smart Campus Management System

A working, offline, role-based smart campus platform built with **Python, Flask,
SQLite, HTML, CSS and vanilla JavaScript**. It integrates academic, administrative,
infrastructure and student-support services behind one interface, monitors campus
IoT devices, and suggests classrooms and laboratories with an **explainable
weighted-ranking recommendation strategy**.

> The recommendation engine is **not** a trained machine-learning model. It is a
> transparent, rule-based weighted-ranking strategy: every score shown in the
> interface is the sum of clearly labelled factor contributions, and the reasons
> displayed are generated from exactly those numbers.

Course: Object Oriented Analysis and Design (CSA11)
Student: Athisaya U - Registration number 192571001

---

## Submission files

| Deliverable | File |
| --- | --- |
| Final assignment PDF | [`docs/report/Athisaya_U_CSA11_CO1-CO3_Assignment_AISCaMS.pdf`](docs/report/Athisaya_U_CSA11_CO1-CO3_Assignment_AISCaMS.pdf) |
| Editable Word report | [`docs/report/Athisaya_U_CSA11_CO1-CO3_Assignment_AISCaMS.docx`](docs/report/Athisaya_U_CSA11_CO1-CO3_Assignment_AISCaMS.docx) |
| UML evidence | [`docs/uml/`](docs/uml/) - ten black-and-white Umbrello exports |
| Prototype evidence | [`docs/screenshots/`](docs/screenshots/) - seven application screens and the complete test run |

The PDF is the submission-ready report. It retains the supplied assignment front
matter and assessment rubric, contains 50 A4 pages, and traces the requirements
to use cases, classes, implementation entry points, screenshots and automated
verification evidence.

---

## 1. Quick start (Windows)

Double-click **`run.bat`**. It creates a virtual environment, installs the
dependencies, creates and seeds the database, and starts the application at
<http://127.0.0.1:5000>.

### Manual setup

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py seed
.venv\Scripts\python.exe run.py
```

Then open <http://127.0.0.1:5000>.

### Running the tests

```bat
.venv\Scripts\python.exe -m pytest
```

The full suite contains **170 tests** and passes in about 20-25 seconds.
The captured output of a real run is stored in `docs/test_results.txt`.

### Database commands

| Command | Effect |
| --- | --- |
| `python manage.py init-db` | create the schema only |
| `python manage.py seed` | create the schema and insert the demo campus (idempotent) |
| `python manage.py summary` | print the row count of every table |
| `python manage.py reset` | delete the database file and rebuild it from scratch |

The database file is created automatically at `instance/aiscams.db` the first
time the application starts, so no manual migration step is needed.

---

## 2. Demo accounts

Every seeded account uses the password **`campus123`**. The sign-in screen also
offers one-click demo role selection.

| Username | Name | Role |
| --- | --- | --- |
| `athisaya` | Athisaya U | Student |
| `dr.kavitha` | Dr. Kavitha Raman | Faculty member |
| `campus.admin` | Vikram Rao | Administrator |
| `security.ravi` | Ravi Shankar | Security personnel |
| `tech.mohan` | Mohan Das | Maintenance staff |

Additional seeded accounts: `rahul.k`, `meera.s`, `arjun.p` (students),
`dr.suresh`, `dr.priya` (faculty), `security.latha`, `tech.arun`.

---

## 3. What the system does

**Student** - personal dashboard, weekly timetable, facility search, explainable
resource recommendations, room booking, campus events, digital campus services,
service requests with tracking, and notifications.

**Faculty** - teaching timetable, attendance recording per session, classroom
search and booking with capacity/equipment requirements, recommendations, issue
reporting and academic activity overview.

**Administrator** - user and role management, campus resource management, booking
approval, campus utilisation analytics, event management, service-request
assignment and SLA monitoring.

**Security personnel** - live parking occupancy, infrastructure and safety alerts,
IoT readings, and alert acknowledgement.

**Maintenance staff** - assigned request queue with priority and SLA information,
status workflow (assigned -> in progress -> resolved -> closed) and equipment
condition updates.

**IoT gateway (external system)** - publishes readings for room occupancy,
temperature, air quality, equipment status, parking occupancy and device health.
A critical reading automatically raises an alert **and** a critical-priority
maintenance or safety ticket, which is auto-assigned to the least loaded
technician.

---

## 4. Architecture

```
app/
├── domain/          entities and business rules (no Flask, no SQL)
├── patterns/        Strategy, Factory and Observer implementations
├── repositories/    the only layer that speaks SQL (Repository pattern)
├── services/        use-case coordination + CampusFacade (Facade pattern)
├── routes/          HTML pages, authentication and the JSON API
├── templates/       Jinja2 templates
├── static/          stylesheet and vanilla JavaScript
├── schema.sql       SQLite schema with constraints and indexes
└── seed.py          deterministic, idempotent demo data
```

Design patterns actually used:

| Pattern | Where | What it solves |
| --- | --- | --- |
| Strategy | `app/patterns/strategy.py` | interchangeable, explainable ranking policies |
| Factory | `app/patterns/factory.py` | classifying a report into the right `ServiceRequest` subclass with priority and SLA |
| Observer | `app/patterns/observer.py` | booking, request-status and alert notifications |
| Repository | `app/repositories/` | database access isolated from the domain |
| Facade | `app/services/campus_facade.py` | one entry point for the campus workflows |

---

## 5. Project layout

```
AISCaMS/
├── app/                    application package (see above)
├── tests/                  170 Pytest tests
├── docs/
│   ├── IMPLEMENTATION_HANDOFF.md
│   ├── test_results.txt
│   ├── report/             final PDF and editable Word assignment
│   ├── screenshots/        eight screenshots of the running system
│   └── uml/                ten Umbrello UML evidence exports
├── instance/               SQLite database (created at runtime)
├── manage.py               database CLI
├── run.py                  development entry point
├── run.bat                 one-click Windows setup and start
├── requirements.txt
└── README.md
```

---

## 6. Notes

* The application runs entirely locally: no paid services, API keys, cloud
  accounts or external databases are required.
* Seeding is idempotent - running `manage.py seed` repeatedly never duplicates a
  record.
* Demo passwords are intentionally simple because the system is a local
  academic prototype; passwords are still stored only as salted hashes.
