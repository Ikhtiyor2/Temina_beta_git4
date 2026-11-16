from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import Challenge
from main.views.api_v1_challenges import _release_escrow


class Command(BaseCommand):
    help = "Expire active challenges past deadline and release XP escrow"

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Challenge.objects.filter(
            status=Challenge.STATUS_ACTIVE,
            deadline__lt=now,
        ).select_related("challenger", "opponent")
        count = 0
        for ch in expired:
            _release_escrow(ch)
            ch.status = Challenge.STATUS_EXPIRED
            ch.save(update_fields=["status"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Expired {count} challenges"))
