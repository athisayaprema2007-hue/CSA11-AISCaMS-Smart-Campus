-- AISCaMS - AI-Enabled Smart Campus Management System
-- SQLite schema with foreign keys, CHECK constraints and indexes.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- users
CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
                CHECK (name IN ('STUDENT','FACULTY','ADMIN','SECURITY','MAINTENANCE')),
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE CHECK (length(username) >= 3),
    full_name     TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    email         TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%._%'),
    password_hash TEXT NOT NULL,
    role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    department    TEXT,
    phone         TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);

-- ------------------------------------------------------------ resources
CREATE TABLE IF NOT EXISTS buildings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    walking_distance_m  INTEGER NOT NULL DEFAULT 0 CHECK (walking_distance_m >= 0)
);

CREATE TABLE IF NOT EXISTS campus_resources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    resource_type TEXT NOT NULL
                  CHECK (resource_type IN ('CLASSROOM','LABORATORY','PARKING_AREA','SMART_DEVICE')),
    building_id   INTEGER NOT NULL REFERENCES buildings(id) ON DELETE RESTRICT,
    floor         INTEGER NOT NULL DEFAULT 0,
    capacity      INTEGER NOT NULL DEFAULT 0 CHECK (capacity >= 0),
    status        TEXT NOT NULL DEFAULT 'AVAILABLE'
                  CHECK (status IN ('AVAILABLE','OCCUPIED','MAINTENANCE','OFFLINE')),
    utilisation   REAL NOT NULL DEFAULT 0.0 CHECK (utilisation BETWEEN 0 AND 1),
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_resources_type   ON campus_resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_resources_status ON campus_resources(status);

CREATE TABLE IF NOT EXISTS classrooms (
    resource_id  INTEGER PRIMARY KEY REFERENCES campus_resources(id) ON DELETE CASCADE,
    seating_type TEXT NOT NULL DEFAULT 'FIXED' CHECK (seating_type IN ('FIXED','MOVABLE','TIERED')),
    board_type   TEXT NOT NULL DEFAULT 'WHITEBOARD'
);

CREATE TABLE IF NOT EXISTS laboratories (
    resource_id   INTEGER PRIMARY KEY REFERENCES campus_resources(id) ON DELETE CASCADE,
    lab_type      TEXT NOT NULL,
    safety_level  TEXT NOT NULL DEFAULT 'STANDARD' CHECK (safety_level IN ('STANDARD','HIGH')),
    workstations  INTEGER NOT NULL DEFAULT 0 CHECK (workstations >= 0)
);

CREATE TABLE IF NOT EXISTS parking_areas (
    resource_id    INTEGER PRIMARY KEY REFERENCES campus_resources(id) ON DELETE CASCADE,
    zone           TEXT NOT NULL,
    total_slots    INTEGER NOT NULL CHECK (total_slots > 0),
    occupied_slots INTEGER NOT NULL DEFAULT 0 CHECK (occupied_slots >= 0),
    CHECK (occupied_slots <= total_slots)
);

CREATE TABLE IF NOT EXISTS smart_devices (
    resource_id     INTEGER PRIMARY KEY REFERENCES campus_resources(id) ON DELETE CASCADE,
    device_type     TEXT NOT NULL
                    CHECK (device_type IN ('OCCUPANCY_SENSOR','CLIMATE_SENSOR','AIR_QUALITY_SENSOR',
                                           'PARKING_SENSOR','EQUIPMENT_MONITOR')),
    firmware        TEXT NOT NULL DEFAULT '1.0.0',
    monitors_id     INTEGER REFERENCES campus_resources(id) ON DELETE SET NULL,
    is_online       INTEGER NOT NULL DEFAULT 1 CHECK (is_online IN (0,1)),
    last_heartbeat  TEXT
);
CREATE INDEX IF NOT EXISTS idx_devices_monitors ON smart_devices(monitors_id);

