from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    """Get an item from a dictionary by key."""
    if not d:
        return None
    return d.get(str(key))

@register.filter
def underscore_to_space(value):
    """Replace underscores with spaces in a string.
    Usage: {{ value|underscore_to_space }}
    """
    if not value:
        return value
    return str(value).replace('_', ' ')


