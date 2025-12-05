from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from core.view_utils import get_list_context
from .models import UserRole, UserProfile, SystemConfiguration
from .forms import UserForm, UserRoleForm, SystemConfigurationForm
from jobs.models import JobSelectionOption
from jobs.forms import JobSelectionOptionForm


def user_has_permission(user, permission):
    """Check if user has a specific permission via their role."""
    if user.is_superuser:
        return True
    
    profile = getattr(user, 'profile', None)
    if not profile or not profile.role:
        return False
    
    return getattr(profile.role, permission, False)


def permission_required(permission):
    """Decorator to check if user has a specific permission."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not user_has_permission(request.user, permission):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('jobs:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def settings_index(request):
    """Main settings page with tabs."""
    # Check if user has any settings permissions
    profile = getattr(request.user, 'profile', None)
    
    if not request.user.is_superuser:
        if not profile or not profile.role:
            messages.error(request, "You don't have permission to access settings.")
            return redirect('jobs:home')
        
        role = profile.role
        has_any_permission = any([
            role.can_manage_users,
            role.can_manage_roles,
            role.can_manage_system_config,
        ])
        
        if not has_any_permission:
            messages.error(request, "You don't have permission to access settings.")
            return redirect('jobs:home')
    
    # Get active tab from query parameter
    active_tab = request.GET.get('tab', 'users')
    
    # Get system configuration
    system_config = SystemConfiguration.get_config()
    
    context = {
        'active_tab': active_tab,
        'system_config': system_config,
    }
    
    return render(request, 'settings_app/settings_index.html', context)


@login_required
@permission_required('can_manage_users')
def users_list_data(request):
    """Return user list data for the users tab."""
    # Get all users with their profiles
    users_queryset = User.objects.select_related('profile', 'profile__role').all()
    
    # Get list context with search, sorting, and pagination
    context = get_list_context(
        queryset=users_queryset,
        request=request,
        search_fields=['username', 'first_name', 'last_name', 'email'],
        sort_fields={'username', '-username', 'email', '-email', 'first_name', '-first_name', 
                    'last_name', '-last_name', 'date_joined', '-date_joined', 'last_login', '-last_login'},
        default_sort=['-date_joined'],
        per_page=25
    )
    
    # Rename object_list to items for template compatibility
    context['items'] = context.pop('object_list')
    
    return render(request, 'settings_app/partials/users_table.html', context)


@login_required
@permission_required('can_manage_users')
def user_create(request):
    """Create a new user."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'userUpdated'})
        else:
            return render(request, 'settings_app/modals/user_modal.html', {
                'form': form,
                'modal_title': 'Create User',
            })
    else:
        form = UserForm()
    
    return render(request, 'settings_app/modals/user_modal.html', {
        'form': form,
        'modal_title': 'Create User',
    })


@login_required
@permission_required('can_manage_users')
def user_edit(request, pk):
    """Edit an existing user."""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user, instance_id=pk)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'userUpdated'})
        else:
            return render(request, 'settings_app/modals/user_modal.html', {
                'form': form,
                'modal_title': 'Edit User',
                'edit_user': user,
            })
    else:
        form = UserForm(instance=user, instance_id=pk)
    
    return render(request, 'settings_app/modals/user_modal.html', {
        'form': form,
        'modal_title': 'Edit User',
        'edit_user': user,
    })


@login_required
@permission_required('can_manage_users')
@require_http_methods(["POST"])
def user_delete(request, pk):
    """Delete a user."""
    user = get_object_or_404(User, pk=pk)
    
    # Don't allow users to delete themselves
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('settings_app:settings_index')
    
    username = user.username
    user.delete()
    messages.success(request, f"User '{username}' deleted successfully.")
    return redirect('settings_app:settings_index')


@login_required
@permission_required('can_manage_users')
@require_http_methods(["POST"])
def user_toggle_active(request, pk):
    """Toggle user active status."""
    user = get_object_or_404(User, pk=pk)
    
    # Don't allow users to deactivate themselves
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return JsonResponse({'success': False, 'error': 'Cannot deactivate own account'})
    
    user.is_active = not user.is_active
    user.save()
    
    return JsonResponse({'success': True, 'is_active': user.is_active})


