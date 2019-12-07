from django import template

register = template.Library()

@register.filter
def calculate_total(fees):
    """Calculate total fees for a student"""
    total = 0
    for fee in fees:
        total += fee.total_fee()
    return total