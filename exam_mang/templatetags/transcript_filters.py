from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sum_obtained_marks(results):
    """Calculate sum of obtained marks for a semester"""
    total = 0
    for result in results:
        if hasattr(result, 'obtained_marks') and result.obtained_marks:
            try:
                total += float(result.obtained_marks)
            except (ValueError, TypeError):
                continue
    return total

@register.filter
def calculate_semester_gpa(results):
    """Calculate GPA for a semester"""
    total_grade_points = 0
    total_credits = 0
    
    for result in results:
        if hasattr(result, 'grade_point') and result.grade_point and hasattr(result, 'credit_hours') and result.credit_hours:
            try:
                grade_point = float(result.grade_point)
                credit_hours = float(result.credit_hours)
                total_grade_points += grade_point * credit_hours
                total_credits += credit_hours
            except (ValueError, TypeError):
                continue
    
    if total_credits > 0:
        return total_grade_points / total_credits
    return 0