from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key, {})

@register.filter
def get_remarks(dictionary, student_id):
    """Get remarks for a student"""
    if hasattr(dictionary, 'get'):
        record = dictionary.get(student_id, {})
        if hasattr(record, 'remarks'):
            return record.remarks
    return ''