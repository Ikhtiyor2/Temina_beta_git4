"""Scoped leaderboard queries."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from main.models import Friendship, Player

# Public / competitive boards: only real athletes (not staff test accounts).
PUBLIC_PLAYER_FILTER = {
    "user__is_active": True,
    "user__is_staff": False,
    "user__is_superuser": False,
}


def public_players_queryset() -> QuerySet[Player]:
    return Player.objects.select_related(
        "user", "institution", "school_institution"
    ).filter(**PUBLIC_PLAYER_FILTER)


def leaderboard_queryset(scope: str, me: Player) -> QuerySet[Player]:
    qs = public_players_queryset()
    scope = (scope or "global").lower()
    if scope == "global":
        return qs
    if scope == "friends":
        friend_ids = set()
        for fr in Friendship.objects.filter(
            Q(from_player=me, status=Friendship.STATUS_ACCEPTED)
            | Q(to_player=me, status=Friendship.STATUS_ACCEPTED)
        ):
            if fr.from_player_id == me.id:
                friend_ids.add(fr.to_player_id)
            else:
                friend_ids.add(fr.from_player_id)
        friend_ids.add(me.id)
        return qs.filter(id__in=friend_ids)
    if scope == "city" and me.city:
        return qs.filter(city__iexact=me.city.strip())
    if scope == "region" and me.region:
        return qs.filter(region__iexact=me.region.strip())
    if scope == "university":
        if me.institution_id:
            return qs.filter(institution_id=me.institution_id)
        if me.institution_custom:
            return qs.filter(institution_custom__iexact=me.institution_custom.strip())
        return qs.none()
    if scope == "school":
        if me.school_institution_id:
            return qs.filter(school_institution_id=me.school_institution_id)
        return qs.none()
    return qs


def season_leaderboard_queryset(scope: str, scope_key: str = "") -> QuerySet[Player]:
    """Leaderboard pool for a season snapshot (uses scope_key, not viewer profile)."""
    qs = public_players_queryset()
    scope = (scope or "global").lower()
    key = (scope_key or "").strip()
    if scope == "global" or not key:
        return qs
    if scope == "city":
        return qs.filter(city__iexact=key)
    if scope == "region":
        return qs.filter(region__iexact=key)
    if scope == "university":
        if key.isdigit():
            return qs.filter(institution_id=int(key))
        return qs.filter(institution_custom__iexact=key)
    if scope == "school" and key.isdigit():
        return qs.filter(school_institution_id=int(key))
    return qs.none()
