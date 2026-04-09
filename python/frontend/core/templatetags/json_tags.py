"""Template filters for safe JSON serialization."""
import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="safe_json")
def safe_json(value):
    """Serialize a Python object to JSON, safe for embedding in <script> tags."""
    try:
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError):
        return mark_safe("{}")
