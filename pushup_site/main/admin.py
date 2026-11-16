from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    Challenge,
    IntegrityFlag,
    Institution,
    Player,
    Quest,
    Season,
    SeasonPrizeTier,
    SeasonRanking,
    Subscription,
    SupportMessage,
    SupportThread,
)


class PlayerInline(admin.StackedInline):
    model = Player
    can_delete = False
    extra = 0
    show_change_link = True
    fk_name = "user"
    fields = [
        "display_name",
        "avatar_url",
        "email_verified",
        "city",
        "region",
        "faculty",
        "course",
        "institution",
        "school_institution",
        "institution_custom",
        "invite_code",
        "level",
        "exp",
        "currency",
        "login_streak",
    ]
    readonly_fields = ["invite_code", "level", "exp", "currency", "login_streak"]
    raw_id_fields = ["institution", "school_institution"]


class UserAdmin(DjangoUserAdmin):
    list_display = [
        "id",
        "username",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "player_link",
        "last_login",
        "date_joined",
    ]
    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
        "groups",
    ]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    list_select_related = True
    inlines = [PlayerInline]
    actions = [
        "activate_users",
        "deactivate_users",
        "grant_staff",
        "revoke_staff",
    ]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": (
                    "Staff/superuser accounts are hidden from public leaderboards "
                    "and player search. Use a separate athlete account for testing ranks."
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    @admin.display(description="Player")
    def player_link(self, obj):
        try:
            player = obj.player
        except Player.DoesNotExist:
            return "—"
        url = reverse("admin:main_player_change", args=[player.pk])
        return format_html('<a href="{}">#{} · L{}</a>', url, player.pk, player.level)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("player")

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} user(s).")

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        qs = queryset.exclude(pk=request.user.pk)
        updated = qs.update(is_active=False)
        skipped = queryset.filter(pk=request.user.pk).count()
        msg = f"Deactivated {updated} user(s)."
        if skipped:
            msg += " (skipped yourself)"
        self.message_user(request, msg)

    @admin.action(description="Grant staff (hidden from leaderboards)")
    def grant_staff(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can grant staff.", level=messages.ERROR)
            return
        updated = queryset.update(is_staff=True)
        self.message_user(
            request,
            f"Granted staff to {updated} user(s). They will leave public leaderboards.",
        )

    @admin.action(description="Revoke staff (can appear on leaderboards again)")
    def revoke_staff(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can revoke staff.", level=messages.ERROR)
            return
        qs = queryset.filter(is_superuser=False).exclude(pk=request.user.pk)
        updated = qs.update(is_staff=False)
        self.message_user(request, f"Revoked staff from {updated} user(s).")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "username",
        "display_name",
        "level",
        "city",
        "region",
        "institution",
        "email_verified",
        "user_is_active",
        "user_is_staff",
        "login_streak",
        "created_at",
    ]
    list_filter = [
        "email_verified",
        "user__is_active",
        "user__is_staff",
        "user__is_superuser",
        "region",
        "city",
        "level",
        "created_at",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "display_name",
        "invite_code",
        "city",
        "faculty",
    ]
    raw_id_fields = ["user", "institution", "school_institution"]
    readonly_fields = [
        "created_at",
        "last_login_date",
        "invite_code",
        "level",
        "exp",
        "exp_to_level",
        "skill_points",
        "strength",
        "stamina",
        "agility",
        "technique",
        "currency",
        "fatigue",
        "login_streak",
        "xp_escrow",
        "season_title",
        "user_account_link",
    ]
    actions = ["mark_email_verified", "mark_email_unverified"]
    fieldsets = [
        (
            "Account",
            {
                "fields": [
                    "user",
                    "user_account_link",
                    "display_name",
                    "avatar_url",
                    "email_verified",
                    "invite_code",
                    "created_at",
                    "last_login_date",
                    "login_streak",
                ]
            },
        ),
        (
            "Location / school",
            {
                "fields": [
                    "city",
                    "region",
                    "faculty",
                    "course",
                    "institution",
                    "school_institution",
                    "institution_custom",
                ]
            },
        ),
        (
            "Progress (readonly)",
            {
                "fields": [
                    "level",
                    "exp",
                    "exp_to_level",
                    "skill_points",
                    "strength",
                    "stamina",
                    "agility",
                    "technique",
                    "currency",
                    "fatigue",
                    "xp_escrow",
                    "season_title",
                ]
            },
        ),
    ]

    @admin.display(description="Username", ordering="user__username")
    def username(self, obj):
        return obj.user.username if obj.user_id else "—"

    @admin.display(description="Active", boolean=True, ordering="user__is_active")
    def user_is_active(self, obj):
        return bool(obj.user.is_active) if obj.user_id else False

    @admin.display(description="Staff", boolean=True, ordering="user__is_staff")
    def user_is_staff(self, obj):
        return bool(obj.user.is_staff or obj.user.is_superuser) if obj.user_id else False

    @admin.display(description="Django user")
    def user_account_link(self, obj):
        if not obj.user_id:
            return "—"
        url = reverse("admin:auth_user_change", args=[obj.user_id])
        flags = []
        if obj.user.is_staff:
            flags.append("staff")
        if obj.user.is_superuser:
            flags.append("superuser")
        if not obj.user.is_active:
            flags.append("inactive")
        suffix = f" ({', '.join(flags)})" if flags else ""
        return format_html('<a href="{}">{}{}</a>', url, obj.user.username, suffix)

    @admin.action(description="Mark email verified")
    def mark_email_verified(self, request, queryset):
        updated = queryset.update(email_verified=True)
        self.message_user(request, f"Marked {updated} player(s) email verified.")

    @admin.action(description="Mark email unverified")
    def mark_email_unverified(self, request, queryset):
        updated = queryset.update(email_verified=False)
        self.message_user(request, f"Marked {updated} player(s) email unverified.")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user", "institution", "school_institution"
        )


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "type",
        "city",
        "region",
        "is_verified",
        "submitted_by",
        "created_at",
    ]
    list_filter = ["type", "is_verified", "region", "city", "country"]
    search_fields = ["name", "name_en", "name_uz", "city", "region"]
    raw_id_fields = ["submitted_by"]
    readonly_fields = ["created_at"]
    list_editable = ["is_verified"]
    actions = ["mark_verified", "mark_unverified"]

    @admin.action(description="Mark selected as verified")
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"Verified {updated} institution(s).")

    @admin.action(description="Mark selected as unverified")
    def mark_unverified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"Unverified {updated} institution(s).")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("submitted_by")


