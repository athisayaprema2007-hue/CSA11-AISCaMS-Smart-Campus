"""Repository for service requests and their status history."""

from ..domain.service_request import (OPEN_STATUSES, REQUEST_CLASSES,
                                      REQUEST_STATUSES)
from ..exceptions import NotFoundError
from ..utils import now, to_db
from .base import BaseRepository

REQUEST_SELECT = """
    SELECT s.*, r.code AS resource_code, r.name AS resource_name,
           ru.full_name AS raised_by_name, au.full_name AS assigned_to_name
    FROM service_requests s
    JOIN campus_resources r ON r.id = s.resource_id
    LEFT JOIN users ru ON ru.id = s.raised_by
    LEFT JOIN users au ON au.id = s.assigned_to
"""


class ServiceRequestRepository(BaseRepository):
    """Persists the `ServiceRequest` hierarchy, restoring the right subclass."""

    table = "service_requests"

    # ------------------------------------------------------------- mapping
    @staticmethod
    def to_domain(row):
        if row is None:
            return None
        cls = REQUEST_CLASSES[row["category"]]
        return cls(
            request_id=row["id"], ticket=row["ticket"], resource_id=row["resource_id"],
            title=row["title"], description=row["description"], priority=row["priority"],
            status=row["status"], raised_by=row["raised_by"],
            assigned_to=row["assigned_to"], source=row["source"],
            sla_hours=row["sla_hours"], sla_due_at=row["sla_due_at"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            resolved_at=row["resolved_at"], closed_at=row["closed_at"],
            resource_code=row["resource_code"], resource_name=row["resource_name"],
            raised_by_name=row["raised_by_name"],
            assigned_to_name=row["assigned_to_name"])

    def _with_history(self, request):
        if request is not None:
            request.history = self.history(request.id)
        return request

    # --------------------------------------------------------------- reads
    def get(self, request_id):
        return self._with_history(
            self.to_domain(self.query_one(REQUEST_SELECT + " WHERE s.id = ?", (request_id,))))

    def require_request(self, request_id):
        request = self.get(request_id)
        if request is None:
            raise NotFoundError("Service request %s was not found." % request_id)
        return request

    def get_by_ticket(self, ticket):
        return self._with_history(
            self.to_domain(self.query_one(REQUEST_SELECT + " WHERE s.ticket = ?", (ticket,))))

    def list_requests(self, raised_by=None, assigned_to=None, status=None,
                      priority=None, resource_id=None, category=None, source=None,
                      open_only=False, limit=None, with_history=False):
        sql = REQUEST_SELECT
        clauses = []
        params = []
        if raised_by:
            clauses.append("s.raised_by = ?")
            params.append(raised_by)
        if assigned_to:
            clauses.append("s.assigned_to = ?")
            params.append(assigned_to)
        if status:
            statuses = [status] if isinstance(status, str) else list(status)
            clauses.append("s.status IN (%s)" % ",".join("?" for _ in statuses))
            params.extend(statuses)
        if open_only:
            clauses.append("s.status IN (%s)" % ",".join("?" for _ in OPEN_STATUSES))
            params.extend(OPEN_STATUSES)
        if priority:
            clauses.append("s.priority = ?")
            params.append(priority)
        if resource_id:
            clauses.append("s.resource_id = ?")
            params.append(resource_id)
        if category:
            clauses.append("s.category = ?")
            params.append(category)
        if source:
            clauses.append("s.source = ?")
            params.append(source)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += (" ORDER BY CASE s.priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1"
                " WHEN 'MEDIUM' THEN 2 ELSE 3 END, s.created_at DESC")
        if limit:
            sql += " LIMIT %d" % int(limit)
        items = [self.to_domain(row) for row in self.query(sql, params)]
        if with_history:
            for item in items:
                item.history = self.history(item.id)
        return items

    def history(self, request_id):
        rows = self.query(
            "SELECT h.*, u.full_name AS changed_by_name FROM request_history h"
            " LEFT JOIN users u ON u.id = h.changed_by WHERE h.request_id = ?"
            " ORDER BY h.id", (request_id,))
        return [dict(row) for row in rows]

    def status_counts(self):
        rows = self.query("SELECT status, COUNT(*) AS total FROM service_requests"
                          " GROUP BY status")
        counts = {status: 0 for status in REQUEST_STATUSES}
        counts.update({row["status"]: row["total"] for row in rows})
        return counts

    def priority_counts(self, open_only=True):
        sql = "SELECT priority, COUNT(*) AS total FROM service_requests"
        params = []
        if open_only:
            sql += " WHERE status IN (%s)" % ",".join("?" for _ in OPEN_STATUSES)
            params.extend(OPEN_STATUSES)
        sql += " GROUP BY priority"
        return {row["priority"]: row["total"] for row in self.query(sql, params)}

    def breached(self, reference=None):
        reference = to_db(reference or now())
        rows = self.query(
            REQUEST_SELECT + " WHERE s.status IN (%s) AND s.sla_due_at < ?"
            % ",".join("?" for _ in OPEN_STATUSES), list(OPEN_STATUSES) + [reference])
        return [self.to_domain(row) for row in rows]

    def category_counts(self):
        rows = self.query("SELECT category, COUNT(*) AS total FROM service_requests"
                          " GROUP BY category")
        return {row["category"]: row["total"] for row in rows}

    # -------------------------------------------------------------- writes
    def add(self, request, note="Request created"):
        cursor = self.execute(
            "INSERT INTO service_requests (ticket, resource_id, raised_by, assigned_to,"
            " category, priority, status, title, description, source, sla_hours,"
            " sla_due_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("TMP-%s" % id(request), request.resource_id, request.raised_by,
             request.assigned_to, request.category, request.priority, request.status,
             request.title, request.description, request.source, request.sla_hours,
             to_db(request.sla_due_at), to_db(request.created_at),
             to_db(request.updated_at)), commit=False)
        request_id = cursor.lastrowid
        ticket = "SR-%05d" % request_id
        self.execute("UPDATE service_requests SET ticket = ? WHERE id = ?",
                     (ticket, request_id), commit=False)
        self.execute(
            "INSERT INTO request_history (request_id, from_status, to_status, note,"
            " changed_by, changed_at) VALUES (?,?,?,?,?,?)",
            (request_id, None, request.status, note, request.raised_by,
             to_db(request.created_at)))
        return self.get(request_id)

    def save(self, request, from_status=None, note=None, changed_by=None):
        """Persist the current state of a request plus a history entry."""
        self.execute(
            "UPDATE service_requests SET assigned_to = ?, priority = ?, status = ?,"
            " sla_hours = ?, sla_due_at = ?, updated_at = ?, resolved_at = ?,"
            " closed_at = ? WHERE id = ?",
            (request.assigned_to, request.priority, request.status, request.sla_hours,
             to_db(request.sla_due_at), to_db(request.updated_at),
             to_db(request.resolved_at), to_db(request.closed_at), request.id),
            commit=False)
        if from_status is not None or note:
            self.execute(
                "INSERT INTO request_history (request_id, from_status, to_status, note,"
                " changed_by) VALUES (?,?,?,?,?)",
                (request.id, from_status, request.status, note, changed_by), commit=False)
        self.commit()
        return self.get(request.id)

    def find_seeded(self, title, resource_id):
        """Used by the idempotent seeding process."""
        row = self.query_one(REQUEST_SELECT + " WHERE s.title = ? AND s.resource_id = ?",
                             (title, resource_id))
        return self.to_domain(row)
