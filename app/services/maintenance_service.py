"""Service request lifecycle: creation, assignment, SLA and status updates."""

from ..domain.service_request import (OPEN_STATUSES, STATUS_ASSIGNED,
                                      STATUS_CLOSED, STATUS_IN_PROGRESS,
                                      STATUS_RESOLVED)
from ..domain.users import Permission
from ..exceptions import PermissionDeniedError, ValidationError
from ..patterns.factory import ServiceRequestFactory
from ..patterns.observer import (REQUEST_ASSIGNED, REQUEST_CREATED,
                                 REQUEST_STATUS_CHANGED)
from ..utils import now, require_choice


class MaintenanceService:
    """Coordinates service requests between reporters, admins and technicians."""

    def __init__(self, request_repository, resource_repository, user_repository,
                 event_bus):
        self._requests = request_repository
        self._resources = resource_repository
        self._users = user_repository
        self._bus = event_bus

    # ------------------------------------------------------------- helpers
    def _admin_ids(self):
        return [user.id for user in self._users.list_users(role="ADMIN", active_only=True)]

    def least_loaded_technician(self):
        """Technician with the fewest open tickets (used for auto-assignment)."""
        staff = self._users.maintenance_staff()
        if not staff:
            return None
        def open_count(member):
            return len(self._requests.list_requests(assigned_to=member.id, open_only=True))
        return sorted(staff, key=lambda member: (open_count(member), member.id))[0]

    # -------------------------------------------------------------- create
    def submit_request(self, user, resource_id, title, description, category=None,
                       priority=None):
        if not user.has_permission(Permission.SUBMIT_REQUEST):
            raise PermissionDeniedError("%s users cannot raise service requests." % user.role)
        resource = self._resources.require_resource(resource_id)
        request = ServiceRequestFactory.create(
            resource_id=resource.id, title=title, description=description,
            raised_by=user.id, category=category, priority=priority, source="USER")
        stored = self._requests.add(request)
        self._bus.notify(REQUEST_CREATED, {
            "recipients": [user.id] + self._admin_ids(),
            "title": "Service request %s created" % stored.ticket,
            "message": ("%s classified as %s / %s for %s. Resolution due by %s."
                        % (stored.ticket, stored.category_label, stored.priority,
                           resource.code, stored.to_dict()["sla_due_display"])),
            "entity_type": "REQUEST",
            "entity_id": stored.id,
            "request": stored,
        })
        return stored

    def create_automatic_request(self, reading, resource_label=None, auto_assign=True):
        """Create a critical ticket from an IoT reading (used by IoTService)."""
        request = ServiceRequestFactory.create_from_reading(reading, resource_label)
        stored = self._requests.add(request, note="Raised automatically by IoT gateway")
        if auto_assign:
            technician = self.least_loaded_technician()
            if technician is not None:
                stored = self.assign_request(None, stored.id, technician.id,
                                             system=True)
        return stored

    # -------------------------------------------------------------- assign
    def assign_request(self, actor, request_id, staff_id, system=False):
        if not system:
            if actor is None or not actor.has_permission(Permission.ASSIGN_REQUEST):
                raise PermissionDeniedError("Only administrators can assign requests.")
        technician = self._users.require_user(staff_id)
        if technician.role != "MAINTENANCE":
            raise ValidationError("Requests can only be assigned to maintenance staff.",
                                  {"field": "assigned_to"})
        request = self._requests.require_request(request_id)
        previous = request.status
        request.assign(technician.id)
        note = ("Auto-assigned to %s by the IoT gateway" if system
                else "Assigned to %s") % technician.full_name
        stored = self._requests.save(request, from_status=previous, note=note,
                                     changed_by=None if system else actor.id)
        self._bus.notify(REQUEST_ASSIGNED, {
            "recipients": [technician.id] + ([request.raised_by] if request.raised_by else []),
            "title": "Request %s assigned" % stored.ticket,
            "message": "%s (%s priority) assigned to %s for %s."
                       % (stored.ticket, stored.priority, technician.full_name,
                          stored.resource_code),
            "entity_type": "REQUEST",
            "entity_id": stored.id,
            "request": stored,
        })
        return stored

    # -------------------------------------------------------------- status
    def update_status(self, user, request_id, new_status, note=None):
        if not user.has_permission(Permission.UPDATE_REQUEST_STATUS):
            raise PermissionDeniedError(
                "%s users cannot update the status of a service request." % user.role)
        request = self._requests.require_request(request_id)
        if (user.role == "MAINTENANCE" and request.assigned_to != user.id):
            raise PermissionDeniedError("This request is assigned to another technician.")
        new_status = require_choice(new_status, "status",
                                    {STATUS_ASSIGNED, STATUS_IN_PROGRESS, STATUS_RESOLVED,
                                     STATUS_CLOSED, "REJECTED"})
        previous = request.transition_to(new_status)
        stored = self._requests.save(request, from_status=previous,
                                     note=note or "Status changed to %s" % new_status,
                                     changed_by=user.id)
        recipients = [uid for uid in (request.raised_by, request.assigned_to) if uid]
        self._bus.notify(REQUEST_STATUS_CHANGED, {
            "recipients": recipients,
            "title": "Request %s is now %s" % (stored.ticket, new_status.replace("_", " ")),
            "message": "%s for %s moved from %s to %s by %s."
                       % (stored.ticket, stored.resource_code, previous, new_status,
                          user.full_name),
            "entity_type": "REQUEST",
            "entity_id": stored.id,
            "request": stored,
            "from_status": previous,
        })
        return stored

    def update_equipment_condition(self, user, resource_id, equipment_code, condition):
        if not user.has_permission(Permission.UPDATE_EQUIPMENT):
            raise PermissionDeniedError("Only maintenance staff can update equipment.")
        return self._resources.set_equipment_condition(resource_id, equipment_code,
                                                       condition)

    # --------------------------------------------------------------- reads
    def requests_for_reporter(self, user):
        return self._requests.list_requests(raised_by=user.id)

    def queue_for(self, technician, open_only=False):
        return self._requests.list_requests(assigned_to=technician.id,
                                            open_only=open_only)

    def open_requests(self):
        return self._requests.list_requests(open_only=True)

    def unassigned_requests(self):
        return [item for item in self._requests.list_requests(status="NEW")]

    def sla_overview(self, reference=None):
        reference = reference or now()
        open_requests = self._requests.list_requests(open_only=True)
        summary = {"total_open": len(open_requests), "on_track": 0, "at_risk": 0,
                   "breached": 0}
        for request in open_requests:
            state = request.sla_state(reference)
            if state == "BREACHED":
                summary["breached"] += 1
            elif state == "AT_RISK":
                summary["at_risk"] += 1
            else:
                summary["on_track"] += 1
        summary["statuses"] = self._requests.status_counts()
        summary["priorities"] = self._requests.priority_counts()
        summary["open_statuses"] = list(OPEN_STATUSES)
        return summary
