"""Repository for campus events, registrations and digital services."""

from ..domain.events import CampusEvent
from ..exceptions import NotFoundError, ValidationError
from ..utils import now, to_db
from .base import BaseRepository

EVENT_SELECT = """
    SELECT e.*, r.code AS venue_code, r.name AS venue_name,
           u.full_name AS organiser_name,
           (SELECT COUNT(*) FROM event_registrations x WHERE x.event_id = e.id) AS registrations
    FROM events e
    LEFT JOIN campus_resources r ON r.id = e.venue_id
    JOIN users u ON u.id = e.organiser_id
"""


class EventRepository(BaseRepository):
    table = "events"

    @staticmethod
    def to_domain(row, registered=False):
        if row is None:
            return None
        return CampusEvent(
            event_id=row["id"], title=row["title"], description=row["description"],
            category=row["category"], start_time=row["start_time"],
            end_time=row["end_time"], capacity=row["capacity"],
            organiser_id=row["organiser_id"], venue_id=row["venue_id"],
            status=row["status"], venue_code=row["venue_code"],
            venue_name=row["venue_name"], organiser_name=row["organiser_name"],
            registrations=row["registrations"], registered=registered)

    def _registered_ids(self, user_id):
        if not user_id:
            return set()
        rows = self.query("SELECT event_id FROM event_registrations WHERE user_id = ?",
                          (user_id,))
        return {row["event_id"] for row in rows}

    # --------------------------------------------------------------- reads
    def get(self, event_id, user_id=None):
        row = self.query_one(EVENT_SELECT + " WHERE e.id = ?", (event_id,))
        if row is None:
            return None
        return self.to_domain(row, event_id in self._registered_ids(user_id))

    def require_event(self, event_id):
        event = self.get(event_id)
        if event is None:
            raise NotFoundError("Event %s was not found." % event_id)
        return event

    def list_events(self, upcoming_only=False, user_id=None, limit=None, status=None):
        sql = EVENT_SELECT
        clauses = []
        params = []
        if upcoming_only:
            clauses.append("e.end_time >= ?")
            params.append(to_db(now()))
            clauses.append("e.status = 'SCHEDULED'")
        if status:
            clauses.append("e.status = ?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY e.start_time"
        if limit:
            sql += " LIMIT %d" % int(limit)
        registered = self._registered_ids(user_id)
        return [self.to_domain(row, row["id"] in registered)
                for row in self.query(sql, params)]

    def registrations_for(self, user_id):
        return [self.to_domain(row, True) for row in self.query(
            EVENT_SELECT + " JOIN event_registrations er ON er.event_id = e.id"
            " WHERE er.user_id = ? ORDER BY e.start_time", (user_id,))]

    # -------------------------------------------------------------- writes
    def add(self, title, description, category, start_time, end_time, capacity,
            organiser_id, venue_id=None, status="SCHEDULED"):
        existing = self.query_one("SELECT id FROM events WHERE title = ?", (title,))
        if existing:
            return self.get(existing["id"])
        # Validate through the domain object before touching the database.
        CampusEvent(None, title, description, category, start_time, end_time,
                    capacity, organiser_id, venue_id, status)
        cursor = self.execute(
            "INSERT INTO events (title, description, category, venue_id, organiser_id,"
            " start_time, end_time, capacity, status) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, description, category, venue_id, organiser_id, to_db(start_time),
             to_db(end_time), int(capacity), status))
        return self.get(cursor.lastrowid)

    def cancel(self, event_id):
        event = self.require_event(event_id)
        event.cancel()
        self.execute("UPDATE events SET status = ? WHERE id = ?", (event.status, event_id))
        return self.get(event_id)

    def register(self, event_id, user_id):
        event = self.get(event_id, user_id)
        if event is None:
            raise NotFoundError("Event %s was not found." % event_id)
        if event.status != "SCHEDULED":
            raise ValidationError("Registration is closed for this event.",
                                  {"field": "event_id"})
        if event.registered:
            return event
        if event.is_full():
            raise ValidationError("This event is fully booked.", {"field": "event_id"})
        self.execute("INSERT OR IGNORE INTO event_registrations (event_id, user_id)"
                     " VALUES (?,?)", (event_id, user_id))
        return self.get(event_id, user_id)


class DigitalServiceRepository(BaseRepository):
    """Read-only catalogue of digital campus services."""

    table = "digital_services"

    def list_services(self):
        return [dict(row) for row in
                self.query("SELECT * FROM digital_services ORDER BY category, name")]

    def add(self, code, name, description, category, is_online=True):
        existing = self.query_one("SELECT id FROM digital_services WHERE code = ?", (code,))
        if existing:
            return existing["id"]
        cursor = self.execute(
            "INSERT INTO digital_services (code, name, description, category, is_online)"
            " VALUES (?,?,?,?,?)", (code, name, description, category,
                                    1 if is_online else 0))
        return cursor.lastrowid
