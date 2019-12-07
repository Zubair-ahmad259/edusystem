# timetables/templatetags/timetable_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    return dictionary.get(key, [])

@register.filter
def filter_day(queryset, day):
    """Filter timetable entries by day"""
    return [entry for entry in queryset if entry.time_slot.day == day]

@register.filter
def length(queryset):
    """Get length of queryset"""
    return queryset.count() if hasattr(queryset, 'count') else len(queryset)

@register.filter
def divisibleby(value, arg):
    """Check if value is divisible by arg"""
    try:
        return (value / arg) * 100
    except:
        return 0