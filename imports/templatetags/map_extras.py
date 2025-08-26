from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    """Get an item from a dictionary by key."""
    if not d:
        return None
    return d.get(str(key))

