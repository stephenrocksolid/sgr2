import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgr_manager.settings')
django.setup()

from django.core.management import call_command

print("Running migrations...")
call_command('migrate', 'settings_app', verbosity=2)
print("Done!")



