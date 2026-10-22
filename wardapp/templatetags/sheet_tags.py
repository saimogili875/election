from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def get_attr(obj, attr_name):
    if hasattr(obj, str(attr_name)):
        return getattr(obj, str(attr_name))
    elif isinstance(obj, dict):
        return obj.get(attr_name)
    return ''