CREATE TABLE IF NOT EXISTS equipment (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_equipment (
    resource_id  INTEGER NOT NULL REFERENCES campus_resources(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    condition    TEXT NOT NULL DEFAULT 'GOOD'
                 CHECK (condition IN ('GOOD','FAIR','FAULTY','OUT_OF_SERVICE')),
    PRIMARY KEY (resource_id, equipment_id)
);

-- ------------------------------------------------------------- bookings
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reference   TEXT NOT NULL UNIQUE,
    resource_id INTEGER NOT NULL REFERENCES campus_resources(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose     TEXT NOT NULL CHECK (length(trim(purpose)) > 0),
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL,
    attendees   INTEGER NOT NULL DEFAULT 1 CHECK (attendees > 0),
    status      TEXT NOT NULL DEFAULT 'CONFIRMED'
                CHECK (status IN ('PENDING','CONFIRMED','REJECTED','CANCELLED','COMPLETED')),
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK (end_time > start_time)
);
CREATE INDEX IF NOT EXISTS idx_bookings_resource ON bookings(resource_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_bookings_user     ON bookings(user_id);

-- ------------------------------------------------------------ academics
CREATE TABLE IF NOT EXISTS schedules (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code  TEXT NOT NULL,
    course_title TEXT NOT NULL,
    faculty_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_id  INTEGER NOT NULL REFERENCES campus_resources(id) ON DELETE CASCADE,
    day_of_week  TEXT NOT NULL
                 CHECK (day_of_week IN ('MON','TUE','WED','THU','FRI','SAT')),
    start_time   TEXT NOT NULL,
    end_time     TEXT NOT NULL,
    semester     TEXT NOT NULL,
    UNIQUE (course_code, day_of_week, start_time, semester),
    CHECK (end_time > start_time)
);
CREATE INDEX IF NOT EXISTS idx_schedules_faculty ON schedules(faculty_id);

CREATE TABLE IF NOT EXISTS enrollments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    UNIQUE (student_id, schedule_id)
);

CREATE TABLE IF NOT EXISTS attendance (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id  INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    student_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_date TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('PRESENT','ABSENT','LATE')),
    recorded_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    recorded_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (schedule_id, student_id, session_date)
);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);

-- ------------------------------------------------------ service requests
CREATE TABLE IF NOT EXISTS service_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket      TEXT NOT NULL UNIQUE,
    resource_id INTEGER NOT NULL REFERENCES campus_resources(id) ON DELETE CASCADE,
    raised_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    category    TEXT NOT NULL
                CHECK (category IN ('MAINTENANCE','SAFETY','IT_SUPPORT','HOUSEKEEPING')),
    priority    TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    status      TEXT NOT NULL DEFAULT 'NEW'
                CHECK (status IN ('NEW','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED','REJECTED')),
    title       TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT NOT NULL CHECK (length(trim(description)) >= 5),
    source      TEXT NOT NULL DEFAULT 'USER' CHECK (source IN ('USER','IOT')),
    sla_hours   INTEGER NOT NULL CHECK (sla_hours > 0),
    sla_due_at  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    resolved_at TEXT,
    closed_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_requests_status   ON service_requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_assignee ON service_requests(assigned_to);
CREATE INDEX IF NOT EXISTS idx_requests_resource ON service_requests(resource_id);

CREATE TABLE IF NOT EXISTS request_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    note        TEXT,
    changed_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_history_request ON request_history(request_id);

-- ------------------------------------------------------------------ IoT
CREATE TABLE IF NOT EXISTS iot_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   INTEGER NOT NULL REFERENCES campus_resources(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES campus_resources(id) ON DELETE CASCADE,
    metric      TEXT NOT NULL
                CHECK (metric IN ('OCCUPANCY','TEMPERATURE','AIR_QUALITY','EQUIPMENT_STATUS',
                                  'PARKING_OCCUPANCY','DEVICE_STATUS')),
    value       REAL NOT NULL,
    unit        TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL DEFAULT 'NORMAL'
                CHECK (severity IN ('NORMAL','WARNING','CRITICAL')),
    recorded_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (device_id, metric, recorded_at)
);
CREATE INDEX IF NOT EXISTS idx_readings_device ON iot_readings(device_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_readings_metric ON iot_readings(metric, recorded_at);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_id      INTEGER REFERENCES iot_readings(id) ON DELETE SET NULL,
    resource_id     INTEGER NOT NULL REFERENCES campus_resources(id) ON DELETE CASCADE,
    request_id      INTEGER REFERENCES service_requests(id) ON DELETE SET NULL,
    alert_type      TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('WARNING','CRITICAL')),
    message         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN','ACKNOWLEDGED','RESOLVED')),
    acknowledged_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    acknowledged_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- --------------------------------------------------------------- events
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL UNIQUE,
    description  TEXT NOT NULL,
    category     TEXT NOT NULL,
    venue_id     INTEGER REFERENCES campus_resources(id) ON DELETE SET NULL,
    organiser_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time   TEXT NOT NULL,
    end_time     TEXT NOT NULL,
    capacity     INTEGER NOT NULL CHECK (capacity > 0),
    status       TEXT NOT NULL DEFAULT 'SCHEDULED'
                 CHECK (status IN ('SCHEDULED','ONGOING','COMPLETED','CANCELLED')),
    CHECK (end_time > start_time)
);

CREATE TABLE IF NOT EXISTS event_registrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    registered_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (event_id, user_id)
);

-- -------------------------------------------------------- notifications
CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    category    TEXT NOT NULL
                CHECK (category IN ('BOOKING','REQUEST','ALERT','EVENT','SYSTEM')),
    entity_type TEXT,
    entity_id   INTEGER,
    is_read     INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0,1)),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);

-- ----------------------------------------------- digital campus services
CREATE TABLE IF NOT EXISTS digital_services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    category    TEXT NOT NULL,
    is_online   INTEGER NOT NULL DEFAULT 1 CHECK (is_online IN (0,1))
);