@login_required
def roles_list_data(request):
    """Return role list data for the roles tab."""
    # Check permission
    if not user_has_permission(request.user, 'can_manage_roles'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    roles_queryset = UserRole.objects.all()
    
    # Get list context with search, sorting, and pagination
    context = get_list_context(
        queryset=roles_queryset,
        request=request,
        search_fields=['name', 'description'],
        sort_fields={'name', '-name', 'is_system_role', '-is_system_role'},
        default_sort=['name'],
        per_page=25
    )
    
    # Rename object_list to items for template compatibility
    context['items'] = context.pop('object_list')
    
    return render(request, 'settings_app/partials/roles_table.html', context)


@login_required
@permission_required('can_manage_roles')
def role_create(request):
    """Create a new role."""
    if request.method == 'POST':
        form = UserRoleForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'roleUpdated'})
        else:
            return render(request, 'settings_app/modals/role_modal.html', {
                'form': form,
                'modal_title': 'Create Role',
            })
    else:
        form = UserRoleForm()
    
    return render(request, 'settings_app/modals/role_modal.html', {
        'form': form,
        'modal_title': 'Create Role',
    })


@login_required
@permission_required('can_manage_roles')
def role_edit(request, pk):
    """Edit an existing role."""
    role = get_object_or_404(UserRole, pk=pk)
    
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'roleUpdated'})
        else:
            return render(request, 'settings_app/modals/role_modal.html', {
                'form': form,
                'modal_title': 'Edit Role',
                'role': role,
            })
    else:
        form = UserRoleForm(instance=role)
    
    return render(request, 'settings_app/modals/role_modal.html', {
        'form': form,
        'modal_title': 'Edit Role',
        'role': role,
    })


@login_required
@permission_required('can_manage_roles')
@require_http_methods(["POST"])
def role_delete(request, pk):
    """Delete a role."""
    role = get_object_or_404(UserRole, pk=pk)
    
    # Don't allow deletion of system roles
    if role.is_system_role:
        messages.error(request, "System roles cannot be deleted.")
        return redirect('settings_app:settings_index')
    
    # Check if role is in use
    if role.user_profiles.exists():
        messages.error(request, f"Cannot delete role '{role.name}' because it is assigned to users.")
        return redirect('settings_app:settings_index')
    
    role_name = role.name
    role.delete()
    messages.success(request, f"Role '{role_name}' deleted successfully.")
    return redirect('settings_app:settings_index')


@login_required
@permission_required('can_manage_system_config')
def system_config_edit(request):
    """Edit system configuration."""
    config = SystemConfiguration.get_config()
    
    if request.method == 'POST':
        form = SystemConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            return redirect('settings_app:settings_index')
    else:
        form = SystemConfigurationForm(instance=config)
    
    return render(request, 'settings_app/partials/system_config_form.html', {
        'form': form,
    })


# ===================================
# Job Selection Options Views
# ===================================

@login_required
def selection_options_list(request):
    """Return selection options list data for the job options tab."""
    context = {
        'parts_selection': JobSelectionOption.objects.filter(group='parts_selection').order_by('sort_order', 'name'),
        'block_build_lists': JobSelectionOption.objects.filter(group='block_build_lists').order_by('sort_order', 'name'),
        'head_build_lists': JobSelectionOption.objects.filter(group='head_build_lists').order_by('sort_order', 'name'),
        'item_selection': JobSelectionOption.objects.filter(group='item_selection').order_by('sort_order', 'name'),
    }
    return render(request, 'settings_app/partials/selection_options_content.html', context)


@login_required
@require_http_methods(["GET"])
def selection_option_create_modal(request):
    """Render create modal for job selection option."""
    form = JobSelectionOptionForm()
    context = {
        'form': form,
        'title': 'Add Job Selection Option',
        'is_create': True,
    }
    return render(request, 'settings_app/modals/selection_option_modal.html', context)


