from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    """Get an item from a dictionary or Django form by key."""
    if not obj:
        return None
    
    # Handle Django forms
    if hasattr(obj, 'fields'):
        return obj.fields.get(str(key))
    
    # Handle dictionaries
    if hasattr(obj, 'get'):
        return obj.get(str(key))
    
    return None

@register.filter
def underscore_to_space(value):
    """Replace underscores with spaces in a string.
    Usage: {{ value|underscore_to_space }}
    """
    if not value:
        return value
    return str(value).replace('_', ' ')



