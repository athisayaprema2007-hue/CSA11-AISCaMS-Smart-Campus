"""Deterministic and idempotent demo data.

Running the seeding process more than once never duplicates a record: every
insert is guarded by a natural key (username, resource code, event title,
ticket subject, or the unique IoT (device, metric, timestamp) triple).
"""

from datetime import datetime, timedelta

from .config import BaseConfig
from .database import init_schema
from .domain.booking import STATUS_COMPLETED, STATUS_CONFIRMED, STATUS_PENDING
from .services.campus_facade import CampusFacade
from .utils import to_db

DEMO_PASSWORD = BaseConfig.DEMO_PASSWORD
SEMESTER = "2026-ODD"

ROLES = [
    ("STUDENT", "Learner enrolled in campus programmes"),
    ("FACULTY", "Teaching staff managing classes and attendance"),
    ("ADMIN", "Campus administrator with full oversight"),
    ("SECURITY", "Security personnel monitoring campus safety"),
    ("MAINTENANCE", "Technician resolving service requests"),
]

BUILDINGS = [
    ("MB", "Main Block", 60),
    ("SB", "Science Block", 180),
    ("EB", "Engineering Block", 300),
    ("IH", "Innovation Hub", 450),
]

EQUIPMENT = [
    ("PROJECTOR", "Ceiling projector"),
    ("SMART_BOARD", "Interactive smart board"),
    ("AC", "Air conditioning"),
    ("WIFI6", "Wi-Fi 6 access point"),
    ("MIC", "Public address microphone"),
    ("VIDEO_CONF", "Video conferencing kit"),
    ("POWER_BACKUP", "Uninterrupted power supply"),
    ("LAB_PC", "Laboratory workstation"),
    ("OSCILLOSCOPE", "Digital oscilloscope"),
    ("FUME_HOOD", "Chemical fume hood"),
]

USERS = [
    # username, full name, email, role, department, phone
    ("athisaya", "Athisaya U", "athisaya@aiscams.edu", "STUDENT",
     "Computer Science and Engineering", "+91-90000-10001"),
    ("rahul.k", "Rahul Krishnan", "rahul.k@aiscams.edu", "STUDENT",
     "Computer Science and Engineering", "+91-90000-10002"),
    ("meera.s", "Meera Sundaram", "meera.s@aiscams.edu", "STUDENT",
     "Electronics and Communication", "+91-90000-10003"),
    ("arjun.p", "Arjun Prakash", "arjun.p@aiscams.edu", "STUDENT",
     "Computer Science and Engineering", "+91-90000-10004"),
    ("dr.kavitha", "Dr. Kavitha Raman", "kavitha.r@aiscams.edu", "FACULTY",
     "Computer Science and Engineering", "+91-90000-20001"),
    ("dr.suresh", "Dr. Suresh Menon", "suresh.m@aiscams.edu", "FACULTY",
     "Electronics and Communication", "+91-90000-20002"),
    ("dr.priya", "Dr. Priya Nair", "priya.n@aiscams.edu", "FACULTY",
     "Applied Chemistry", "+91-90000-20003"),
    ("campus.admin", "Vikram Rao", "vikram.rao@aiscams.edu", "ADMIN",
     "Campus Administration", "+91-90000-30001"),
    ("security.ravi", "Ravi Shankar", "ravi.s@aiscams.edu", "SECURITY",
     "Campus Security", "+91-90000-40001"),
    ("security.latha", "Latha Devi", "latha.d@aiscams.edu", "SECURITY",
     "Campus Security", "+91-90000-40002"),
    ("tech.mohan", "Mohan Das", "mohan.d@aiscams.edu", "MAINTENANCE",
     "Electrical and IT Facilities", "+91-90000-50001"),
    ("tech.arun", "Arun Kumar", "arun.k@aiscams.edu", "MAINTENANCE",
     "Civil and HVAC Facilities", "+91-90000-50002"),
]

