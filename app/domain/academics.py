"""Academic entities: timetable slots and attendance records."""

from ..exceptions import ValidationError
from ..utils import DAY_CODES, parse_datetime

ATTENDANCE_PRESENT = "PRESENT"
ATTENDANCE_ABSENT = "ABSENT"
ATTENDANCE_LATE = "LATE"
ATTENDANCE_STATUSES = (ATTENDANCE_PRESENT, ATTENDANCE_ABSENT, ATTENDANCE_LATE)


class Schedule:
    """A recurring weekly class slot held in a campus resource."""

    def __init__(self, schedule_id, course_code, course_title, faculty_id, resource_id,
                 day_of_week, start_time, end_time, semester, resource_code=None,
                 resource_name=None, faculty_name=None, enrolled=0):
        day = (day_of_week or "").upper()
        if day not in DAY_CODES:
            raise ValidationError("Unknown day of week: %s" % day_of_week,
                                  {"field": "day_of_week"})
        if end_time <= start_time:
            raise ValidationError("Class end time must be after the start time.",
                                  {"field": "end_time"})
        self._id = schedule_id
        self._course_code = course_code
        self._course_title = course_title
        self._faculty_id = faculty_id
        self._resource_id = resource_id
        self._day_of_week = day
        self._start_time = start_time
        self._end_time = end_time
        self._semester = semester
        self.resource_code = resource_code
        self.resource_name = resource_name
        self.faculty_name = faculty_name
        self.enrolled = int(enrolled or 0)

    @property
    def id(self):
        return self._id

    @property
    def course_code(self):
        return self._course_code

    @property
    def course_title(self):
        return self._course_title

    @property
    def faculty_id(self):
        return self._faculty_id

    @property
    def resource_id(self):
        return self._resource_id

    @property
    def day_of_week(self):
        return self._day_of_week

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def semester(self):
        return self._semester

    @property
    def time_range(self):
        return "%s - %s" % (self._start_time, self._end_time)

    def is_today(self, today_code):
        return self._day_of_week == today_code

    def to_dict(self):
        return {
            "id": self._id,
            "course_code": self._course_code,
            "course_title": self._course_title,
            "faculty_id": self._faculty_id,
            "faculty_name": self.faculty_name,
            "resource_id": self._resource_id,
            "resource_code": self.resource_code,
            "resource_name": self.resource_name,
            "day_of_week": self._day_of_week,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "time_range": self.time_range,
            "semester": self._semester,
            "enrolled": self.enrolled,
        }


class AttendanceRecord:
    """Attendance of one student for one session of a scheduled class."""

    def __init__(self, record_id, schedule_id, student_id, session_date, status,
                 recorded_by=None, recorded_at=None, student_name=None,
                 course_code=None):
        status = (status or "").upper()
        if status not in ATTENDANCE_STATUSES:
            raise ValidationError("Unknown attendance status: %s" % status,
                                  {"field": "status"})
        self._id = record_id
        self._schedule_id = schedule_id
        self._student_id = student_id
        self._session_date = str(session_date)
        self._status = status
        self._recorded_by = recorded_by
        self._recorded_at = parse_datetime(recorded_at) if recorded_at else None
        self.student_name = student_name
        self.course_code = course_code

    @property
    def id(self):
        return self._id

    @property
    def schedule_id(self):
        return self._schedule_id

    @property
    def student_id(self):
        return self._student_id

    @property
    def session_date(self):
        return self._session_date

    @property
    def status(self):
        return self._status

    @property
    def recorded_by(self):
        return self._recorded_by

    def is_present(self):
        return self._status in (ATTENDANCE_PRESENT, ATTENDANCE_LATE)

    def to_dict(self):
        return {
            "id": self._id,
            "schedule_id": self._schedule_id,
            "student_id": self._student_id,
            "student_name": self.student_name,
            "course_code": self.course_code,
            "session_date": self._session_date,
            "status": self._status,
            "recorded_by": self._recorded_by,
            "present": self.is_present(),
        }
