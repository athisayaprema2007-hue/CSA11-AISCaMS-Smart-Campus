"""IoT reading entity and the threshold rules that classify its severity."""

from ..exceptions import ValidationError
from ..utils import human_time, now, parse_datetime, to_db

METRIC_OCCUPANCY = "OCCUPANCY"
METRIC_TEMPERATURE = "TEMPERATURE"
METRIC_AIR_QUALITY = "AIR_QUALITY"
METRIC_EQUIPMENT_STATUS = "EQUIPMENT_STATUS"
METRIC_PARKING_OCCUPANCY = "PARKING_OCCUPANCY"
METRIC_DEVICE_STATUS = "DEVICE_STATUS"
METRICS = (METRIC_OCCUPANCY, METRIC_TEMPERATURE, METRIC_AIR_QUALITY,
           METRIC_EQUIPMENT_STATUS, METRIC_PARKING_OCCUPANCY, METRIC_DEVICE_STATUS)

SEVERITY_NORMAL = "NORMAL"
SEVERITY_WARNING = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"

METRIC_UNITS = {
    METRIC_OCCUPANCY: "%",
    METRIC_TEMPERATURE: "C",
    METRIC_AIR_QUALITY: "AQI",
    METRIC_EQUIPMENT_STATUS: "state",
    METRIC_PARKING_OCCUPANCY: "%",
    METRIC_DEVICE_STATUS: "state",
}

METRIC_LABELS = {
    METRIC_OCCUPANCY: "Room occupancy",
    METRIC_TEMPERATURE: "Temperature",
    METRIC_AIR_QUALITY: "Air quality index",
    METRIC_EQUIPMENT_STATUS: "Equipment status",
    METRIC_PARKING_OCCUPANCY: "Parking occupancy",
    METRIC_DEVICE_STATUS: "Device status",
}

#: Inclusive thresholds used to classify a reading.
THRESHOLDS = {
    METRIC_OCCUPANCY: {"warning": 90.0, "critical": 100.0},
    METRIC_TEMPERATURE: {"warning": 30.0, "critical": 35.0, "low_warning": 16.0,
                         "low_critical": 10.0},
    METRIC_AIR_QUALITY: {"warning": 150.0, "critical": 250.0},
    METRIC_PARKING_OCCUPANCY: {"warning": 85.0, "critical": 97.0},
}


class IoTReading:
    """A single measurement published by a smart device."""

    def __init__(self, reading_id, device_id, metric, value, resource_id=None,
                 unit=None, severity=None, recorded_at=None, device_code=None,
                 device_name=None, resource_code=None, resource_name=None):
        if metric not in METRICS:
            raise ValidationError("Unknown metric: %s" % metric, {"field": "metric"})
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            raise ValidationError("Reading value must be numeric.", {"field": "value"})
        self._id = reading_id
        self._device_id = device_id
        self._resource_id = resource_id
        self._metric = metric
        self._value = numeric
        self._unit = unit if unit is not None else METRIC_UNITS[metric]
        self._severity = severity or self.classify(metric, numeric)
        self._recorded_at = parse_datetime(recorded_at) if recorded_at else now()
        self.device_code = device_code
        self.device_name = device_name
        self.resource_code = resource_code
        self.resource_name = resource_name

    # -------------------------------------------------------------- rules
    @staticmethod
    def classify(metric, value):
        """Return NORMAL / WARNING / CRITICAL for a metric value."""
        value = float(value)
        if metric in (METRIC_EQUIPMENT_STATUS, METRIC_DEVICE_STATUS):
            if value <= 0:
                return SEVERITY_CRITICAL
            if value < 1:
                return SEVERITY_WARNING
            return SEVERITY_NORMAL
        limits = THRESHOLDS.get(metric)
        if not limits:
            return SEVERITY_NORMAL
        if value >= limits["critical"]:
            return SEVERITY_CRITICAL
        if "low_critical" in limits and value <= limits["low_critical"]:
            return SEVERITY_CRITICAL
        if value >= limits["warning"]:
            return SEVERITY_WARNING
        if "low_warning" in limits and value <= limits["low_warning"]:
            return SEVERITY_WARNING
        return SEVERITY_NORMAL

    # --------------------------------------------------------- properties
    @property
    def id(self):
        return self._id

    @property
    def device_id(self):
        return self._device_id

    @property
    def resource_id(self):
        return self._resource_id

    @property
    def metric(self):
        return self._metric

    @property
    def metric_label(self):
        return METRIC_LABELS[self._metric]

    @property
    def value(self):
        return self._value

    @property
    def unit(self):
        return self._unit

    @property
    def severity(self):
        return self._severity

    @property
    def recorded_at(self):
        return self._recorded_at

    # ---------------------------------------------------------- behaviour
    def is_critical(self):
        return self._severity == SEVERITY_CRITICAL

    def is_normal(self):
        return self._severity == SEVERITY_NORMAL

    def requires_intervention(self):
        """Critical readings automatically raise a high priority ticket."""
        return self._severity in (SEVERITY_CRITICAL,)

    def display_value(self):
        if self._metric in (METRIC_EQUIPMENT_STATUS, METRIC_DEVICE_STATUS):
            if self._value >= 1:
                return "Operational"
            if self._value > 0:
                return "Degraded"
            return "Failed"
        if float(self._value).is_integer():
            return "%d %s" % (int(self._value), self._unit)
        return "%.1f %s" % (self._value, self._unit)

    def describe(self):
        return "%s on %s: %s (%s)" % (self.metric_label,
                                      self.resource_code or self.device_code or "device",
                                      self.display_value(), self._severity.lower())

    def to_dict(self):
        return {
            "id": self._id,
            "device_id": self._device_id,
            "device_code": self.device_code,
            "device_name": self.device_name,
            "resource_id": self._resource_id,
            "resource_code": self.resource_code,
            "resource_name": self.resource_name,
            "metric": self._metric,
            "metric_label": self.metric_label,
            "value": self._value,
            "unit": self._unit,
            "display_value": self.display_value(),
            "severity": self._severity,
            "recorded_at": to_db(self._recorded_at),
            "recorded_display": human_time(self._recorded_at),
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<IoTReading %s=%s %s>" % (self._metric, self._value, self._severity)
