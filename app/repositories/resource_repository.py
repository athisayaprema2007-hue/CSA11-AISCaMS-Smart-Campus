"""Repository for buildings, campus resources and their equipment."""

from ..domain.resources import (Building, Classroom, Laboratory, ParkingArea,
                                RESOURCE_STATUSES, SmartDevice)
from ..exceptions import NotFoundError, ValidationError
from ..utils import require_choice, require_int, require_text
from .base import BaseRepository

RESOURCE_SELECT = """
    SELECT r.id, r.code, r.name, r.resource_type, r.building_id, r.floor,
           r.capacity, r.status, r.utilisation,
           b.code AS building_code, b.name AS building_name,
           b.walking_distance_m AS walking_distance_m,
           c.seating_type, c.board_type,
           l.lab_type, l.safety_level, l.workstations,
           p.zone, p.total_slots, p.occupied_slots,
           d.device_type, d.firmware, d.monitors_id, d.is_online, d.last_heartbeat
    FROM campus_resources r
    JOIN buildings b ON b.id = r.building_id
    LEFT JOIN classrooms c ON c.resource_id = r.id
    LEFT JOIN laboratories l ON l.resource_id = r.id
    LEFT JOIN parking_areas p ON p.resource_id = r.id
    LEFT JOIN smart_devices d ON d.resource_id = r.id
"""