CLASSROOMS = [
    # code, name, building, floor, capacity, utilisation, status, seating, equipment
    ("CR-101", "Lecture Hall A", "MB", 1, 60, 0.72, "AVAILABLE", "TIERED",
     ["PROJECTOR", "AC", "WIFI6", "MIC"]),
    ("CR-102", "Lecture Hall B", "MB", 1, 45, 0.55, "MAINTENANCE", "FIXED",
     ["PROJECTOR", "AC", "WIFI6"]),
    ("CR-201", "Seminar Room 201", "MB", 2, 30, 0.41, "AVAILABLE", "MOVABLE",
     ["SMART_BOARD", "AC", "WIFI6"]),
    ("CR-202", "Seminar Room 202", "MB", 2, 24, 0.28, "AVAILABLE", "MOVABLE",
     ["WIFI6"]),
    ("SB-101", "Science Hall 1", "SB", 1, 80, 0.63, "AVAILABLE", "TIERED",
     ["PROJECTOR", "AC", "WIFI6", "MIC", "VIDEO_CONF"]),
    ("SB-202", "Tutorial Room 202", "SB", 2, 35, 0.35, "AVAILABLE", "FIXED",
     ["PROJECTOR", "WIFI6"]),
    ("EB-301", "Engineering Hall", "EB", 3, 100, 0.58, "AVAILABLE", "TIERED",
     ["PROJECTOR", "AC", "WIFI6", "MIC", "POWER_BACKUP"]),
    ("IH-101", "Innovation Studio", "IH", 1, 40, 0.22, "AVAILABLE", "MOVABLE",
     ["PROJECTOR", "SMART_BOARD", "VIDEO_CONF", "AC", "WIFI6"]),
]

LABORATORIES = [
    # code, name, building, floor, capacity, utilisation, lab type, safety, stations, equipment
    ("LB-CS1", "Computing Laboratory 1", "EB", 1, 60, 0.68, "COMPUTING", "STANDARD", 40,
     ["LAB_PC", "PROJECTOR", "AC", "WIFI6", "POWER_BACKUP"]),
    ("LB-CS2", "Computing Laboratory 2", "EB", 2, 45, 0.44, "COMPUTING", "STANDARD", 35,
     ["LAB_PC", "AC", "WIFI6"]),
    ("LB-EL1", "Electronics Laboratory", "SB", 1, 30, 0.51, "ELECTRONICS", "HIGH", 25,
     ["OSCILLOSCOPE", "LAB_PC", "POWER_BACKUP", "WIFI6"]),
    ("LB-CH1", "Chemistry Laboratory", "SB", 2, 30, 0.39, "CHEMISTRY", "HIGH", 24,
     ["FUME_HOOD", "AC", "WIFI6"]),
]

PARKING = [
    # code, name, building, zone, total, occupied
    ("PK-A", "Main Gate Parking", "MB", "A", 120, 92),
    ("PK-B", "Staff Parking", "EB", "B", 60, 41),
    ("PK-C", "Visitor Parking", "IH", "C", 40, 12),
]

DEVICES = [
    # code, name, building, device type, monitored resource code
    ("IOT-OCC-101", "Occupancy Sensor CR-101", "MB", "OCCUPANCY_SENSOR", "CR-101"),
    ("IOT-OCC-201", "Occupancy Sensor CR-201", "MB", "OCCUPANCY_SENSOR", "CR-201"),
    ("IOT-OCC-SB1", "Occupancy Sensor SB-101", "SB", "OCCUPANCY_SENSOR", "SB-101"),
    ("IOT-OCC-IH1", "Occupancy Sensor IH-101", "IH", "OCCUPANCY_SENSOR", "IH-101"),
    ("IOT-CLI-101", "Climate Sensor CR-101", "MB", "CLIMATE_SENSOR", "CR-101"),
    ("IOT-CLI-CS1", "Climate Sensor LB-CS1", "EB", "CLIMATE_SENSOR", "LB-CS1"),
    ("IOT-AIR-101", "Air Quality Sensor CR-101", "MB", "AIR_QUALITY_SENSOR", "CR-101"),
    ("IOT-AIR-CH1", "Air Quality Sensor LB-CH1", "SB", "AIR_QUALITY_SENSOR", "LB-CH1"),
    ("IOT-PRK-A", "Parking Sensor Zone A", "MB", "PARKING_SENSOR", "PK-A"),
    ("IOT-PRK-B", "Parking Sensor Zone B", "EB", "PARKING_SENSOR", "PK-B"),
    ("IOT-EQP-CS1", "Equipment Monitor LB-CS1", "EB", "EQUIPMENT_MONITOR", "LB-CS1"),
    ("IOT-EQP-301", "Equipment Monitor EB-301", "EB", "EQUIPMENT_MONITOR", "EB-301"),
]

