from django import template
from django.utils import timezone
from ..models import AssignmentSubmission

register = template.Library()

@register.filter
def get_user_submission(assignment, user):
    """Get the submission for a specific assignment and user"""
    try:
        if user.is_authenticated:
            # Check if user is teacher or student
            if hasattr(user, 'teacher') or hasattr(user, 'student'):
                submission = AssignmentSubmission.objects.filter(
                    assignment=assignment,
                    student=user
                ).first()
                return submission
    except Exception as e:
        print(f"Error getting submission: {e}")
    return None

@register.filter
def get_submission_status(assignment, user):
    """Get submission status as string"""
    submission = get_user_submission(assignment, user)
    if submission:
        if submission.status == 'submitted':
            return 'submitted'
        elif submission.status == 'graded':
            return 'graded'
        else:
            return 'pending'
    return 'not_submitted'

@register.filter
def get_submission_grade(assignment, user):
    """Get submission grade"""
    submission = get_user_submission(assignment, user)
    if submission and submission.marks_obtained:
        return f"{submission.marks_obtained}/{submission.assignment.total_marks}"
    return 'Not graded'

@register.filter
def can_submit(assignment, user):
    """Check if user can submit assignment"""
    submission = get_user_submission(assignment, user)
    if submission:
        return False
    return assignment.status == 'active' and assignment.due_date >= timezone.now()