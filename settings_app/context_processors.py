def user_permissions(request):
    """Add user permissions and notification count to template context."""
    if not request.user.is_authenticated:
        return {}
    
    # Get unread notification count for sidebar indicator
    from jobs.models import JobNotification
    unread_notification_count = JobNotification.objects.filter(
        user=request.user,
        read_at__isnull=True
    ).count()
    
    # Superusers have all permissions
    if request.user.is_superuser:
        return {
            'unread_notification_count': unread_notification_count,
            'user_permissions': {
                'can_view_jobs': True,
                'can_edit_jobs': True,
                'can_delete_jobs': True,
                'can_manage_job_options': True,
                'can_view_inventory': True,
                'can_edit_inventory': True,
                'can_delete_inventory': True,
                'can_view_imports': True,
                'can_create_imports': True,
                'can_revert_imports': True,
                'can_view_employees': True,
                'can_edit_employees': True,
                'can_delete_employees': True,
                'can_manage_users': True,
                'can_manage_roles': True,
                'can_manage_system_config': True,
                'can_view_reports': True,
                'can_export_reports': True,
            }
        }
    
    # Get user's role and permissions
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.role:
        # Default minimal permissions if no role assigned
        return {
            'unread_notification_count': unread_notification_count,
            'user_permissions': {
                'can_view_jobs': True,
                'can_edit_jobs': False,
                'can_delete_jobs': False,
                'can_manage_job_options': False,
                'can_view_inventory': True,
                'can_edit_inventory': False,
                'can_delete_inventory': False,
                'can_view_imports': False,
                'can_create_imports': False,
                'can_revert_imports': False,
                'can_view_employees': True,
                'can_edit_employees': False,
                'can_delete_employees': False,
                'can_manage_users': False,
                'can_manage_roles': False,
                'can_manage_system_config': False,
                'can_view_reports': True,
                'can_export_reports': False,
            }
        }
    
    role = profile.role
    return {
        'unread_notification_count': unread_notification_count,
        'user_permissions': {
            'can_view_jobs': role.can_view_jobs,
            'can_edit_jobs': role.can_edit_jobs,
            'can_delete_jobs': role.can_delete_jobs,
            'can_manage_job_options': role.can_manage_job_options,
            'can_view_inventory': role.can_view_inventory,
            'can_edit_inventory': role.can_edit_inventory,
            'can_delete_inventory': role.can_delete_inventory,
            'can_view_imports': role.can_view_imports,
            'can_create_imports': role.can_create_imports,
            'can_revert_imports': role.can_revert_imports,
            'can_view_employees': role.can_view_employees,
            'can_edit_employees': role.can_edit_employees,
            'can_delete_employees': role.can_delete_employees,
            'can_manage_users': role.can_manage_users,
            'can_manage_roles': role.can_manage_roles,
            'can_manage_system_config': role.can_manage_system_config,
            'can_view_reports': role.can_view_reports,
            'can_export_reports': role.can_export_reports,
        }
    }