@admin.register(IntegrityFlag)
class IntegrityFlagAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "player",
        "session_id",
        "raw_reps",
        "sanitized_reps",
        "flags_preview",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = [
        "player__user__username",
        "player__user__email",
        "player__display_name",
        "session_id",
    ]
    raw_id_fields = ["player"]
    readonly_fields = [
        "player",
        "session_id",
        "flags",
        "sanitized_reps",
        "raw_reps",
        "payload",
        "created_at",
    ]
    date_hierarchy = "created_at"

    @admin.display(description="Flags")
    def flags_preview(self, obj):
        flags = obj.flags or []
        if isinstance(flags, list):
            text = ", ".join(str(f) for f in flags[:5])
            if len(flags) > 5:
                text += "…"
            return text or "—"
        return str(flags)[:80]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("player__user")


class SeasonPrizeTierInline(admin.TabularInline):
    model = SeasonPrizeTier
    extra = 0
    fields = [
        "rank_from",
        "rank_to",
        "prize_type",
        "description",
        "fulfillment_status",
    ]


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "scope",
        "scope_key",
        "starts_at",
        "ends_at",
        "is_active",
        "created_at",
    ]
    list_filter = ["scope", "is_active", "starts_at"]
    search_fields = ["name", "scope_key"]
    readonly_fields = ["created_at"]
    inlines = [SeasonPrizeTierInline]
    actions = ["activate", "deactivate"]

    @admin.action(description="Activate selected seasons")
    def activate(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} season(s).")

    @admin.action(description="Deactivate selected seasons")
    def deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} season(s).")


@admin.register(SeasonPrizeTier)
class SeasonPrizeTierAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "season",
        "rank_from",
        "rank_to",
        "prize_type",
        "fulfillment_status",
    ]
    list_filter = ["prize_type", "fulfillment_status"]
    search_fields = ["season__name", "description"]
    raw_id_fields = ["season"]
    list_editable = ["fulfillment_status"]


