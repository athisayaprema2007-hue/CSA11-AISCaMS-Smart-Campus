"""Repository for room and laboratory bookings."""

from ..domain.booking import BLOCKING_STATUSES, BOOKING_STATUSES, Booking
from ..exceptions import NotFoundError
from ..utils import to_db
from .base import BaseRepository

BOOKING_SELECT = """
    SELECT b.*, r.code AS resource_code, r.name AS resource_name,
           u.full_name AS user_name
    FROM bookings b
    JOIN campus_resources r ON r.id = b.resource_id
    JOIN users u ON u.id = b.user_id
"""


class BookingRepository(BaseRepository):
    table = "bookings"

    # ------------------------------------------------------------- mapping
    @staticmethod
    def to_domain(row):
        if row is None:
            return None
        return Booking(
            booking_id=row["id"], reference=row["reference"],
            resource_id=row["resource_id"], user_id=row["user_id"],
            purpose=row["purpose"], start_time=row["start_time"],
            end_time=row["end_time"], attendees=row["attendees"],
            status=row["status"], approved_by=row["approved_by"],
            created_at=row["created_at"], resource_code=row["resource_code"],
            resource_name=row["resource_name"], user_name=row["user_name"])

    # --------------------------------------------------------------- reads
    def get(self, booking_id):
        return self.to_domain(self.query_one(BOOKING_SELECT + " WHERE b.id = ?",
                                             (booking_id,)))

    def require_booking(self, booking_id):
        booking = self.get(booking_id)
        if booking is None:
            raise NotFoundError("Booking %s was not found." % booking_id)
        return booking

    def get_by_reference(self, reference):
        return self.to_domain(self.query_one(BOOKING_SELECT + " WHERE b.reference = ?",
                                             (reference,)))

    def list_bookings(self, user_id=None, resource_id=None, status=None,
                      upcoming_from=None, limit=None):
        sql = BOOKING_SELECT
        clauses = []
        params = []
        if user_id:
            clauses.append("b.user_id = ?")
            params.append(user_id)
        if resource_id:
            clauses.append("b.resource_id = ?")
            params.append(resource_id)
        if status:
            statuses = [status] if isinstance(status, str) else list(status)
            clauses.append("b.status IN (%s)" % ",".join("?" for _ in statuses))
            params.extend(statuses)
        if upcoming_from:
            clauses.append("b.end_time >= ?")
            params.append(to_db(upcoming_from))
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY b.start_time"
        if limit:
            sql += " LIMIT %d" % int(limit)
        return [self.to_domain(row) for row in self.query(sql, params)]

    def conflicts(self, resource_id, start_time, end_time, exclude_id=None):
        """Bookings that block the requested window on this resource."""
        sql = (BOOKING_SELECT + " WHERE b.resource_id = ? AND b.status IN (%s)"
               " AND b.start_time < ? AND b.end_time > ?"
               % ",".join("?" for _ in BLOCKING_STATUSES))
        params = [resource_id] + list(BLOCKING_STATUSES) + [to_db(end_time), to_db(start_time)]
        if exclude_id:
            sql += " AND b.id != ?"
            params.append(exclude_id)
        return [self.to_domain(row) for row in self.query(sql, params)]

    def busy_resource_ids(self, start_time, end_time):
        rows = self.query(
            "SELECT DISTINCT resource_id FROM bookings WHERE status IN (%s)"
            " AND start_time < ? AND end_time > ?" % ",".join("?" for _ in BLOCKING_STATUSES),
            list(BLOCKING_STATUSES) + [to_db(end_time), to_db(start_time)])
        return {row["resource_id"] for row in rows}

    def status_counts(self):
        rows = self.query("SELECT status, COUNT(*) AS total FROM bookings GROUP BY status")
        return {row["status"]: row["total"] for row in rows}

    def booked_hours(self, since=None):
        sql = ("SELECT SUM((julianday(end_time) - julianday(start_time)) * 24) FROM bookings"
               " WHERE status IN ('CONFIRMED','COMPLETED')")
        params = []
        if since:
            sql += " AND start_time >= ?"
            params.append(to_db(since))
        return round(float(self.scalar(sql, params, 0.0) or 0.0), 1)

    def top_resources(self, limit=5):
        rows = self.query(
            "SELECT r.code, r.name, COUNT(b.id) AS bookings,"
            " ROUND(SUM((julianday(b.end_time) - julianday(b.start_time)) * 24), 1) AS hours"
            " FROM bookings b JOIN campus_resources r ON r.id = b.resource_id"
            " WHERE b.status IN ('CONFIRMED','COMPLETED','PENDING')"
            " GROUP BY r.id ORDER BY bookings DESC, r.code LIMIT ?", (int(limit),))
        return [dict(row) for row in rows]

    # -------------------------------------------------------------- writes
    def add(self, booking):
        """Persist a new booking and return it with its generated reference."""
        cursor = self.execute(
            "INSERT INTO bookings (reference, resource_id, user_id, purpose, start_time,"
            " end_time, attendees, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?)",
            ("TMP-%s" % id(booking), booking.resource_id, booking.user_id, booking.purpose,
             to_db(booking.start_time), to_db(booking.end_time), booking.attendees,
             booking.status, booking.approved_by), commit=False)
        booking_id = cursor.lastrowid
        reference = "BK-%05d" % booking_id
        self.execute("UPDATE bookings SET reference = ? WHERE id = ?",
                     (reference, booking_id))
        return self.get(booking_id)

    def save_status(self, booking):
        if booking.status not in BOOKING_STATUSES:
            raise NotFoundError("Unknown booking status: %s" % booking.status)
        self.execute("UPDATE bookings SET status = ?, approved_by = ? WHERE id = ?",
                     (booking.status, booking.approved_by, booking.id))
        return self.get(booking.id)

    def delete(self, booking_id):
        self.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
