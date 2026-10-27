"""JSON boundaries: unavailable numeric metrics are null, never NaN/Infinity."""
import math
from numbers import Integral, Real


def json_safe(value):
    """Return a copy; never rewrite a stored result while preparing a response."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        return float(value) if math.isfinite(value) else None
    return value
