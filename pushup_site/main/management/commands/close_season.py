from django.core.management.base import BaseCommand
from django.utils import timezone

from main.leaderboard_service import season_leaderboard_queryset
from main.models import PlayerBadge, Season, SeasonRanking
from main.profile_helpers import serialize_player_public, total_xp


class Command(BaseCommand):
    help = "Close expired seasons and snapshot top rankings"

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Season.objects.filter(is_active=True, ends_at__lt=now)
        for season in expired:
            players = season_leaderboard_queryset(season.scope, season.scope_key).order_by(
                "-level", "-exp", "id"
            )[:100]
            SeasonRanking.objects.filter(season=season).delete()
            for i, p in enumerate(players, start=1):
                SeasonRanking.objects.create(
                    season=season,
                    player=p,
                    rank=i,
                    total_xp=total_xp(p),
                    snapshot_json=serialize_player_public(p, rank=i),
                )
                if i <= 3:
                    p.season_title = f"Топ-{i} {season.name}"
                    p.save(update_fields=["season_title"])
                    PlayerBadge.objects.create(
                        player=p,
                        season=season,
                        label=f"Топ-{i} {season.name}",
                        icon="trophy",
                    )
            season.is_active = False
            season.save(update_fields=["is_active"])
            self.stdout.write(self.style.SUCCESS(f"Closed season {season.name}"))
