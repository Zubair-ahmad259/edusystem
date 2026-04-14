from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from student.models import Discipline
from .models import AdminProfile

# Import features temporarily disabled due to openpyxl dependency
def import_admin_profiles(request):
    messages.error(request, "Import feature temporarily disabled. Please use admin panel to add profiles.")
    return redirect('admin_profile:admin_profile_list')

def download_sample_excel(request):
    messages.error(request, "Export feature temporarily disabled.")
    return redirect('admin_profile:admin_profile_list')

@login_required
def admin_profile_list(request):
    """List all admin profiles with search and filter options"""
    admin_profiles = AdminProfile.objects.select_related('discipline').all()
    
    # Clear import errors from session if requested
    if request.GET.get('clear_errors'):
        if 'import_errors' in request.session:
            del request.session['import_errors']
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        admin_profiles = admin_profiles.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(father_name__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        admin_profiles = admin_profiles.filter(role=role_filter)
    
    # Filter by discipline
    discipline_filter = request.GET.get('discipline', '')
    if discipline_filter:
        admin_profiles = admin_profiles.filter(discipline_id=discipline_filter)
    
    # Pagination
    paginator = Paginator(admin_profiles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all disciplines for filter dropdown
    disciplines = Discipline.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'discipline_filter': discipline_filter,
        'disciplines': disciplines,
        'role_choices': AdminProfile._meta.get_field('role').choices,
        'import_errors': request.session.get('import_errors', []),
    }
    return render(request, 'admin_profile/admin_profile_list.html', context)

@login_required
def admin_profile_detail(request, pk):
    """View single admin profile details"""
    admin_profile = get_object_or_404(
        AdminProfile.objects.select_related('discipline'), 
        pk=pk
    )
    return render(request, 'admin_profile/admin_profile_detail.html', {
        'admin_profile': admin_profile
    })

@login_required
def admin_profile_create(request):
    """Create a new admin profile"""
    if request.method == 'POST':
        try:
            # Check if email already exists
            email = request.POST.get('email')
            if AdminProfile.objects.filter(email=email).exists():
                messages.error(request, f'Email "{email}" already exists!')
                return redirect('admin_profile:admin_profile_create')
            
            # Create admin profile
            discipline_id = request.POST.get('discipline')
            discipline = Discipline.objects.get(id=discipline_id) if discipline_id else None
            
            AdminProfile.objects.create(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                father_name=request.POST.get('father_name'),
                contact_number=request.POST.get('contact_number'),
                email=email,
                discipline=discipline,
                role=request.POST.get('role'),
                address=request.POST.get('address')
            )
            
            messages.success(request, 'Admin profile created successfully!')
            return redirect('admin_profile:admin_profile_list')
                
        except Exception as e:
            messages.error(request, f'Error creating admin profile: {str(e)}')
    
    # GET request - show form
    disciplines = Discipline.objects.all()
    context = {
        'disciplines': disciplines,
        'role_choices': AdminProfile._meta.get_field('role').choices,
    }
    return render(request, 'admin_profile/admin_profile_form.html', context)

@login_required
def admin_profile_update(request, pk):
    """Update an existing admin profile"""
    admin_profile = get_object_or_404(AdminProfile, pk=pk)
    
    if request.method == 'POST':
        try:
            # Check if email is being changed and if it's unique
            new_email = request.POST.get('email')
            if new_email != admin_profile.email and AdminProfile.objects.filter(email=new_email).exists():
                messages.error(request, f'Email "{new_email}" already exists!')
                return redirect('admin_profile:admin_profile_update', pk=pk)
            
            # Update admin profile
            discipline_id = request.POST.get('discipline')
            admin_profile.discipline = Discipline.objects.get(id=discipline_id) if discipline_id else None
            
            admin_profile.first_name = request.POST.get('first_name')
            admin_profile.last_name = request.POST.get('last_name')
            admin_profile.father_name = request.POST.get('father_name')
            admin_profile.contact_number = request.POST.get('contact_number')
            admin_profile.email = new_email
            admin_profile.role = request.POST.get('role')
            admin_profile.address = request.POST.get('address')
            admin_profile.save()
            
            messages.success(request, 'Admin profile updated successfully!')
            return redirect('admin_profile:admin_profile_detail', pk=admin_profile.pk)
                
        except Exception as e:
            messages.error(request, f'Error updating admin profile: {str(e)}')
    
    # GET request - show form with current data
    disciplines = Discipline.objects.all()
    context = {
        'admin_profile': admin_profile,
        'disciplines': disciplines,
        'role_choices': AdminProfile._meta.get_field('role').choices,
    }
    return render(request, 'admin_profile/admin_profile_form.html', context)

@login_required
def admin_profile_delete(request, pk):
    """Delete an admin profile"""
    admin_profile = get_object_or_404(AdminProfile, pk=pk)
    
    if request.method == 'POST':
        try:
            email = admin_profile.email
            admin_profile.delete()
            messages.success(request, f'Admin profile for "{email}" deleted successfully!')
            return redirect('admin_profile:admin_profile_list')
        except Exception as e:
            messages.error(request, f'Error deleting admin profile: {str(e)}')
    
    return render(request, 'admin_profile/admin_profile_confirm_delete.html', {
        'admin_profile': admin_profile
    })

@login_required
def debug_admin_permissions(request):
    """Debug view to check admin permissions"""
    user = request.user
    
    # Check if user has admin profile
    try:
        admin_profile = AdminProfile.objects.get(email=user.email)
        has_admin_profile = True
        admin_role = admin_profile.role
    except AdminProfile.DoesNotExist:
        has_admin_profile = False
        admin_role = None
    
    # Get all user attributes
    user_attrs = {
        'username': user.username,
        'email': user.email,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'is_admin': getattr(user, 'is_admin', False),
        'has_admin_profile': has_admin_profile,
        'admin_role': admin_role,
    }
    
    # Get all available attributes
    all_attrs = {}
    for attr in dir(user):
        if not attr.startswith('_') and not callable(getattr(user, attr)):
            try:
                all_attrs[attr] = str(getattr(user, attr))
            except:
                all_attrs[attr] = "Error getting value"
    
    return JsonResponse({
        'user_attributes': user_attrs,
        'all_attributes': all_attrs,
    })
