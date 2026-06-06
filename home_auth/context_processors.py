def user_role_context(request):
    """Add user role and permissions to all templates"""
    context = {
        'user_role': None,
        'is_demo_user': False,
        'can_edit': False,
        'can_delete': False,
        'can_add': False,
        'can_view': True,
    }
    
    if request.user.is_authenticated:
        user = request.user
        
        # Check if demo user
        if user.username == 'demo_user':
            context['is_demo_user'] = True
            context['can_view'] = True
            context['can_edit'] = False
            context['can_delete'] = False
            context['can_add'] = False
            context['user_role'] = 'Demo Viewer'
            return context
        
        # For real users - set permissions based on role
        try:
            from head.models import AdminProfile
            admin_profile = AdminProfile.objects.get(user=user)
            role = admin_profile.role
            context['user_role'] = role
            
            if role == 'Office Clerk':
                context['can_edit'] = False
                context['can_delete'] = False
                context['can_add'] = False
            elif role == 'Accounts':
                context['can_edit'] = True
                context['can_delete'] = False
                context['can_add'] = True
            else:
                context['can_edit'] = True
                context['can_delete'] = True
                context['can_add'] = True
        except:
            if hasattr(user, 'teacher') and user.teacher:
                context['user_role'] = 'Teacher'
                context['can_edit'] = True
            elif hasattr(user, 'student') and user.student:
                context['user_role'] = 'Student'
                context['can_edit'] = False
            elif user.is_superuser or user.is_admin:
                context['user_role'] = 'Admin'
                context['can_edit'] = True
                context['can_delete'] = True
                context['can_add'] = True
    
    return context