class ResourceRepository(BaseRepository):
    """Loads `CampusResource` objects with the correct concrete subclass."""

    table = "campus_resources"

    # ------------------------------------------------------------- mapping
    def _equipment_for(self, resource_ids):
        if not resource_ids:
            return {}
        placeholders = ",".join("?" for _ in resource_ids)
        rows = self.query(
            "SELECT re.resource_id, e.code, re.condition FROM resource_equipment re "
            "JOIN equipment e ON e.id = re.equipment_id "
            "WHERE re.resource_id IN (%s) ORDER BY e.code" % placeholders,
            list(resource_ids))
        mapping = {}
        for row in rows:
            mapping.setdefault(row["resource_id"], {})[row["code"]] = row["condition"]
        return mapping

    @staticmethod
    def _build(row, equipment):
        building = Building(row["building_id"], row["building_code"], row["building_name"],
                            row["walking_distance_m"])
        common = dict(resource_id=row["id"], code=row["code"], name=row["name"],
                      building=building, floor=row["floor"], capacity=row["capacity"],
                      status=row["status"], utilisation=row["utilisation"],
                      equipment=equipment)
        kind = row["resource_type"]
        if kind == "CLASSROOM":
            return Classroom(seating_type=row["seating_type"] or "FIXED",
                             board_type=row["board_type"] or "WHITEBOARD", **common)
        if kind == "LABORATORY":
            return Laboratory(lab_type=row["lab_type"] or "COMPUTING",
                              safety_level=row["safety_level"] or "STANDARD",
                              workstations=row["workstations"] or 0, **common)
        if kind == "PARKING_AREA":
            return ParkingArea(zone=row["zone"] or "A",
                               total_slots=row["total_slots"] or 0,
                               occupied_slots=row["occupied_slots"] or 0, **common)
        return SmartDevice(device_type=row["device_type"] or "OCCUPANCY_SENSOR",
                           firmware=row["firmware"] or "1.0.0",
                           monitors_id=row["monitors_id"],
                           is_online=bool(row["is_online"]) if row["is_online"] is not None else True,
                           last_heartbeat=row["last_heartbeat"], **common)

    def _to_domain_many(self, rows):
        equipment = self._equipment_for([row["id"] for row in rows])
        return [self._build(row, equipment.get(row["id"], {})) for row in rows]

    # --------------------------------------------------------------- reads
    def get(self, resource_id):
        row = self.query_one(RESOURCE_SELECT + " WHERE r.id = ?", (resource_id,))
        if row is None:
            return None
        return self._build(row, self._equipment_for([resource_id]).get(resource_id, {}))

    def require_resource(self, resource_id):
        resource = self.get(resource_id)
        if resource is None:
            raise NotFoundError("Campus resource %s was not found." % resource_id)
        return resource

    def get_by_code(self, code):
        row = self.query_one(RESOURCE_SELECT + " WHERE r.code = ?", (code,))
        if row is None:
            return None
        return self._build(row, self._equipment_for([row["id"]]).get(row["id"], {}))

    def list_resources(self, resource_type=None, status=None, search=None,
                       min_capacity=None, building=None, equipment=None,
                       bookable_only=False):
        """Search resources; equipment filtering is applied in the domain layer."""
        sql = RESOURCE_SELECT
        clauses = []
        params = []
        if resource_type:
            clauses.append("r.resource_type = ?")
            params.append(resource_type)
        if bookable_only:
            clauses.append("r.resource_type IN ('CLASSROOM','LABORATORY')")
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        if min_capacity:
            clauses.append("r.capacity >= ?")
            params.append(int(min_capacity))
        if building:
            clauses.append("(b.code = ? OR b.name = ?)")
            params.extend([building, building])
        if search:
            like = "%%%s%%" % str(search).strip()
            clauses.append("(r.code LIKE ? OR r.name LIKE ? OR b.name LIKE ?)")
            params.extend([like, like, like])
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY r.resource_type, r.code"
        resources = self._to_domain_many(self.query(sql, params))
        if equipment:
            wanted = [code for code in equipment if code]
            resources = [res for res in resources if not res.missing_equipment(wanted)]
        return resources

    def buildings(self):
        return [Building(row["id"], row["code"], row["name"], row["walking_distance_m"])
                for row in self.query("SELECT * FROM buildings ORDER BY walking_distance_m")]

    def equipment_catalog(self):
        return [dict(row) for row in self.query("SELECT * FROM equipment ORDER BY code")]

    def parking_areas(self):
        return self.list_resources(resource_type="PARKING_AREA")

    def smart_devices(self):
        return self.list_resources(resource_type="SMART_DEVICE")

    def type_counts(self):
        rows = self.query(
            "SELECT resource_type, COUNT(*) AS total FROM campus_resources "
            "GROUP BY resource_type")
        return {row["resource_type"]: row["total"] for row in rows}

    def status_counts(self):
        rows = self.query(
            "SELECT status, COUNT(*) AS total FROM campus_resources GROUP BY status")
        return {row["status"]: row["total"] for row in rows}

    def average_utilisation(self, resource_type=None):
        sql = "SELECT AVG(utilisation) FROM campus_resources"
        params = []
        if resource_type:
            sql += " WHERE resource_type = ?"
            params.append(resource_type)
        return round(float(self.scalar(sql, params, 0.0) or 0.0), 3)

    # -------------------------------------------------------------- writes
    def building_id(self, code):
        row = self.query_one("SELECT id FROM buildings WHERE code = ? OR name = ?",
                             (code, code))
        if row is None:
            raise NotFoundError("Unknown building: %s" % code)
        return row["id"]

    def add_building(self, code, name, walking_distance_m):
        existing = self.query_one("SELECT id FROM buildings WHERE code = ?", (code,))
        if existing:
            return existing["id"]
        cursor = self.execute(
            "INSERT INTO buildings (code, name, walking_distance_m) VALUES (?,?,?)",
            (code, name, int(walking_distance_m)))
        return cursor.lastrowid

    def add_equipment_type(self, code, name):
        existing = self.query_one("SELECT id FROM equipment WHERE code = ?", (code,))
        if existing:
            return existing["id"]
        cursor = self.execute("INSERT INTO equipment (code, name) VALUES (?,?)", (code, name))
        return cursor.lastrowid

    def add_resource(self, code, name, resource_type, building, capacity=0, floor=0,
                     status="AVAILABLE", utilisation=0.0, equipment=None, **extra):
        """Create a resource together with its sub-type row (idempotent by code)."""
        code = require_text(code, "code", minimum=2, maximum=20).upper()
        name = require_text(name, "name", minimum=2, maximum=80)
        resource_type = require_choice(resource_type, "resource type",
                                       {"CLASSROOM", "LABORATORY", "PARKING_AREA", "SMART_DEVICE"})
        status = require_choice(status, "status", set(RESOURCE_STATUSES))
        capacity = require_int(capacity, "capacity", minimum=0, maximum=2000)
        existing = self.get_by_code(code)
        if existing is not None:
            return existing
        building_id = building if isinstance(building, int) else self.building_id(building)
        cursor = self.execute(
            "INSERT INTO campus_resources (code, name, resource_type, building_id, floor,"
            " capacity, status, utilisation) VALUES (?,?,?,?,?,?,?,?)",
            (code, name, resource_type, building_id, int(floor), capacity, status,
             float(utilisation)), commit=False)
        resource_id = cursor.lastrowid
        if resource_type == "CLASSROOM":
            self.execute("INSERT INTO classrooms (resource_id, seating_type, board_type)"
                         " VALUES (?,?,?)",
                         (resource_id, extra.get("seating_type", "FIXED"),
                          extra.get("board_type", "WHITEBOARD")), commit=False)
        elif resource_type == "LABORATORY":
            self.execute("INSERT INTO laboratories (resource_id, lab_type, safety_level,"
                         " workstations) VALUES (?,?,?,?)",
                         (resource_id, extra.get("lab_type", "COMPUTING"),
                          extra.get("safety_level", "STANDARD"),
                          int(extra.get("workstations", 0))), commit=False)
        elif resource_type == "PARKING_AREA":
            self.execute("INSERT INTO parking_areas (resource_id, zone, total_slots,"
                         " occupied_slots) VALUES (?,?,?,?)",
                         (resource_id, extra.get("zone", "A"),
                          int(extra.get("total_slots", capacity or 1)),
                          int(extra.get("occupied_slots", 0))), commit=False)
        else:
            self.execute("INSERT INTO smart_devices (resource_id, device_type, firmware,"
                         " monitors_id, is_online, last_heartbeat) VALUES (?,?,?,?,?,?)",
                         (resource_id, extra.get("device_type", "OCCUPANCY_SENSOR"),
                          extra.get("firmware", "1.0.0"), extra.get("monitors_id"),
                          1 if extra.get("is_online", True) else 0,
                          extra.get("last_heartbeat")), commit=False)
        for equipment_code, condition in (equipment or {}).items():
            equipment_id = self.add_equipment_type(equipment_code, equipment_code.title())
            self.execute("INSERT OR IGNORE INTO resource_equipment (resource_id,"
                         " equipment_id, condition) VALUES (?,?,?)",
                         (resource_id, equipment_id, condition), commit=False)
        self.commit()
        return self.get(resource_id)

    def update_status(self, resource_id, status):
        status = require_choice(status, "status", set(RESOURCE_STATUSES))
        self.require_resource(resource_id)
        self.execute("UPDATE campus_resources SET status = ? WHERE id = ?",
                     (status, resource_id))
        return self.get(resource_id)

    def update_utilisation(self, resource_id, utilisation):
        value = max(0.0, min(float(utilisation), 1.0))
        self.execute("UPDATE campus_resources SET utilisation = ? WHERE id = ?",
                     (value, resource_id))
        return self.get(resource_id)

    def set_equipment_condition(self, resource_id, equipment_code, condition):
        condition = require_choice(condition, "condition",
                                   {"GOOD", "FAIR", "FAULTY", "OUT_OF_SERVICE"})
        resource = self.require_resource(resource_id)
        if equipment_code not in resource.equipment:
            raise ValidationError("%s does not have equipment %s."
                                  % (resource.code, equipment_code),
                                  {"field": "equipment_code"})
        row = self.query_one("SELECT id FROM equipment WHERE code = ?", (equipment_code,))
        self.execute("UPDATE resource_equipment SET condition = ? WHERE resource_id = ?"
                     " AND equipment_id = ?", (condition, resource_id, row["id"]))
        return self.get(resource_id)

    def update_parking_occupancy(self, resource_id, occupied_slots):
        area = self.require_resource(resource_id)
        if not isinstance(area, ParkingArea):
            raise ValidationError("Resource %s is not a parking area." % area.code,
                                  {"field": "resource_id"})
        area.update_occupancy(occupied_slots)
        self.execute("UPDATE parking_areas SET occupied_slots = ? WHERE resource_id = ?",
                     (area.occupied_slots, resource_id))
        return self.get(resource_id)

    def set_device_online(self, resource_id, is_online, heartbeat=None):
        self.execute("UPDATE smart_devices SET is_online = ?, last_heartbeat = COALESCE(?,"
                     " last_heartbeat) WHERE resource_id = ?",
                     (1 if is_online else 0, heartbeat, resource_id))
        if not is_online:
            self.execute("UPDATE campus_resources SET status = 'OFFLINE' WHERE id = ?",
                         (resource_id,))
        return self.get(resource_id)
