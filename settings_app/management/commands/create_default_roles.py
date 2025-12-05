from django.core.management.base import BaseCommand
from settings_app.models import UserRole


class Command(BaseCommand):
    help = 'Create default user roles'

    def handle(self, *args, **options):
        # Admin role with all permissions
        admin_role, created = UserRole.objects.get_or_create(
            name='Admin',
            defaults={
                'description': 'Full system access with all permissions',
                'is_system_role': True,
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
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Admin role'))
        else:
            # Update existing admin role to have all permissions
            admin_role.is_system_role = True
            admin_role.can_view_jobs = True
            admin_role.can_edit_jobs = True
            admin_role.can_delete_jobs = True
            admin_role.can_manage_job_options = True
            admin_role.can_view_inventory = True
            admin_role.can_edit_inventory = True
            admin_role.can_delete_inventory = True
            admin_role.can_view_imports = True
            admin_role.can_create_imports = True
            admin_role.can_revert_imports = True
            admin_role.can_view_employees = True
            admin_role.can_edit_employees = True
            admin_role.can_delete_employees = True
            admin_role.can_manage_users = True
            admin_role.can_manage_roles = True
            admin_role.can_manage_system_config = True
            admin_role.can_view_reports = True
            admin_role.can_export_reports = True
            admin_role.save()
            self.stdout.write(self.style.SUCCESS(f'Updated Admin role'))

        # Manager role with most permissions except system settings
        manager_role, created = UserRole.objects.get_or_create(
            name='Manager',
            defaults={
                'description': 'Can manage jobs, inventory, and employees but not system settings',
                'is_system_role': True,
                'can_view_jobs': True,
                'can_edit_jobs': True,
                'can_delete_jobs': True,
                'can_manage_job_options': True,
                'can_view_inventory': True,
                'can_edit_inventory': True,
                'can_delete_inventory': True,
                'can_view_imports': True,
                'can_create_imports': True,
                'can_revert_imports': False,
                'can_view_employees': True,
                'can_edit_employees': True,
                'can_delete_employees': False,
                'can_manage_users': False,
                'can_manage_roles': False,
                'can_manage_system_config': False,
                'can_view_reports': True,
                'can_export_reports': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Manager role'))

        # Shop User role with basic permissions
        shop_user_role, created = UserRole.objects.get_or_create(
            name='Shop User',
            defaults={
                'description': 'Basic access to view and edit jobs and inventory',
                'is_system_role': True,
                'can_view_jobs': True,
                'can_edit_jobs': True,
                'can_delete_jobs': False,
                'can_manage_job_options': False,
                'can_view_inventory': True,
                'can_edit_inventory': True,
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
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Shop User role'))

        # View Only role
        view_only_role, created = UserRole.objects.get_or_create(
            name='View Only',
            defaults={
                'description': 'Read-only access to all modules',
                'is_system_role': True,
                'can_view_jobs': True,
                'can_edit_jobs': False,
                'can_delete_jobs': False,
                'can_manage_job_options': False,
                'can_view_inventory': True,
                'can_edit_inventory': False,
                'can_delete_inventory': False,
                'can_view_imports': True,
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
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created View Only role'))

        self.stdout.write(self.style.SUCCESS('Default roles setup complete!'))