@login_required
@require_http_methods(["POST"])
def selection_option_create(request):
    """Create a new job selection option."""
    form = JobSelectionOptionForm(request.POST)
    
    if form.is_valid():
        form.save()
        # Return updated list - trigger full page reload
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    
    # Return form with errors
    context = {
        'form': form,
        'title': 'Add Job Selection Option',
        'is_create': True,
    }
    return render(request, 'settings_app/modals/selection_option_modal.html', context, status=400)


@login_required
@require_http_methods(["GET"])
def selection_option_update_modal(request, pk):
    """Render update modal for job selection option."""
    option = get_object_or_404(JobSelectionOption, pk=pk)
    form = JobSelectionOptionForm(instance=option)
    context = {
        'form': form,
        'option': option,
        'title': 'Edit Job Selection Option',
        'is_create': False,
    }
    return render(request, 'settings_app/modals/selection_option_modal.html', context)


@login_required
@require_http_methods(["POST"])
def selection_option_update(request, pk):
    """Update an existing job selection option."""
    option = get_object_or_404(JobSelectionOption, pk=pk)
    form = JobSelectionOptionForm(request.POST, instance=option)
    
    if form.is_valid():
        form.save()
        # Return updated list - trigger full page reload
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    
    # Return form with errors
    context = {
        'form': form,
        'option': option,
        'title': 'Edit Job Selection Option',
        'is_create': False,
    }
    return render(request, 'settings_app/modals/selection_option_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def selection_option_delete(request, pk):
    """Delete a job selection option."""
    option = get_object_or_404(JobSelectionOption, pk=pk)
    option.delete()
    return redirect('/settings/?tab=job_options')


# Selection Option Search Modals
@login_required
@require_http_methods(["GET"])
def so_part_search_modal(request):
    """Render part search modal for selection options."""
    return render(request, 'settings_app/partials/so_part_search_modal.html')


@login_required
@require_http_methods(["GET"])
def so_part_search_results(request):
    """Search parts for selection options."""
    from inventory.models import Part
    query = request.GET.get('q', '').strip()
    parts = []
    
    if query:
        parts = Part.objects.filter(
            Q(part_number__icontains=query) | 
            Q(name__icontains=query)
        )[:50]
    
    context = {
        'parts': parts,
        'query': query,
    }
    return render(request, 'settings_app/partials/so_part_search_results.html', context)


@login_required
@require_http_methods(["GET"])
def so_kit_search_modal(request):
    """Render kit search modal for selection options."""
    return render(request, 'settings_app/partials/so_kit_search_modal.html')


@login_required
@require_http_methods(["GET"])
def so_kit_search_results(request):
    """Search kits for selection options."""
    from inventory.models import Kit
    query = request.GET.get('q', '').strip()
    kits = []
    
    if query:
        kits = Kit.objects.filter(
            Q(name__icontains=query) |
            Q(notes__icontains=query)
        )[:50]
    
    context = {
        'kits': kits,
        'query': query,
    }
    return render(request, 'settings_app/partials/so_kit_search_results.html', context)


@login_required
@require_http_methods(["GET"])
def so_buildlist_search_modal(request):
    """Render build list search modal for selection options."""
    return render(request, 'settings_app/partials/so_buildlist_search_modal.html')


@login_required
@require_http_methods(["GET"])
def so_buildlist_search_results(request):
    """Search build lists for selection options."""
    from inventory.models import BuildList
    query = request.GET.get('q', '').strip()
    buildlists = []
    
    if query:
        buildlists = BuildList.objects.filter(
            Q(name__icontains=query) |
            Q(notes__icontains=query)
        )[:50]
    
    context = {
        'buildlists': buildlists,
        'query': query,
    }
    return render(request, 'settings_app/partials/so_buildlist_search_results.html', context)


# ===================================
# Part Categories Views
# ===================================

@login_required
def part_categories_list(request):
    """Return part categories list data for the settings tab."""
    from inventory.models import PartCategory
    from django.db.models import Count
    
    categories = PartCategory.objects.annotate(
        field_count=Count('attributes')
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    return render(request, 'settings_app/partials/part_categories_table.html', context)


@login_required
@require_http_methods(["GET"])
def part_category_create_modal(request):
    """Render create modal for part category."""
    from inventory.forms import PartCategoryForm
    form = PartCategoryForm()
    context = {
        'form': form,
        'title': 'Create Part Category',
        'is_create': True,
    }
    return render(request, 'settings_app/modals/part_category_modal.html', context)


@login_required
@require_http_methods(["POST"])
def part_category_create(request):
    """Create a new part category."""
    from inventory.forms import PartCategoryForm
    form = PartCategoryForm(request.POST)
    
    if form.is_valid():
        form.save()
        return HttpResponse(status=204, headers={'HX-Trigger': 'categoryUpdated'})
    
    # Return form with errors
    context = {
        'form': form,
        'title': 'Create Part Category',
        'is_create': True,
    }
    return render(request, 'settings_app/modals/part_category_modal.html', context, status=400)


@login_required
@require_http_methods(["GET"])
def part_category_edit_modal(request, pk):
    """Render edit modal for part category."""
    from inventory.models import PartCategory
    from inventory.forms import PartCategoryForm
    category = get_object_or_404(PartCategory, pk=pk)
    form = PartCategoryForm(instance=category)
    context = {
        'form': form,
        'category': category,
        'title': 'Edit Part Category',
        'is_create': False,
    }
    return render(request, 'settings_app/modals/part_category_modal.html', context)


@login_required
@require_http_methods(["POST"])
def part_category_update(request, pk):
    """Update an existing part category."""
    from inventory.models import PartCategory
    from inventory.forms import PartCategoryForm
    category = get_object_or_404(PartCategory, pk=pk)
    form = PartCategoryForm(request.POST, instance=category)
    
    if form.is_valid():
        form.save()
        return HttpResponse(status=204, headers={'HX-Trigger': 'categoryUpdated'})
    
    # Return form with errors
    context = {
        'form': form,
        'category': category,
        'title': 'Edit Part Category',
        'is_create': False,
    }
    return render(request, 'settings_app/modals/part_category_modal.html', context, status=400)


@login_required
@require_http_methods(["POST"])
def part_category_delete(request, pk):
    """Delete a part category."""
    from inventory.models import PartCategory
    category = get_object_or_404(PartCategory, pk=pk)
    
    # Check if category is in use
    if category.parts.exists():
        messages.error(request, f"Cannot delete category '{category.name}' because it is assigned to parts.")
        return HttpResponse(status=400)
    
    category.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': 'categoryUpdated'})


@login_required
def part_category_detail(request, pk):
    """Render category detail page with attributes."""
    from inventory.models import PartCategory
    category = get_object_or_404(PartCategory, pk=pk)
    attributes = category.attributes.all().order_by('sort_order', 'name')
    
    context = {
        'category': category,
        'attributes': attributes,
    }
    return render(request, 'settings_app/part_category_detail.html', context)


@login_required
@require_http_methods(["GET"])
def part_attribute_create_modal(request, category_pk):
    """Render create modal for part attribute."""
    from inventory.models import PartCategory
    category = get_object_or_404(PartCategory, pk=category_pk)
    context = {
        'category': category,
        'title': 'Add Field',
        'is_create': True,
    }
    return render(request, 'settings_app/modals/part_attribute_modal.html', context)


@login_required
@require_http_methods(["POST"])
def part_attribute_create(request, category_pk):
    """Create a new part attribute."""
    from inventory.models import PartCategory, PartAttribute
    category = get_object_or_404(PartCategory, pk=category_pk)
    
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    data_type = request.POST.get('data_type', 'text')
    unit = request.POST.get('unit', '').strip()
    is_required = request.POST.get('is_required') == 'on'
    sort_order = int(request.POST.get('sort_order', 0) or 0)
    help_text = request.POST.get('help_text', '').strip()
    
    if not name:
        messages.error(request, "Field name is required.")
        return HttpResponse(status=400)
    
    # Auto-generate code if not provided
    if not code:
        code = name.lower().replace(' ', '_').replace('-', '_')
        import re
        code = re.sub(r'[^a-z0-9_]', '', code)
    
    PartAttribute.objects.create(
        category=category,
        name=name,
        code=code,
        data_type=data_type,
        unit=unit,
        is_required=is_required,
        sort_order=sort_order,
        help_text=help_text,
    )
    
    return HttpResponse(status=204, headers={'HX-Trigger': 'attributeUpdated'})


@login_required
@require_http_methods(["GET"])
def part_attribute_edit_modal(request, category_pk, attribute_pk):
    """Render edit modal for part attribute."""
    from inventory.models import PartCategory, PartAttribute
    category = get_object_or_404(PartCategory, pk=category_pk)
    attribute = get_object_or_404(PartAttribute, pk=attribute_pk, category=category)
    context = {
        'category': category,
        'attribute': attribute,
        'title': 'Edit Field',
        'is_create': False,
    }
    return render(request, 'settings_app/modals/part_attribute_modal.html', context)


@login_required
@require_http_methods(["POST"])
def part_attribute_update(request, category_pk, attribute_pk):
    """Update an existing part attribute."""
    from inventory.models import PartCategory, PartAttribute
    category = get_object_or_404(PartCategory, pk=category_pk)
    attribute = get_object_or_404(PartAttribute, pk=attribute_pk, category=category)
    
    attribute.name = request.POST.get('name', '').strip()
    attribute.code = request.POST.get('code', '').strip()
    attribute.data_type = request.POST.get('data_type', 'text')
    attribute.unit = request.POST.get('unit', '').strip()
    attribute.is_required = request.POST.get('is_required') == 'on'
    attribute.sort_order = int(request.POST.get('sort_order', 0) or 0)
    attribute.help_text = request.POST.get('help_text', '').strip()
    
    if not attribute.name:
        messages.error(request, "Field name is required.")
        return HttpResponse(status=400)
    
    attribute.save()
    return HttpResponse(status=204, headers={'HX-Trigger': 'attributeUpdated'})


@login_required
@require_http_methods(["POST"])
def part_attribute_delete(request, category_pk, attribute_pk):
    """Delete a part attribute."""
    from inventory.models import PartCategory, PartAttribute
    category = get_object_or_404(PartCategory, pk=category_pk)
    attribute = get_object_or_404(PartAttribute, pk=attribute_pk, category=category)
    
    attribute.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': 'attributeUpdated'})


@login_required
@require_http_methods(["GET"])
def part_attribute_choice_create_modal(request, category_pk, attribute_pk):
    """Render create modal for attribute choice."""
    from inventory.models import PartCategory, PartAttribute
    category = get_object_or_404(PartCategory, pk=category_pk)
    attribute = get_object_or_404(PartAttribute, pk=attribute_pk, category=category)
    context = {
        'category': category,
        'attribute': attribute,
        'title': 'Add Choice',
        'is_create': True,
    }
    return render(request, 'settings_app/modals/part_attribute_choice_modal.html', context)


@login_required
@require_http_methods(["POST"])
def part_attribute_choice_create(request, category_pk, attribute_pk):
    """Create a new attribute choice."""
    from inventory.models import PartCategory, PartAttribute, PartAttributeChoice
    category = get_object_or_404(PartCategory, pk=category_pk)
    attribute = get_object_or_404(PartAttribute, pk=attribute_pk, category=category)
    
    value = request.POST.get('value', '').strip()
    label = request.POST.get('label', '').strip()
    sort_order = int(request.POST.get('sort_order', 0) or 0)
    
    if not value or not label:
        messages.error(request, "Value and label are required.")
        return HttpResponse(status=400)
    
    PartAttributeChoice.objects.create(
        attribute=attribute,
        value=value,
        label=label,
        sort_order=sort_order,
    )
    
    return HttpResponse(status=204, headers={'HX-Trigger': 'attributeUpdated'})


@login_required
@require_http_methods(["POST"])
def part_attribute_choice_delete(request, category_pk, attribute_pk, choice_pk):
    """Delete an attribute choice."""
    from inventory.models import PartCategory, PartAttribute, PartAttributeChoice
    category = get_object_or_404(PartCategory, pk=category_pk)
    attribute = get_object_or_404(PartAttribute, pk=attribute_pk, category=category)
    choice = get_object_or_404(PartAttributeChoice, pk=choice_pk, attribute=attribute)
    
    choice.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': 'attributeUpdated'})
