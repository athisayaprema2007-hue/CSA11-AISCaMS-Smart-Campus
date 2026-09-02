"""Repositories for IoT readings and infrastructure alerts."""

from ..domain.iot import IoTReading
from ..exceptions import NotFoundError
from ..utils import now, to_db
from .base import BaseRepository

READING_SELECT = """
    SELECT i.*, d.code AS device_code, d.name AS device_name,
           t.code AS resource_code, t.name AS resource_name
    FROM iot_readings i
    JOIN campus_resources d ON d.id = i.device_id
    LEFT JOIN campus_resources t ON t.id = i.resource_id
"""


class IoTRepository(BaseRepository):
    table = "iot_readings"

    @staticmethod
    def to_domain(row):
        if row is None:
            return None
        return IoTReading(
            reading_id=row["id"], device_id=row["device_id"], metric=row["metric"],
            value=row["value"], resource_id=row["resource_id"], unit=row["unit"],
            severity=row["severity"], recorded_at=row["recorded_at"],
            device_code=row["device_code"], device_name=row["device_name"],
            resource_code=row["resource_code"], resource_name=row["resource_name"])

    # --------------------------------------------------------------- reads
    def get(self, reading_id):
        return self.to_domain(self.query_one(READING_SELECT + " WHERE i.id = ?",
                                             (reading_id,)))

    def list_readings(self, metric=None, severity=None, device_id=None,
                      resource_id=None, limit=50):
        sql = READING_SELECT
        clauses = []
        params = []
        if metric:
            clauses.append("i.metric = ?")
            params.append(metric)
        if severity:
            clauses.append("i.severity = ?")
            params.append(severity)
        if device_id:
            clauses.append("i.device_id = ?")
            params.append(device_id)
        if resource_id:
            clauses.append("i.resource_id = ?")
            params.append(resource_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY i.recorded_at DESC, i.id DESC LIMIT %d" % int(limit)
        return [self.to_domain(row) for row in self.query(sql, params)]

    def latest_per_device(self):
        """Most recent reading of every device/metric pair."""
        rows = self.query(
            READING_SELECT +
            " JOIN (SELECT device_id, metric, MAX(recorded_at) AS latest, MAX(id) AS max_id"
            "       FROM iot_readings GROUP BY device_id, metric) latest_rows"
            "   ON latest_rows.max_id = i.id"
            " ORDER BY i.severity DESC, d.code")
        return [self.to_domain(row) for row in rows]

    def latest_for(self, resource_id, metric):
        row = self.query_one(
            READING_SELECT + " WHERE i.resource_id = ? AND i.metric = ?"
            " ORDER BY i.recorded_at DESC, i.id DESC LIMIT 1", (resource_id, metric))
        return self.to_domain(row)

    def latest_occupancy_map(self):
        """{resource_id: occupancy ratio} from the newest OCCUPANCY readings."""
        rows = self.query(
            "SELECT i.resource_id, i.value FROM iot_readings i"
            " JOIN (SELECT resource_id, MAX(id) AS max_id FROM iot_readings"
            "       WHERE metric = 'OCCUPANCY' AND resource_id IS NOT NULL"
            "       GROUP BY resource_id) l ON l.max_id = i.id")
        return {row["resource_id"]: float(row["value"]) / 100.0 for row in rows}

    def severity_counts(self, since=None):
        sql = "SELECT severity, COUNT(*) AS total FROM iot_readings"
        params = []
        if since:
            sql += " WHERE recorded_at >= ?"
            params.append(to_db(since))
        sql += " GROUP BY severity"
        counts = {"NORMAL": 0, "WARNING": 0, "CRITICAL": 0}
        counts.update({row["severity"]: row["total"] for row in self.query(sql, params)})
        return counts

    # -------------------------------------------------------------- writes
    def add_reading(self, reading):
        """Store a reading; identical (device, metric, timestamp) rows are ignored."""
        cursor = self.execute(
            "INSERT OR IGNORE INTO iot_readings (device_id, resource_id, metric, value,"
            " unit, severity, recorded_at) VALUES (?,?,?,?,?,?,?)",
            (reading.device_id, reading.resource_id, reading.metric, reading.value,
             reading.unit, reading.severity, to_db(reading.recorded_at)))
        if cursor.lastrowid and cursor.rowcount:
            return self.get(cursor.lastrowid)
        row = self.query_one(
            READING_SELECT + " WHERE i.device_id = ? AND i.metric = ? AND i.recorded_at = ?",
            (reading.device_id, reading.metric, to_db(reading.recorded_at)))
        return self.to_domain(row)


ALERT_SELECT = """
    SELECT a.*, r.code AS resource_code, r.name AS resource_name,
           s.ticket AS request_ticket, u.full_name AS acknowledged_by_name
    FROM alerts a
    JOIN campus_resources r ON r.id = a.resource_id
    LEFT JOIN service_requests s ON s.id = a.request_id
    LEFT JOIN users u ON u.id = a.acknowledged_by
"""


class AlertRepository(BaseRepository):
    """Infrastructure and safety alerts raised from critical IoT readings."""

    table = "alerts"

    def get(self, alert_id):
        row = self.query_one(ALERT_SELECT + " WHERE a.id = ?", (alert_id,))
        return dict(row) if row else None

    def require_alert(self, alert_id):
        alert = self.get(alert_id)
        if alert is None:
            raise NotFoundError("Alert %s was not found." % alert_id)
        return alert

    def list_alerts(self, status=None, severity=None, limit=50):
        sql = ALERT_SELECT
        clauses = []
        params = []
        if status:
            statuses = [status] if isinstance(status, str) else list(status)
            clauses.append("a.status IN (%s)" % ",".join("?" for _ in statuses))
            params.extend(statuses)
        if severity:
            clauses.append("a.severity = ?")
            params.append(severity)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY a.created_at DESC, a.id DESC LIMIT %d" % int(limit)
        return [dict(row) for row in self.query(sql, params)]

    def open_for(self, resource_id, alert_type):
        row = self.query_one(
            ALERT_SELECT + " WHERE a.resource_id = ? AND a.alert_type = ?"
            " AND a.status != 'RESOLVED' ORDER BY a.id DESC LIMIT 1",
            (resource_id, alert_type))
        return dict(row) if row else None

    def add(self, resource_id, alert_type, severity, message, reading_id=None,
            request_id=None):
        cursor = self.execute(
            "INSERT INTO alerts (reading_id, resource_id, request_id, alert_type,"
            " severity, message) VALUES (?,?,?,?,?,?)",
            (reading_id, resource_id, request_id, alert_type, severity, message))
        return cursor.lastrowid

    def link_request(self, alert_id, request_id):
        self.execute("UPDATE alerts SET request_id = ? WHERE id = ?",
                     (request_id, alert_id))
        return self.get(alert_id)

    def acknowledge(self, alert_id, user_id):
        alert = self.require_alert(alert_id)
        if alert["status"] != "OPEN":
            return alert
        self.execute(
            "UPDATE alerts SET status = 'ACKNOWLEDGED', acknowledged_by = ?,"
            " acknowledged_at = ? WHERE id = ?", (user_id, to_db(now()), alert_id))
        return self.get(alert_id)

    def resolve(self, alert_id):
        self.execute("UPDATE alerts SET status = 'RESOLVED' WHERE id = ?", (alert_id,))
        return self.get(alert_id)

    def status_counts(self):
        rows = self.query("SELECT status, COUNT(*) AS total FROM alerts GROUP BY status")
        counts = {"OPEN": 0, "ACKNOWLEDGED": 0, "RESOLVED": 0}
        counts.update({row["status"]: row["total"] for row in rows})
        return counts