SCHEDULES = [
    # course code, title, faculty, resource, day, start, end
    ("CSA11", "Object Oriented Analysis and Design", "dr.kavitha", "CR-101", "MON", "09:00", "10:30"),
    ("CSA15", "Cloud Computing", "dr.suresh", "EB-301", "MON", "14:00", "15:30"),
    ("CSA12", "Data Structures Laboratory", "dr.kavitha", "LB-CS1", "TUE", "11:00", "12:30"),
    ("ECA22", "Signals and Systems", "dr.suresh", "SB-202", "TUE", "14:00", "15:30"),
    ("CSA11", "Object Oriented Analysis and Design", "dr.kavitha", "CR-101", "WED", "09:00", "10:30"),
    ("CSA13", "Database Management Systems", "dr.suresh", "CR-201", "WED", "11:00", "12:30"),
    ("CSA16", "Web Technologies", "dr.kavitha", "IH-101", "WED", "14:00", "15:30"),
    ("ECA21", "Digital Electronics Laboratory", "dr.suresh", "LB-EL1", "THU", "09:00", "11:00"),
    ("CSA14", "Software Engineering", "dr.kavitha", "SB-101", "THU", "14:00", "15:30"),
    ("CHA10", "Applied Chemistry Laboratory", "dr.priya", "LB-CH1", "FRI", "14:00", "16:00"),
    ("CSA17", "Mini Project Review", "dr.kavitha", "IH-101", "FRI", "10:00", "11:30"),
    ("CSA14", "Software Engineering", "dr.kavitha", "SB-101", "SAT", "09:00", "10:30"),
]

#: Students enrolled in each course code.
ENROLMENTS = {
    "CSA11": ["athisaya", "rahul.k", "arjun.p", "meera.s"],
    "CSA12": ["athisaya", "rahul.k", "arjun.p"],
    "CSA13": ["athisaya", "rahul.k", "arjun.p"],
    "CSA14": ["athisaya", "rahul.k", "arjun.p", "meera.s"],
    "CSA15": ["athisaya", "arjun.p"],
    "CSA16": ["athisaya", "rahul.k"],
    "CSA17": ["athisaya", "rahul.k", "arjun.p"],
    "ECA21": ["meera.s"],
    "ECA22": ["meera.s"],
    "CHA10": ["meera.s", "arjun.p"],
}

DIGITAL_SERVICES = [
    ("LIB", "Library portal", "Search the catalogue, reserve books and renew loans.",
     "Academic", True),
    ("FEE", "Fee payment", "View invoices and pay semester fees online.", "Finance", True),
    ("HOSTEL", "Hostel services", "Room allocation, mess menu and leave requests.",
     "Residential", True),
    ("TRANSPORT", "Transport tracker", "Live campus shuttle timings and route map.",
     "Transport", True),
    ("CERT", "e-Certificate requests", "Apply for bonafide, transcript and conduct certificates.",
     "Administration", True),
    ("HEALTH", "Health centre appointments", "Book a slot with the campus medical centre.",
     "Wellbeing", False),
]


# ---------------------------------------------------------------- helpers
def _midnight(reference=None):
    base = reference or datetime.now()
    return base.replace(hour=0, minute=0, second=0, microsecond=0)


def _at(day_offset, hour, minute=0, reference=None):
    return _midnight(reference) + timedelta(days=day_offset, hours=hour, minutes=minute)


def _past_sessions(day_code, count, reference=None):
    """The last `count` dates (YYYY-MM-DD) matching a weekday, before today."""
    order = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
    target = order.index(day_code)
    cursor = _midnight(reference) - timedelta(days=1)
    dates = []
    while len(dates) < count:
        if cursor.weekday() == target:
            dates.append(cursor.strftime("%Y-%m-%d"))
        cursor -= timedelta(days=1)
    return list(reversed(dates))


