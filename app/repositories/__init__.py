"""Repository layer: the only place that talks SQL."""

from .base import BaseRepository
from .booking_repository import BookingRepository
from .event_repository import DigitalServiceRepository, EventRepository
from .iot_repository import AlertRepository, IoTRepository
from .notification_repository import NotificationRepository
from .request_repository import ServiceRequestRepository
from .resource_repository import ResourceRepository
from .schedule_repository import ScheduleRepository
from .user_repository import UserRepository


class RepositoryRegistry:
    """Bundles every repository for one database connection (unit of work)."""

    def __init__(self, connection):
        self.connection = connection
        self.users = UserRepository(connection)
        self.resources = ResourceRepository(connection)
        self.bookings = BookingRepository(connection)
        self.requests = ServiceRequestRepository(connection)
        self.schedules = ScheduleRepository(connection)
        self.iot = IoTRepository(connection)
        self.alerts = AlertRepository(connection)
        self.events = EventRepository(connection)
        self.notifications = NotificationRepository(connection)
        self.digital_services = DigitalServiceRepository(connection)


__all__ = [
    "BaseRepository", "UserRepository", "ResourceRepository", "BookingRepository",
    "ServiceRequestRepository", "ScheduleRepository", "IoTRepository",
    "AlertRepository", "EventRepository", "DigitalServiceRepository",
    "NotificationRepository", "RepositoryRegistry",
]
