from django.core.management.base import BaseCommand
from inventory.models import EngineSupercession


class Command(BaseCommand):
    help = 'Remove all engine supercession relationships'

    def handle(self, *args, **options):
        count = EngineSupercession.objects.count()
        EngineSupercession.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully removed {count} supercession relationships')
        )
