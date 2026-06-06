from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def demo_block(view_func):
    """Decorator to block demo user from making changes"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.username == 'demo_user' and request.method == 'POST':
            messages.error(request, '⚠️ Demo Mode: View-only access. You cannot make changes.')
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        return view_func(request, *args, **kwargs)
    return wrapper

def is_demo_user(user):
    """Check if user is demo account"""
    return user.username == 'demo_user'