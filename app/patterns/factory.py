"""Factory pattern - creation and automatic classification of service requests.

The factory is the single place that knows how free text (or an IoT reading)
becomes a concrete `ServiceRequest` subclass with a category, a priority and an
SLA.  Callers simply ask for a request and receive a fully initialised object.
"""

from ..domain.iot import (METRIC_AIR_QUALITY, METRIC_DEVICE_STATUS,
                          METRIC_EQUIPMENT_STATUS, METRIC_OCCUPANCY,
                          METRIC_PARKING_OCCUPANCY, METRIC_TEMPERATURE)
from ..domain.service_request import (HousekeepingRequest, ITSupportRequest,
                                      MaintenanceRequest, PRIORITIES,
                                      PRIORITY_CRITICAL, PRIORITY_HIGH,
                                      PRIORITY_LOW, PRIORITY_MEDIUM,
                                      PRIORITY_ORDER, REQUEST_CLASSES,
                                      SafetyRequest)
from ..exceptions import ValidationError
from ..utils import add_hours, now, require_text

#: Keyword tables used to classify the category of a free text request.
CATEGORY_KEYWORDS = (
    ("SAFETY", ("fire", "smoke", "gas", "spark", "shock", "hazard", "injury",
                "emergency", "short circuit", "exposed wire", "unsafe",
                "intruder", "theft", "collapse")),
    ("IT_SUPPORT", ("projector", "network", "wifi", "wi-fi", "internet", "computer",
                    "pc", "laptop", "printer", "monitor", "software", "login",
                    "server", "switch", "smart board", "smartboard")),
    ("HOUSEKEEPING", ("clean", "cleaning", "garbage", "trash", "waste", "dust",
                      "spill", "washroom", "toilet", "hygiene", "litter")),
    ("MAINTENANCE", ("air condition", "air-condition", "ac ", "fan", "light", "lamp",
                     "door", "window", "chair", "table", "bench", "leak", "water",
                     "plumbing", "power", "socket", "lift", "elevator", "paint")),
)

#: Words that push a request one priority level higher.
ESCALATION_KEYWORDS = ("urgent", "immediately", "asap", "not working", "no power",
                       "completely", "entire", "all ", "danger", "stuck", "broken",
                       "cannot", "unable", "exam", "flood")

#: Base priority per category before escalation.
BASE_PRIORITY = {
    "SAFETY": PRIORITY_HIGH,
    "IT_SUPPORT": PRIORITY_MEDIUM,
    "MAINTENANCE": PRIORITY_MEDIUM,
    "HOUSEKEEPING": PRIORITY_LOW,
}

#: How an IoT metric maps onto a request category when a reading is critical.
METRIC_CATEGORY = {
    METRIC_TEMPERATURE: "MAINTENANCE",
    METRIC_AIR_QUALITY: "SAFETY",
    METRIC_OCCUPANCY: "SAFETY",
    METRIC_PARKING_OCCUPANCY: "MAINTENANCE",
    METRIC_EQUIPMENT_STATUS: "IT_SUPPORT",
    METRIC_DEVICE_STATUS: "IT_SUPPORT",
}


class ServiceRequestFactory:
    """Creates the right `ServiceRequest` subclass for the reported problem."""

    @staticmethod
    def classify_category(text):
        """Pick a category from the reported text using keyword rules."""
        haystack = " %s " % (text or "").lower()
        for category, keywords in CATEGORY_KEYWORDS:
            for keyword in keywords:
                if keyword in haystack:
                    return category
        return "MAINTENANCE"

    @staticmethod
    def classify_priority(text, category):
        """Derive a priority from the category plus escalation keywords."""
        haystack = " %s " % (text or "").lower()
        priority = BASE_PRIORITY.get(category, PRIORITY_MEDIUM)
        escalations = [word for word in ESCALATION_KEYWORDS if word in haystack]
        if escalations:
            index = min(PRIORITY_ORDER[priority] + 1, PRIORITY_ORDER[PRIORITY_CRITICAL])
            priority = PRIORITIES[index]
        if category == "SAFETY" and escalations:
            priority = PRIORITY_CRITICAL
        return priority, escalations

    @classmethod
    def create(cls, resource_id, title, description, raised_by=None, category=None,
              priority=None, source="USER", ticket=None, created_at=None,
              **context):
        """Build a request, classifying category and priority when not supplied."""
        title = require_text(title, "title", minimum=3, maximum=120)
        description = require_text(description, "description", minimum=5, maximum=1000)
        if resource_id is None:
            raise ValidationError("A campus resource must be selected.",
                                  {"field": "resource_id"})
        combined = "%s %s" % (title, description)
        category = (category or cls.classify_category(combined)).upper()
        if category not in REQUEST_CLASSES:
            raise ValidationError("Unknown request category: %s" % category,
                                  {"field": "category"})
        if priority:
            priority = str(priority).upper()
            if priority not in PRIORITIES:
                raise ValidationError("Unknown priority: %s" % priority,
                                      {"field": "priority"})
        else:
            priority, _ = cls.classify_priority(combined, category)
        request_cls = REQUEST_CLASSES[category]
        created = created_at or now()
        sla_hours = request_cls.sla_hours_for(priority)
        return request_cls(
            request_id=None,
            ticket=ticket,
            resource_id=resource_id,
            title=title,
            description=description,
            priority=priority,
            raised_by=raised_by,
            source=source,
            sla_hours=sla_hours,
            sla_due_at=add_hours(created, sla_hours),
            created_at=created,
            **context)

    @classmethod
    def create_from_reading(cls, reading, resource_label=None, created_at=None):
        """Turn a critical IoT reading into a high priority ticket."""
        if not reading.requires_intervention():
            raise ValidationError("Only critical readings raise an automatic request.",
                                  {"field": "severity"})
        category = METRIC_CATEGORY.get(reading.metric, "MAINTENANCE")
        label = resource_label or reading.resource_code or reading.device_code or "resource"
        title = "%s: %s critical reading" % (label, reading.metric_label.lower())
        description = (
            "Automatically generated from IoT device %s. %s measured %s which "
            "crossed the critical threshold. Immediate inspection required."
            % (reading.device_code or reading.device_id, reading.metric_label,
               reading.display_value()))
        return cls.create(
            resource_id=reading.resource_id or reading.device_id,
            title=title,
            description=description,
            raised_by=None,
            category=category,
            priority=PRIORITY_CRITICAL,
            source="IOT",
            created_at=created_at or reading.recorded_at)

    @staticmethod
    def rebuild(row_like):
        """Recreate the concrete subclass from a stored row (repository use)."""
        category = row_like.get("category", "MAINTENANCE")
        request_cls = REQUEST_CLASSES.get(category, MaintenanceRequest)
        payload = dict(row_like)
        payload.pop("category", None)
        return request_cls(**payload)


__all__ = ["ServiceRequestFactory", "CATEGORY_KEYWORDS", "ESCALATION_KEYWORDS",
           "BASE_PRIORITY", "METRIC_CATEGORY", "SafetyRequest", "ITSupportRequest",
           "HousekeepingRequest", "MaintenanceRequest"]
