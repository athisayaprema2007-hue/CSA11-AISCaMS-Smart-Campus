"""Booking workflow: validation, conflict detection and approval routing."""

from ..domain.booking import (Booking, STATUS_CONFIRMED, STATUS_PENDING)
from ..domain.users import Permission
from ..exceptions import (BookingConflictError, CapacityError, EquipmentError,
                          PermissionDeniedError, ResourceUnavailableError,
                          ValidationError)
from ..patterns.observer import (BOOKING_APPROVED, BOOKING_CANCELLED,
                                 BOOKING_CREATED, BOOKING_REJECTED)
from ..utils import human_time, now, parse_datetime

#: A student booking above this size is routed to an administrator first.
STUDENT_APPROVAL_THRESHOLD = 30


class BookingService:
    """Creates and manages bookings of classrooms and laboratories."""

    def __init__(self, booking_repository, resource_repository, user_repository,
                 event_bus):
        self._bookings = booking_repository
        self._resources = resource_repository
        self._users = user_repository
        self._bus = event_bus

    # ------------------------------------------------------------- helpers
    def _admin_ids(self):
        return [user.id for user in self._users.list_users(role="ADMIN", active_only=True)]

    @staticmethod
    def _requires_approval(user, resource, attendees):
        """Students booking large rooms or laboratories need approval."""
        if user.role != "STUDENT":
            return False
        return attendees > STUDENT_APPROVAL_THRESHOLD or resource.resource_type == "LABORATORY"

    # -------------------------------------------------------------- create
    def create_booking(self, user, resource_id, start_time, end_time, attendees,
                       purpose, required_equipment=None):
        if not user.has_permission(Permission.BOOK_RESOURCE):
            raise PermissionDeniedError("%s users cannot book campus resources." % user.role)
        resource = self._resources.require_resource(resource_id)
        start = parse_datetime(start_time, "start time")
        end = parse_datetime(end_time, "end time")
        if start < now().replace(hour=0, minute=0, second=0):
            raise ValidationError("Bookings cannot start in the past.",
                                  {"field": "start_time"})
        if not resource.is_bookable():
            raise ResourceUnavailableError(
                "%s is a %s and cannot be reserved." %
                (resource.code, resource.resource_type.replace("_", " ").lower()))
        if not resource.is_available():
            raise ResourceUnavailableError(
                "%s is currently %s and cannot be booked."
                % (resource.code, resource.status.replace("_", " ").lower()))
        attendees = int(attendees or 0)
        if not resource.matches_capacity(attendees):
            raise CapacityError(
                "%s seats %d people; %d were requested."
                % (resource.code, resource.capacity, attendees),
                {"field": "attendees", "capacity": resource.capacity})
        missing = resource.missing_equipment(required_equipment or [])
        if missing:
            raise EquipmentError(
                "%s does not provide: %s." % (resource.code, ", ".join(missing)),
                {"field": "required_equipment", "missing": missing})
        conflicts = self._bookings.conflicts(resource.id, start, end)
        if conflicts:
            clash = conflicts[0]
            raise BookingConflictError(
                "%s is already booked from %s to %s (%s)."
                % (resource.code, human_time(clash.start_time),
                   human_time(clash.end_time), clash.reference),
                {"conflict_reference": clash.reference})

        status = (STATUS_PENDING if self._requires_approval(user, resource, attendees)
                  else STATUS_CONFIRMED)
        booking = Booking(None, None, resource.id, user.id, purpose, start, end,
                          attendees, status)
        stored = self._bookings.add(booking)

        recipients = [user.id]
        if status == STATUS_PENDING:
            recipients.extend(self._admin_ids())
            message = ("Booking %s for %s on %s is awaiting administrator approval."
                       % (stored.reference, resource.code, human_time(start)))
        else:
            message = ("Booking %s confirmed: %s from %s to %s."
                       % (stored.reference, resource.code, human_time(start),
                          human_time(end)))
        self._bus.notify(BOOKING_CREATED, {
            "recipients": recipients,
            "title": "Booking %s" % ("submitted" if status == STATUS_PENDING else "confirmed"),
            "message": message,
            "entity_type": "BOOKING",
            "entity_id": stored.id,
            "booking": stored,
        })
        return stored

    # ------------------------------------------------------------- approve
    def approve_booking(self, admin, booking_id, approve=True):
        if not admin.has_permission(Permission.APPROVE_BOOKING):
            raise PermissionDeniedError("Only administrators can approve bookings.")
        booking = self._bookings.require_booking(booking_id)
        if approve:
            conflicts = [item for item in
                         self._bookings.conflicts(booking.resource_id, booking.start_time,
                                                  booking.end_time, exclude_id=booking.id)
                         if item.status == STATUS_CONFIRMED]
            if conflicts:
                raise BookingConflictError(
                    "Cannot approve %s: the slot is already confirmed for %s."
                    % (booking.reference, conflicts[0].reference))
            booking.confirm(admin.id)
            event = BOOKING_APPROVED
            message = "Booking %s for %s was approved." % (booking.reference,
                                                           booking.resource_code)
        else:
            booking.reject(admin.id)
            event = BOOKING_REJECTED
            message = "Booking %s for %s was rejected." % (booking.reference,
                                                           booking.resource_code)
        stored = self._bookings.save_status(booking)
        self._bus.notify(event, {
            "recipients": [booking.user_id],
            "title": "Booking %s" % ("approved" if approve else "rejected"),
            "message": message,
            "entity_type": "BOOKING",
            "entity_id": booking.id,
            "booking": stored,
        })
        return stored

    # -------------------------------------------------------------- cancel
    def cancel_booking(self, user, booking_id):
        booking = self._bookings.require_booking(booking_id)
        if booking.user_id != user.id and not user.has_permission(Permission.APPROVE_BOOKING):
            raise PermissionDeniedError("You can only cancel your own bookings.")
        booking.cancel()
        stored = self._bookings.save_status(booking)
        self._bus.notify(BOOKING_CANCELLED, {
            "recipients": [booking.user_id],
            "title": "Booking cancelled",
            "message": "Booking %s for %s was cancelled." % (booking.reference,
                                                             booking.resource_code),
            "entity_type": "BOOKING",
            "entity_id": booking.id,
            "booking": stored,
        })
        return stored

    # --------------------------------------------------------------- reads
    def bookings_for(self, user, upcoming_only=False):
        return self._bookings.list_bookings(
            user_id=user.id, upcoming_from=now() if upcoming_only else None)

    def pending_approvals(self, admin):
        if not admin.has_permission(Permission.APPROVE_BOOKING):
            raise PermissionDeniedError("Only administrators can review bookings.")
        return self._bookings.list_bookings(status=STATUS_PENDING)

    def calendar_for_resource(self, resource_id):
        return self._bookings.list_bookings(resource_id=resource_id,
                                            status=["PENDING", "CONFIRMED"])
