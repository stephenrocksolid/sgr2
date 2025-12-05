from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from settings_app.models import UserProfile, UserRole


class Command(BaseCommand):
    help = 'Create profiles for all users that don\'t have one'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(profile__isnull=True)
        count = 0
        
        # Get default role (Admin) if available
        default_role = UserRole.objects.filter(name='Admin').first()
        
        for user in users_without_profile:
            profile = UserProfile.objects.create(
                user=user,
                role=default_role if user.is_superuser else None
            )
            count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created profile for user: {user.username}'
                )
            )
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {count} user profile(s)'
                )
            )




