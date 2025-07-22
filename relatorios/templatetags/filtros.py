from django import template
register = template.Library()

@register.filter
def get_item(value, arg):
    """
    Puxa value[arg] de forma genérica:
    - Se for dict, tenta usar arg como int primeiro, depois como str.
    - Se for lista/tupla, usa arg convertido em int.
    """
    try:
        # primeiro, tenta usar arg como inteiro
        key = int(arg)
    except (ValueError, TypeError):
        key = arg

    try:
        if isinstance(value, dict):
            # se não achar por int, tenta por str
            return value.get(key, value.get(str(key), ""))
        elif isinstance(value, (list, tuple)):
            return value[key]
    except (KeyError, IndexError, TypeError):
        return ""
    return ""
