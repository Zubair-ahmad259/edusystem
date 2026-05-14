# exam/templatetags/exam_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return None
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

@register.filter
def attr(obj, attr_name):
    """Get attribute from object"""
    if obj is None:
        return ''
    return getattr(obj, attr_name, '')