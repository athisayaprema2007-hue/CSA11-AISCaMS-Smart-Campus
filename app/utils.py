"""Small shared helpers: time formatting and input validation primitives."""

from datetime import datetime, timedelta

from .exceptions import ValidationError

DB_FORMAT = "%Y-%m-%d %H:%M:%S"
INPUT_FORMATS = (DB_FORMAT, "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")
DAY_CODES = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def now():
    """Current local time truncated to whole seconds."""
    return datetime.now().replace(microsecond=0)


def to_db(value):
    """Serialise a datetime for storage/comparison in SQLite."""
    if value is None:
        return None
    if isinstance(value, str):
        return parse_datetime(value).strftime(DB_FORMAT)
    return value.strftime(DB_FORMAT)


def parse_datetime(value, field="timestamp"):
    """Parse a datetime accepting the formats produced by HTML inputs."""
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    if not value or not str(value).strip():
        raise ValidationError("%s is required." % field.capitalize(), {"field": field})
    text = str(value).strip().replace("T", " ")
    for fmt in (DB_FORMAT, "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValidationError(
        "%s must use the format YYYY-MM-DD HH:MM." % field.capitalize(), {"field": field}
    )


def human_time(value):
    """Render a timestamp for the user interface."""
    if not value:
        return "-"
    dt = parse_datetime(value) if isinstance(value, str) else value
    return dt.strftime("%d %b %Y, %H:%M")


def human_clock(value):
    if not value:
        return "-"
    dt = parse_datetime(value) if isinstance(value, str) else value
    return dt.strftime("%H:%M")


def day_code(value=None):
    dt = value or now()
    return DAY_CODES[dt.weekday()]


def hours_between(start, end):
    return round((end - start).total_seconds() / 3600.0, 2)


def add_hours(value, hours):
    return value + timedelta(hours=hours)


def require_text(value, field, minimum=1, maximum=500):
    """Validate and normalise a free text field."""
    text = (value or "").strip() if isinstance(value, str) else ""
    if len(text) < minimum:
        raise ValidationError(
            "%s must be at least %d characters." % (field.capitalize(), minimum),
            {"field": field},
        )
    if len(text) > maximum:
        raise ValidationError(
            "%s must be at most %d characters." % (field.capitalize(), maximum),
            {"field": field},
        )
    return text


def require_int(value, field, minimum=None, maximum=None):
    """Validate an integer field coming from a form or JSON payload."""
    if value is None or value == "":
        raise ValidationError("%s is required." % field.capitalize(), {"field": field})
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError("%s must be a whole number." % field.capitalize(), {"field": field})
    if minimum is not None and number < minimum:
        raise ValidationError(
            "%s must be at least %d." % (field.capitalize(), minimum), {"field": field}
        )
    if maximum is not None and number > maximum:
        raise ValidationError(
            "%s must be at most %d." % (field.capitalize(), maximum), {"field": field}
        )
    return number


def require_float(value, field, minimum=None, maximum=None):
    if value is None or value == "":
        raise ValidationError("%s is required." % field.capitalize(), {"field": field})
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError("%s must be a number." % field.capitalize(), {"field": field})
    if minimum is not None and number < minimum:
        raise ValidationError(
            "%s must be at least %s." % (field.capitalize(), minimum), {"field": field}
        )
    if maximum is not None and number > maximum:
        raise ValidationError(
            "%s must be at most %s." % (field.capitalize(), maximum), {"field": field}
        )
    return number


def require_choice(value, field, choices):
    text = (str(value).strip().upper() if value is not None else "")
    if text not in choices:
        raise ValidationError(
            "%s must be one of: %s." % (field.capitalize(), ", ".join(sorted(choices))),
            {"field": field},
        )
    return text
