from django.core.management.base import BaseCommand

from main.models import WorkoutSession
from main.views.api_v1_helpers import MAX_WORKOUT_DURATION_SECONDS, clamp_workout_duration_seconds


class Command(BaseCommand):
    help = "Clamp unrealistic duration_seconds values in workout history."

    def handle(self, *args, **options):
        queryset = WorkoutSession.objects.filter(duration_seconds__gt=MAX_WORKOUT_DURATION_SECONDS)
        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No sessions with unrealistic duration found."))
            return

        for session in queryset.iterator():
            old = session.duration_seconds
            session.duration_seconds = clamp_workout_duration_seconds(old)
            session.save(update_fields=["duration_seconds"])
            self.stdout.write(f"Session {session.id} ({session.exercise_type}): {old}s -> {session.duration_seconds}s")

        self.stdout.write(self.style.SUCCESS(f"Fixed {total} session(s)."))