def _ensure_booking(repos, resource_id, user_id, purpose, start, end, attendees, status,
                    approved_by=None):
    existing = repos.bookings.query_one(
        "SELECT id FROM bookings WHERE resource_id = ? AND user_id = ? AND start_time = ?",
        (resource_id, user_id, to_db(start)))
    if existing:
        return repos.bookings.get(existing["id"])
    cursor = repos.bookings.execute(
        "INSERT INTO bookings (reference, resource_id, user_id, purpose, start_time,"
        " end_time, attendees, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?)",
        ("TMP-SEED-%s-%s" % (resource_id, to_db(start)), resource_id, user_id, purpose,
         to_db(start), to_db(end), attendees, status, approved_by), commit=False)
    booking_id = cursor.lastrowid
    repos.bookings.execute("UPDATE bookings SET reference = ? WHERE id = ?",
                           ("BK-%05d" % booking_id, booking_id))
    return repos.bookings.get(booking_id)


def _ensure_request(facade, reporter, resource_id, title, description):
    existing = facade.repos.requests.find_seeded(title, resource_id)
    if existing:
        return existing, False
    return facade.maintenance.submit_request(reporter, resource_id, title, description), True


def _ensure_reading(repos, device, metric, value, recorded_at, target):
    from .domain.iot import IoTReading

    reading = IoTReading(None, device.id, metric, value,
                         resource_id=target.id if target else device.id,
                         recorded_at=recorded_at, device_code=device.code,
                         device_name=device.name,
                         resource_code=target.code if target else device.code,
                         resource_name=target.name if target else device.name)
    return repos.iot.add_reading(reading)


