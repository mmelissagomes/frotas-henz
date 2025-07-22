from django import template
register = template.Library()

@register.filter
def get_item(value, arg):
    try:
        if isinstance(value, dict):
            return value.get(arg, "")
        elif isinstance(value, (list, tuple)):
            return value[int(arg)]
    except (KeyError, IndexError, ValueError, TypeError):
        return ""
    return ""

