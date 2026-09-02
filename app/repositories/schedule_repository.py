"""Repository for timetables, enrolments and attendance."""

from ..domain.academics import ATTENDANCE_STATUSES, AttendanceRecord, Schedule
from ..exceptions import NotFoundError, ValidationError
from ..utils import require_choice
from .base import BaseRepository

SCHEDULE_SELECT = """
    SELECT s.*, r.code AS resource_code, r.name AS resource_name,
           f.full_name AS faculty_name,
           (SELECT COUNT(*) FROM enrollments e WHERE e.schedule_id = s.id) AS enrolled
    FROM schedules s
    JOIN campus_resources r ON r.id = s.resource_id
    JOIN users f ON f.id = s.faculty_id
"""

DAY_ORDER = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


class ScheduleRepository(BaseRepository):
    table = "schedules"

    @staticmethod
    def to_domain(row):
        if row is None:
            return None
        return Schedule(
            schedule_id=row["id"], course_code=row["course_code"],
            course_title=row["course_title"], faculty_id=row["faculty_id"],
            resource_id=row["resource_id"], day_of_week=row["day_of_week"],
            start_time=row["start_time"], end_time=row["end_time"],
            semester=row["semester"], resource_code=row["resource_code"],
            resource_name=row["resource_name"], faculty_name=row["faculty_name"],
            enrolled=row["enrolled"])

    # --------------------------------------------------------------- reads
    def get(self, schedule_id):
        return self.to_domain(self.query_one(SCHEDULE_SELECT + " WHERE s.id = ?",
                                             (schedule_id,)))

    def require_schedule(self, schedule_id):
        schedule = self.get(schedule_id)
        if schedule is None:
            raise NotFoundError("Schedule %s was not found." % schedule_id)
        return schedule

    def _ordered(self, rows):
        items = [self.to_domain(row) for row in rows]
        items.sort(key=lambda s: (DAY_ORDER.index(s.day_of_week), s.start_time))
        return items

    def for_faculty(self, faculty_id, day=None):
        sql = SCHEDULE_SELECT + " WHERE s.faculty_id = ?"
        params = [faculty_id]
        if day:
            sql += " AND s.day_of_week = ?"
            params.append(day)
        return self._ordered(self.query(sql, params))

    def for_student(self, student_id, day=None):
        sql = (SCHEDULE_SELECT + " JOIN enrollments e ON e.schedule_id = s.id"
               " WHERE e.student_id = ?")
        params = [student_id]
        if day:
            sql += " AND s.day_of_week = ?"
            params.append(day)
        return self._ordered(self.query(sql, params))

    def for_resource(self, resource_id):
        return self._ordered(self.query(SCHEDULE_SELECT + " WHERE s.resource_id = ?",
                                        (resource_id,)))

    def all_schedules(self):
        return self._ordered(self.query(SCHEDULE_SELECT))

    def roster(self, schedule_id):
        rows = self.query(
            "SELECT u.id, u.full_name, u.username, u.department FROM enrollments e"
            " JOIN users u ON u.id = e.student_id WHERE e.schedule_id = ?"
            " ORDER BY u.full_name", (schedule_id,))
        return [dict(row) for row in rows]

    # ---------------------------------------------------------- attendance
    def attendance_for_session(self, schedule_id, session_date):
        rows = self.query(
            "SELECT a.*, u.full_name AS student_name, s.course_code FROM attendance a"
            " JOIN users u ON u.id = a.student_id"
            " JOIN schedules s ON s.id = a.schedule_id"
            " WHERE a.schedule_id = ? AND a.session_date = ?"
            " ORDER BY u.full_name", (schedule_id, session_date))
        return [AttendanceRecord(
            record_id=row["id"], schedule_id=row["schedule_id"],
            student_id=row["student_id"], session_date=row["session_date"],
            status=row["status"], recorded_by=row["recorded_by"],
            recorded_at=row["recorded_at"], student_name=row["student_name"],
            course_code=row["course_code"]) for row in rows]

    def attendance_summary(self, student_id):
        row = self.query_one(
            "SELECT COUNT(*) AS sessions,"
            " SUM(CASE WHEN status IN ('PRESENT','LATE') THEN 1 ELSE 0 END) AS present"
            " FROM attendance WHERE student_id = ?", (student_id,))
        sessions = row["sessions"] or 0
        present = row["present"] or 0
        percentage = round((present / float(sessions)) * 100, 1) if sessions else 0.0
        return {"sessions": sessions, "present": present, "percentage": percentage}

    def course_attendance(self, schedule_id):
        row = self.query_one(
            "SELECT COUNT(*) AS records,"
            " SUM(CASE WHEN status IN ('PRESENT','LATE') THEN 1 ELSE 0 END) AS present"
            " FROM attendance WHERE schedule_id = ?", (schedule_id,))
        records = row["records"] or 0
        present = row["present"] or 0
        return {"records": records, "present": present,
                "percentage": round((present / float(records)) * 100, 1) if records else 0.0}

    def record_attendance(self, schedule_id, student_id, session_date, status,
                          recorded_by=None):
        status = require_choice(status, "status", set(ATTENDANCE_STATUSES))
        self.require_schedule(schedule_id)
        enrolled = self.exists_enrollment(student_id, schedule_id)
        if not enrolled:
            raise ValidationError("This student is not enrolled in the selected class.",
                                  {"field": "student_id"})
        self.execute(
            "INSERT INTO attendance (schedule_id, student_id, session_date, status,"
            " recorded_by) VALUES (?,?,?,?,?)"
            " ON CONFLICT(schedule_id, student_id, session_date)"
            " DO UPDATE SET status = excluded.status, recorded_by = excluded.recorded_by,"
            " recorded_at = datetime('now', 'localtime')",
            (schedule_id, student_id, session_date, status, recorded_by))
        return self.attendance_for_session(schedule_id, session_date)

    # -------------------------------------------------------------- writes
    def exists_enrollment(self, student_id, schedule_id):
        return self.query_one(
            "SELECT 1 FROM enrollments WHERE student_id = ? AND schedule_id = ?",
            (student_id, schedule_id)) is not None

    def add_schedule(self, course_code, course_title, faculty_id, resource_id,
                     day_of_week, start_time, end_time, semester):
        existing = self.query_one(
            "SELECT id FROM schedules WHERE course_code = ? AND day_of_week = ?"
            " AND start_time = ? AND semester = ?",
            (course_code, day_of_week, start_time, semester))
        if existing:
            return self.get(existing["id"])
        cursor = self.execute(
            "INSERT INTO schedules (course_code, course_title, faculty_id, resource_id,"
            " day_of_week, start_time, end_time, semester) VALUES (?,?,?,?,?,?,?,?)",
            (course_code, course_title, faculty_id, resource_id, day_of_week,
             start_time, end_time, semester))
        return self.get(cursor.lastrowid)

    def enrol(self, student_id, schedule_id):
        self.execute("INSERT OR IGNORE INTO enrollments (student_id, schedule_id)"
                     " VALUES (?,?)", (student_id, schedule_id))
        return True

    def seed_attendance(self, schedule_id, student_id, session_date, status,
                        recorded_by=None):
        """Idempotent attendance insert used by the seeding process."""
        self.execute(
            "INSERT OR IGNORE INTO attendance (schedule_id, student_id, session_date,"
            " status, recorded_by) VALUES (?,?,?,?,?)",
            (schedule_id, student_id, session_date, status, recorded_by))