# ------------------------------------------------------------------- seed
def seed_database(connection, reference=None):
    """Populate the database with the demo campus (safe to run repeatedly)."""
    init_schema(connection)
    facade = CampusFacade(connection)
    repos = facade.repos
    reference = reference or datetime.now()

    # --- roles -----------------------------------------------------------
    for name, description in ROLES:
        repos.users.execute(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?,?)",
            (name, description))

    # --- buildings and equipment ----------------------------------------
    for code, name, distance in BUILDINGS:
        repos.resources.add_building(code, name, distance)
    for code, name in EQUIPMENT:
        repos.resources.add_equipment_type(code, name)

    # --- users -----------------------------------------------------------
    users = {}
    for username, full_name, email, role, department, phone in USERS:
        users[username] = repos.users.upsert_seed_user(
            username, full_name, email, DEMO_PASSWORD, role, department, phone)

    # --- resources -------------------------------------------------------
    resources = {}
    for code, name, building, floor, capacity, utilisation, status, seating, equipment in CLASSROOMS:
        resources[code] = repos.resources.add_resource(
            code, name, "CLASSROOM", building, capacity=capacity, floor=floor,
            status=status, utilisation=utilisation, seating_type=seating,
            board_type="SMART" if "SMART_BOARD" in equipment else "WHITEBOARD",
            equipment={item: "GOOD" for item in equipment})
    for (code, name, building, floor, capacity, utilisation, lab_type, safety,
         stations, equipment) in LABORATORIES:
        resources[code] = repos.resources.add_resource(
            code, name, "LABORATORY", building, capacity=capacity, floor=floor,
            utilisation=utilisation, lab_type=lab_type, safety_level=safety,
            workstations=stations, equipment={item: "GOOD" for item in equipment})
    for code, name, building, zone, total, occupied in PARKING:
        resources[code] = repos.resources.add_resource(
            code, name, "PARKING_AREA", building, capacity=total, zone=zone,
            total_slots=total, occupied_slots=occupied)
    for code, name, building, device_type, monitors in DEVICES:
        target = resources.get(monitors)
        resources[code] = repos.resources.add_resource(
            code, name, "SMART_DEVICE", building, capacity=0,
            device_type=device_type, firmware="2.4.1",
            monitors_id=target.id if target else None, is_online=True,
            last_heartbeat=to_db(_at(0, 8, 0, reference)))

    # --- timetable, enrolment and attendance -----------------------------
    schedules = {}
    for course_code, title, faculty, room, day, start, end in SCHEDULES:
        schedule = repos.schedules.add_schedule(
            course_code, title, users[faculty].id, resources[room].id, day, start,
            end, SEMESTER)
        schedules[(course_code, day)] = schedule
        for student in ENROLMENTS.get(course_code, []):
            repos.schedules.enrol(users[student].id, schedule.id)

    attendance_pattern = ("PRESENT", "PRESENT", "LATE", "PRESENT", "ABSENT", "PRESENT")
    slot = 0
    for (course_code, day), schedule in schedules.items():
        for session_date in _past_sessions(day, 3, reference):
            for student in ENROLMENTS.get(course_code, []):
                status = attendance_pattern[slot % len(attendance_pattern)]
                slot += 1
                repos.schedules.seed_attendance(schedule.id, users[student].id,
                                                session_date, status,
                                                schedule.faculty_id)

    # --- bookings --------------------------------------------------------
    _ensure_booking(repos, resources["EB-301"].id, users["dr.kavitha"].id,
                    "Cloud computing revision session", _at(-1, 9, 0, reference),
                    _at(-1, 11, 0, reference), 70, STATUS_COMPLETED)
    _ensure_booking(repos, resources["CR-101"].id, users["dr.suresh"].id,
                    "Department meeting", _at(0, 11, 0, reference),
                    _at(0, 12, 0, reference), 25, STATUS_CONFIRMED)
    _ensure_booking(repos, resources["SB-101"].id, users["dr.kavitha"].id,
                    "Guest lecture rehearsal", _at(0, 16, 0, reference),
                    _at(0, 17, 30, reference), 60, STATUS_CONFIRMED)
    _ensure_booking(repos, resources["CR-201"].id, users["athisaya"].id,
                    "OOAD project team discussion", _at(1, 15, 0, reference),
                    _at(1, 16, 0, reference), 8, STATUS_CONFIRMED)
    _ensure_booking(repos, resources["LB-CS2"].id, users["rahul.k"].id,
                    "Data structures practice session", _at(1, 10, 0, reference),
                    _at(1, 11, 0, reference), 20, STATUS_PENDING)
    _ensure_booking(repos, resources["IH-101"].id, users["arjun.p"].id,
                    "Innovation club meetup", _at(2, 13, 0, reference),
                    _at(2, 14, 30, reference), 18, STATUS_CONFIRMED)

    # --- service requests ------------------------------------------------
    projector, created = _ensure_request(
        facade, users["dr.kavitha"], resources["CR-101"].id,
        "Projector not working in Lecture Hall A",
        "The ceiling projector in CR-101 is not working since this morning and the "
        "lecture could not be delivered with slides.")
    if created:
        facade.assign_request(users["campus.admin"], projector.id, users["tech.mohan"].id)
        facade.advance_request(users["tech.mohan"], projector.id, "IN_PROGRESS",
                               "Technician on site, replacing the projector lamp.")

    leak, created = _ensure_request(
        facade, users["security.ravi"], resources["SB-101"].id,
        "Water leakage near Science Hall entrance",
        "Water is leaking from the ceiling near the entrance of SB-101 and the floor "
        "is slippery.")
    if created:
        facade.assign_request(users["campus.admin"], leak.id, users["tech.arun"].id)

    chairs, created = _ensure_request(
        facade, users["rahul.k"], resources["CR-202"].id,
        "Broken chairs in Seminar Room 202",
        "Four chairs in CR-202 are broken and cannot be used during tutorials.")
    if created:
        facade.assign_request(users["campus.admin"], chairs.id, users["tech.arun"].id)
        facade.advance_request(users["tech.arun"], chairs.id, "IN_PROGRESS",
                               "Replacement chairs requested from the store.")
        facade.advance_request(users["tech.arun"], chairs.id, "RESOLVED",
                               "Four chairs replaced and inspected.")
        facade.advance_request(users["campus.admin"], chairs.id, "CLOSED",
                               "Verified by the administration office.")

    _ensure_request(facade, users["athisaya"], resources["CR-201"].id,
                    "Air conditioning making loud noise",
                    "The air conditioning unit in CR-201 makes a loud rattling noise "
                    "during seminars.")
    _ensure_request(facade, users["meera.s"], resources["LB-CS2"].id,
                    "Laboratory floor needs cleaning",
                    "The floor of Computing Laboratory 2 needs cleaning after the "
                    "practical session.")

    # --- IoT readings ----------------------------------------------------
    normal_readings = [
        ("IOT-OCC-101", "OCCUPANCY", [(8, 25.0), (10, 48.0), (12, 62.0)]),
        ("IOT-OCC-201", "OCCUPANCY", [(8, 10.0), (10, 27.0), (12, 35.0)]),
        ("IOT-OCC-SB1", "OCCUPANCY", [(8, 40.0), (10, 71.0), (12, 88.0)]),
        ("IOT-OCC-IH1", "OCCUPANCY", [(8, 5.0), (10, 18.0), (12, 21.0)]),
        ("IOT-CLI-101", "TEMPERATURE", [(8, 22.4), (10, 23.8), (12, 24.5)]),
        ("IOT-CLI-CS1", "TEMPERATURE", [(8, 26.1), (10, 29.4), (12, 31.5)]),
        ("IOT-AIR-101", "AIR_QUALITY", [(8, 52.0), (10, 66.0), (12, 74.0)]),
        ("IOT-PRK-A", "PARKING_OCCUPANCY", [(8, 41.0), (10, 74.0), (12, 88.0)]),
        ("IOT-PRK-B", "PARKING_OCCUPANCY", [(8, 30.0), (10, 55.0), (12, 68.0)]),
        ("IOT-EQP-CS1", "EQUIPMENT_STATUS", [(8, 1.0), (12, 1.0)]),
        ("IOT-EQP-301", "EQUIPMENT_STATUS", [(8, 1.0), (10, 0.5)]),
        ("IOT-AIR-CH1", "AIR_QUALITY", [(8, 88.0), (10, 141.0)]),
    ]
    for device_code, metric, samples in normal_readings:
        device = resources[device_code]
        target = repos.resources.get(device.monitors_id) if device.monitors_id else None
        for hour, value in samples:
            _ensure_reading(repos, device, metric, value, _at(0, hour, 0, reference), target)

    # Two critical readings ingested through the IoT gateway workflow: each one
    # raises an alert and an automatic high priority ticket exactly once.
    facade.ingest_reading(resources["IOT-AIR-CH1"].id, "AIR_QUALITY", 268.0,
                          _at(0, 12, 30, reference))
    facade.ingest_reading(resources["IOT-EQP-301"].id, "EQUIPMENT_STATUS", 0.0,
                          _at(0, 12, 45, reference))

    # --- events ----------------------------------------------------------
    events = [
        ("AI in Education Symposium",
         "Faculty and industry speakers discuss AI supported teaching on campus.",
         "Seminar", "SB-101", 3, 10, 12, 120),
        ("Alumni Technical Talk",
         "Alumni engineers share industry practices with final year students.",
         "Talk", "IH-101", 5, 15, 17, 60),
        ("Campus Hackathon 2026",
         "Twenty four hour hackathon on smart campus and sustainability themes.",
         "Competition", "LB-CS1", 7, 9, 18, 80),
        ("Placement Drive - Software Engineering",
         "Recruitment drive for software engineering roles across product companies.",
         "Placement", "EB-301", 10, 9, 16, 200),
        ("Green Campus Sustainability Walk",
         "Awareness walk and tree plantation across the campus blocks.",
         "Community", "IH-101", 14, 7, 9, 150),
    ]
    for title, description, category, venue, offset, start_hour, end_hour, capacity in events:
        repos.events.add(title, description, category, _at(offset, start_hour, 0, reference),
                         _at(offset, end_hour, 0, reference), capacity,
                         users["campus.admin"].id, resources[venue].id)
    first_event = repos.events.list_events(upcoming_only=True, limit=1)
    if first_event:
        repos.events.register(first_event[0].id, users["athisaya"].id)
        repos.events.register(first_event[0].id, users["rahul.k"].id)

    # --- digital services -------------------------------------------------
    for code, name, description, category, online in DIGITAL_SERVICES:
        repos.digital_services.add(code, name, description, category, online)

    # --- a welcome notification per demo account --------------------------
    for username, user in users.items():
        repos.notifications.add_once(
            user.id, "Welcome to AISCaMS",
            "You are signed in as %s. Use the sidebar to reach your campus services."
            % user.job_title, "SYSTEM")

    connection.commit()
    return facade


def summary(connection):
    """Row counts per table, used by the tests and the seeding CLI."""
    tables = ("roles", "users", "buildings", "campus_resources", "equipment",
              "resource_equipment", "bookings", "schedules", "enrollments",
              "attendance", "service_requests", "request_history", "iot_readings",
              "alerts", "events", "event_registrations", "notifications",
              "digital_services")
    counts = {}
    for table in tables:
        counts[table] = connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
    return counts
