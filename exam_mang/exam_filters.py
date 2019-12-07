# exam_mang/templatetags/exam_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        # Convert to Decimal for accurate calculations
        if isinstance(value, (int, float, Decimal)) and isinstance(arg, (int, float, Decimal)):
            return Decimal(str(value)) * Decimal(str(arg))
        return float(value) * float(arg)
    except (ValueError, TypeError, AttributeError):
        try:
            return 0
        except:
            return ""

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    return dictionary.get(key, '')

@register.filter
def format_percentage(value):
    """Format a decimal as percentage"""
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return "0.0%"

@register.filter
def format_grade_point(value):
    """Format grade point with 2 decimal places"""
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "0.00"

@register.filter
def check_exam_applicable(subject_mark_component, exam_type):
    """Check if an exam type is applicable for a subject"""
    if exam_type == 'lab':
        return subject_mark_component.lab_percentage > 0
    elif exam_type == 'viva':
        return subject_mark_component.viva_percentage > 0
    else:
        # For other exam types, they're always applicable if they exist
        return True

@register.filter
def get_exam_marks(comprehensive_result, exam_type):
    """Get marks for a specific exam type from comprehensive result"""
    marks_field = f"{exam_type}_marks"
    return getattr(comprehensive_result, marks_field, Decimal('0.00'))