@admin.register(SeasonRanking)
class SeasonRankingAdmin(admin.ModelAdmin):
    list_display = ["id", "season", "rank", "player", "total_xp", "created_at"]
    list_filter = ["season", "created_at"]
    search_fields = ["player__user__username", "season__name"]
    raw_id_fields = ["season", "player"]
    readonly_fields = ["created_at", "snapshot_json"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("season", "player__user")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "challenger",
        "opponent",
        "exercise_type",
        "goal_metric",
        "goal_value",
        "wager_xp",
        "status",
        "deadline",
        "winner",
        "created_at",
    ]
    list_filter = ["status", "exercise_type", "goal_metric", "deadline"]
    search_fields = [
        "challenger__user__username",
        "opponent__user__username",
        "challenger__display_name",
        "opponent__display_name",
    ]
    raw_id_fields = ["challenger", "opponent", "winner"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "challenger_result",
        "opponent_result",
        "session_challenger_id",
        "session_opponent_id",
    ]
    date_hierarchy = "deadline"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("challenger__user", "opponent__user", "winner__user")
        )


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ["title", "player", "quest_type", "progress", "goal", "completed", "created_at"]
    list_filter = ["quest_type", "completed", "created_at"]
    search_fields = ["title", "player__user__username"]
    raw_id_fields = ["player"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "status",
        "entitlement_id",
        "product_id",
        "store",
        "current_period_end",
        "auto_renewing",
        "updated_at",
    ]
    list_filter = ["status", "store", "platform", "auto_renewing"]
    search_fields = ["user__username", "app_user_id", "product_id"]
    readonly_fields = ["created_at", "updated_at", "last_event_id"]
    raw_id_fields = ["user"]


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1
    fields = ["sender_type", "sender_user", "body", "created_at"]
    readonly_fields = ["created_at"]
    ordering = ["created_at"]


@admin.register(SupportThread)
class SupportThreadAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "player",
        "subject",
        "category",
        "status",
        "unread_by_user",
        "last_message_at",
        "updated_at",
    ]
    list_filter = ["status", "category", "created_at"]
    search_fields = ["subject", "player__user__username", "player__user__email"]
    readonly_fields = ["created_at", "updated_at", "last_message_at", "unread_by_user"]
    raw_id_fields = ["player"]
    inlines = [SupportMessageInline]
    actions = ["mark_waiting_user", "mark_closed"]

    @admin.action(description="Mark as waiting for user (staff replied)")
    def mark_waiting_user(self, request, queryset):
        queryset.update(status=SupportThread.STATUS_WAITING_USER, updated_at=timezone.now())

    @admin.action(description="Close selected threads")
    def mark_closed(self, request, queryset):
        queryset.update(status=SupportThread.STATUS_CLOSED, updated_at=timezone.now())

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        thread = form.instance
        now = timezone.now()
        staff_replied = False
        for obj in instances:
            if isinstance(obj, SupportMessage) and obj.pk is None:
                if not obj.sender_type or obj.sender_type == SupportMessage.SENDER_USER:
                    obj.sender_type = SupportMessage.SENDER_STAFF
                if obj.sender_user_id is None and obj.sender_type == SupportMessage.SENDER_STAFF:
                    obj.sender_user = request.user
                if obj.sender_type == SupportMessage.SENDER_STAFF:
                    staff_replied = True
            obj.save()
        formset.save_m2m()
        if staff_replied and thread.status != SupportThread.STATUS_CLOSED:
            thread.status = SupportThread.STATUS_WAITING_USER
            thread.unread_by_user = (thread.unread_by_user or 0) + 1
            thread.last_message_at = now
            thread.save(update_fields=["status", "unread_by_user", "last_message_at", "updated_at"])


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "thread", "sender_type", "body_preview", "created_at"]
    list_filter = ["sender_type", "created_at"]
    search_fields = ["body", "thread__subject", "thread__player__user__username"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["thread", "sender_user"]

    @admin.display(description="Body")
    def body_preview(self, obj):
        return (obj.body or "")[:80]
