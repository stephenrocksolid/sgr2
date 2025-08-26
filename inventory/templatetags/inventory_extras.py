from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    return dictionary.get(key)


@register.filter
def get_value_text(attr_value):
    """Get the text value from a PartAttributeValue."""
    if attr_value and hasattr(attr_value, 'value_text'):
        return attr_value.value_text
    return ''


@register.filter
def get_value_int(attr_value):
    """Get the integer value from a PartAttributeValue."""
    if attr_value and hasattr(attr_value, 'value_int') and attr_value.value_int is not None:
        return attr_value.value_int
    return ''


@register.filter
def get_value_dec(attr_value):
    """Get the decimal value from a PartAttributeValue."""
    if attr_value and hasattr(attr_value, 'value_dec') and attr_value.value_dec is not None:
        return floatformat(attr_value.value_dec, 6)
    return ''


@register.filter
def get_value_bool(attr_value):
    """Get the boolean value from a PartAttributeValue."""
    if attr_value and hasattr(attr_value, 'value_bool'):
        return attr_value.value_bool
    return False


@register.filter
def get_value_date(attr_value):
    """Get the date value from a PartAttributeValue."""
    if attr_value and hasattr(attr_value, 'value_date') and attr_value.value_date:
        return attr_value.value_date
    return None


@register.filter
def get_choice_value(attr_value):
    """Get the choice value from a PartAttributeValue."""
    if attr_value and hasattr(attr_value, 'choice') and attr_value.choice:
        return attr_value.choice.value
    return ''


@register.filter
def get_value_for_edit(attr_value):
    """Get the appropriate value for editing based on data type."""
    if not attr_value:
        return ''
    
    if hasattr(attr_value, 'value_text') and attr_value.value_text:
        return attr_value.value_text
    elif hasattr(attr_value, 'value_int') and attr_value.value_int is not None:
        return str(attr_value.value_int)
    elif hasattr(attr_value, 'value_dec') and attr_value.value_dec is not None:
        return str(attr_value.value_dec)
    elif hasattr(attr_value, 'value_bool') and attr_value.value_bool is not None:
        return 'true' if attr_value.value_bool else 'false'
    elif hasattr(attr_value, 'value_date') and attr_value.value_date:
        return attr_value.value_date.strftime('%Y-%m-%d')
    elif hasattr(attr_value, 'choice') and attr_value.choice:
        return attr_value.choice.value
    
    return ''
