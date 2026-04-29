# home_auth/context_processors.py

def user_role_context(request):
    """Add user role to all templates"""
    if request.user.is_authenticated:
        # Check for admin profile role
        if hasattr(request.user, 'admin_profile') and request.user.admin_profile:
            role = request.user.admin_profile.role
            print(f"User Role from context processor: {role}")  # Debug print
            return {'user_role': role}
        
        # Check for superuser or admin
        if request.user.is_superuser:
            return {'user_role': 'superuser'}
        if request.user.is_admin:
            return {'user_role': 'admin'}
        if request.user.is_teacher:
            return {'user_role': 'teacher'}
        if request.user.is_student:
            return {'user_role': 'student'}
    
    return {'user_role': None}