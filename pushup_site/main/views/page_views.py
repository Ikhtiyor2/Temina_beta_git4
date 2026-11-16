# main/views/page_views.py
import os
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Max
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from main.decorators import subscription_required
from main.turnstile import captcha_message, page_lang, registration_captcha, verify_turnstile


# ======================================================
# PWA (Service Worker at root for scope)
# ======================================================

def service_worker_js(request):
    """Serve sw.js at /sw.js so PWA scope is the whole site."""
    path = settings.BASE_DIR / "static" / "sw.js"
    if not path.exists():
        return HttpResponse("// PWA sw.js not found", content_type="application/javascript")
    with open(path, "r", encoding="utf-8") as f:
        return HttpResponse(f.read(), content_type="application/javascript")


# ======================================================
# PUBLIC PAGES
# ======================================================

def home_page(request):
    """Главная страница"""
    return render(request, "main/home.html")


def privacy_policy_page(request):
    """Публичная политика конфиденциальности (Google Play, сайт, приложение)."""
    return render(request, "main/privacy.html")


def login_page(request):
    """Страница входа"""
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        from main.models import Player
        player, _ = Player.objects.get_or_create(user=user)
        player.update_login_streak()
        player.save()
        messages.success(request, "✅ Успешный вход")
        return redirect("dashboard")

    if request.method == "POST" and not form.is_valid():
        messages.error(request, "❌ Неверный логин или пароль")

    return render(request, "main/login.html", {"form": form})


def register_page(request):
    """Регистрация"""
    if request.user.is_authenticated:
        return redirect("dashboard")

    from main.forms import RegistrationForm

    site_key, captcha_blocked = registration_captcha()
    lang = page_lang(request)

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        form.is_valid()
        if captcha_blocked:
            form.add_error(None, captcha_message(lang, "unavailable"))
        elif site_key and not verify_turnstile(request.POST.get("cf-turnstile-response")):
            form.add_error(None, captcha_message(lang, "failed"))
        elif form.is_valid():
            user = form.save()
            from main.models import Player
            from main.email_verification import send_verification_email

            player, _ = Player.objects.get_or_create(user=user)
            player.email_verified = False
            player.save(update_fields=["email_verified"])
            login(request, user)
            sent, _send_err = send_verification_email(user)
            if sent:
                messages.success(
                    request,
                    "Аккаунт создан. Мы отправили письмо для подтверждения email — "
                    "приложение можно использовать и без подтверждения.",
                )
            else:
                messages.info(
                    request,
                    "Аккаунт создан. Письмо подтверждения не удалось отправить сейчас — "
                    "позже можно запросить повторно в приложении.",
                )
            return redirect("welcome_page")
    else:
        form = RegistrationForm()

    return render(
        request,
        "main/registration.html",
        {
            "form": form,
            "turnstile_site_key": site_key,
            "turnstile_blocked": captcha_blocked,
        },
    )


@login_required
def welcome_page(request):
    """Приветственная карточка после регистрации — для скриншота и шеринга."""
    name = (request.user.first_name or request.user.username or "").strip()
    if not name:
        name = request.user.username or ""
    display_name = (name.capitalize() if name else "Качмен")[:50]
    return render(request, "main/welcome.html", {"display_name": display_name})


@require_http_methods(["POST"])
def logout_view(request):
    """Выход (только POST — защита от logout CSRF)."""
    logout(request)
    return redirect("home")


def _safe_internal_path(value):
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return None
    return value


def quick_login(request):
    """Быстрый вход (демо). Только при DEBUG=True."""
    from django.conf import settings
    if not settings.DEBUG:
        return redirect("login_page")
    nxt = _safe_internal_path(request.GET.get("next") or "")
    if request.user.is_authenticated:
        return redirect(nxt or "dashboard")

    user, created = User.objects.get_or_create(
        username="testuser",
        defaults={
            "email": "test@test.com",
            "is_active": True,
        },
    )

    if created:
        user.set_password("testpass123")
        user.save()

        from main.models import Player
        Player.objects.create(user=user)

    user = authenticate(request, username="testuser", password="testpass123")
    if user is not None:
        login(request, user)

        from main.models import Player
        player, _ = Player.objects.get_or_create(user=user)
        player.update_login_streak()
        player.save()

        messages.success(request, f"🚀 Быстрый вход как {user.username}")
        if nxt:
            return redirect(nxt)
        if request.GET.get("tma") == "1":
            return redirect("/dashboard/?tma=1")
        return redirect("dashboard")

    messages.error(request, "❌ Ошибка быстрого входа")
    return redirect("login_page")


@xframe_options_exempt
@ensure_csrf_cookie
def miniapp_page(request):
    """Отдельный Telegram Mini App. Сайт и Android остаются на своих страницах."""
    return render(request, "miniapp/index.html", {"debug": settings.DEBUG})


# ======================================================
# AUTHENTICATED PAGES
# ======================================================

@login_required
def dashboard_page(request):
    """
    Dashboard с реальной статистикой пользователя.
    Все цифры берём из WorkoutSession.
    """
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count, Max
    from main.models import Player, WorkoutSession

    player, _ = Player.objects.get_or_create(user=request.user)

    sessions = WorkoutSession.objects.filter(player=player).order_by("-date")

    # -----------------------------
    # Общая статистика
    # -----------------------------
    totals = sessions.aggregate(
        total_workouts=Count("id"),
        total_reps=Sum("reps_count"),
        total_time=Sum("duration_seconds"),
        total_calories=Sum("calories_burned"),
    )

    total_workouts = totals["total_workouts"] or 0
    total_reps = totals["total_reps"] or 0
    total_time = totals["total_time"] or 0
    total_calories = float(totals["total_calories"] or 0)

    # -----------------------------
    # Сумма повторений по упражнениям
    # -----------------------------
    def sum_reps(ex_type: str) -> int:
        return (
            sessions.filter(exercise_type=ex_type)
            .aggregate(total=Sum("reps_count"))["total"]
            or 0
        )

    pushups_total = sum_reps("PUSHUP")
    squats_total = sum_reps("SQUAT")
    crunches_total = sum_reps("CRUNCH")
    pullups_total = sum_reps("PULLUP")

    # -----------------------------
    # Рекорды (лучший сет)
    # -----------------------------
    def max_set(ex_type: str) -> int:
        return (
            sessions.filter(exercise_type=ex_type)
            .aggregate(mx=Max("reps_count"))["mx"]
            or 0
        )

    best_pushups = max_set("PUSHUP")
    best_squats = max_set("SQUAT")
    best_crunches = max_set("CRUNCH")
    best_pullups = max_set("PULLUP")

    # -----------------------------
    # Неделя / месяц
    # -----------------------------
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    week_sessions = sessions.filter(date__gte=week_ago)
    month_sessions = sessions.filter(date__gte=month_ago)

    week_stats = week_sessions.aggregate(
        workouts=Count("id"),
        reps=Sum("reps_count"),
        calories=Sum("calories_burned"),
        time=Sum("duration_seconds"),
    )

    month_stats = month_sessions.aggregate(
        workouts=Count("id"),
        reps=Sum("reps_count"),
        calories=Sum("calories_burned"),
        time=Sum("duration_seconds"),
    )

    for k in list(week_stats.keys()):
        week_stats[k] = week_stats[k] or 0
    for k in list(month_stats.keys()):
        month_stats[k] = month_stats[k] or 0

    # -----------------------------
    # История последних 10 тренировок
    # -----------------------------
    last_sessions = list(
        sessions[:10].values(
            "id",
            "exercise_type",
            "reps_count",
            "errors_count",
            "duration_seconds",
            "calories_burned",
            "date",
        )
    )

    # Переводы
    EXERCISE_RU = {
        "PUSHUP": "Отжимания",
        "SQUAT": "Приседания",
        "CRUNCH": "Скручивания",
        "PULLUP": "Подтягивания",
    }

    for s in last_sessions:
        s["exercise_name"] = EXERCISE_RU.get(s["exercise_type"], s["exercise_type"])
        s["duration_minutes"] = (s.get("duration_seconds") or 0) // 60

    # Серия входов (для дашборда)
    streak_days = getattr(player, "login_streak", 0) or 0
    try:
        streak_days = max(streak_days, getattr(player.stats, "current_streak", 0) or 0)
    except Exception:
        pass
    streak_percent = min(100, streak_days * 10)

    # XP и прогресс уровня для Lovable-style дашборда
    exp_to = getattr(player, "exp_to_level", 100) or 100
    exp_cur = getattr(player, "exp", 0) or 0
    level_progress_dash = min(100, int(exp_cur / exp_to * 100)) if exp_to else 0
    total_xp = int(exp_cur)

    context = {
        "player": player,
        "level_progress_dash": level_progress_dash,
        "total_xp": total_xp,

        # totals
        "total_workouts": total_workouts,
        "total_reps": total_reps,
        "total_time": total_time,
        "total_time_minutes": total_time // 60,
        "total_calories": round(total_calories, 1),

        # per exercise totals
        "pushups_total": pushups_total,
        "squats_total": squats_total,
        "crunches_total": crunches_total,
        "pullups_total": pullups_total,

        # records (aliases for template)
        "best_pushups": best_pushups,
        "best_squats": best_squats,
        "best_crunches": best_crunches,
        "best_pullups": best_pullups,
        "pushups_record": best_pushups,
        "squats_record": best_squats,
        "crunches_record": best_crunches,
        "pushups_calories": round(float(sessions.filter(exercise_type="PUSHUP").aggregate(c=Sum("calories_burned"))["c"] or 0), 0),
        "squats_calories": round(float(sessions.filter(exercise_type="SQUAT").aggregate(c=Sum("calories_burned"))["c"] or 0), 0),
        "crunches_calories": round(float(sessions.filter(exercise_type="CRUNCH").aggregate(c=Sum("calories_burned"))["c"] or 0), 0),

        # week/month
        "week_stats": {
            "workouts": week_stats["workouts"],
            "reps": week_stats["reps"],
            "calories": round(float(week_stats["calories"]), 1),
            "time": week_stats["time"],
        },
        "week_workouts": week_stats["workouts"],
        "week_reps": week_stats["reps"],
        "week_calories": round(float(week_stats["calories"]), 1),
        "month_stats": {
            "workouts": month_stats["workouts"],
            "reps": month_stats["reps"],
            "calories": round(float(month_stats["calories"]), 1),
            "time": month_stats["time"],
        },

        # streak
        "streak_days": streak_days,
        "streak_percent": streak_percent,

        # history
        "last_sessions": last_sessions,

        # AI Coach tip of the day (rotates by day)
        "coach_tip_ru": _coach_tips_ru[(now.day + 31 * (now.month - 1)) % len(_coach_tips_ru)],
        "coach_tip_en": _coach_tips_en[(now.day + 31 * (now.month - 1)) % len(_coach_tips_en)],
    }

    return render(request, "main/dashboard.html", context)


# Советы ИИ‑тренера для блока на дашборде (по одному в день)
_coach_tips_ru = [
    "Держи локти ближе к корпусу при отжиманиях — так лучше работают грудь и трицепс.",
    "Приседай минимум до параллели бедра с полом, чтобы повтор засчитался.",
    "В планке держи плечи над запястьями и тело одной линией.",
    "Выдыхай на усилии, вдыхай на возврате — так стабильнее и сильнее.",
    "Качество важнее количества: один правильный повтор лучше пяти с плохой техникой.",
    "Разомнись 5–10 медленными повторениями перед быстрым темпом.",
]
_coach_tips_en = [
    "Keep elbows close to your body during push-ups for better chest and triceps engagement.",
    "Squat until your thighs are at least parallel to the floor for the rep to count.",
    "In plank, keep shoulders over wrists and body in one straight line.",
    "Breathe out on the effort, in on the return — it helps stability and power.",
    "Quality over quantity: one correct rep is better than five with poor form.",
    "Warm up with 5–10 reps at a slow pace before going full speed.",
]



@login_required
def profile_page(request):
    """Профиль игрока"""
    from main.models import Player, WorkoutSet, WorkoutSession, PlayerStats, Quest
    from django.db.models import Sum, Count, Max
    from django.db.models.functions import TruncDate
    from django.db.utils import OperationalError

    player, _ = Player.objects.get_or_create(user=request.user)

    # Прогресс уровня (процент)
    exp_to = getattr(player, "exp_to_level", 100) or 100
    exp_cur = getattr(player, "exp", 0) or 0
    level_progress = min(100, int(exp_cur / exp_to * 100)) if exp_to else 0

    # Последние подходы (WorkoutSet привязан к user)
    latest_activities = list(
        WorkoutSet.objects.filter(user=request.user).order_by("-date_completed")[:6]
    )

    # Агрегаты по сессиям игрока
    sessions = WorkoutSession.objects.filter(player=player)
    agg = sessions.aggregate(
        total_reps=Sum("reps_count"),
        total_sets=Count("id"),
        max_reps=Max("reps_count"),
    )
    days_active = (
        sessions.annotate(day=TruncDate("date")).values("day").distinct().count()
    )
    total_reps = agg["total_reps"] or 0
    total_sets = agg["total_sets"] or 0
    max_reps_overall = agg["max_reps"] or 0

    # Доп. из PlayerStats если есть (игнорируем ошибки БД, например нет колонки planks_total до миграции)
    try:
        stats = player.stats
        total_reps = stats.total_reps or total_reps
        total_sets = stats.total_workouts or total_sets
        max_reps_overall = max(
            max_reps_overall,
            getattr(stats, "max_pushups_set", 0) or 0,
            getattr(stats, "max_squats_set", 0) or 0,
        )
        current_streak = getattr(stats, "current_streak", 0) or 0
    except (PlayerStats.DoesNotExist, OperationalError):
        current_streak = getattr(player, "login_streak", 0) or 0

    completed_quests = Quest.objects.filter(player=player, completed=True).count()

    return render(
        request,
        "main/profile.html",
        {
            "player": player,
            "level_progress": level_progress,
            "latest_activities": latest_activities,
            "total_reps": total_reps,
            "total_sets": total_sets,
            "max_reps_overall": max_reps_overall,
            "days_active": days_active,
            "completed_quests": completed_quests,
            "current_streak": current_streak,
            "skill_points": getattr(player, "skill_points", 0) or 0,
        },
    )


@login_required
def profile_view_page(request, player_id):
    """Просмотр профиля другого игрока (только чтение)."""
    from main.models import Player, WorkoutSet, WorkoutSession, PlayerStats, Quest
    from django.db.models import Sum, Count, Max
    from django.db.models.functions import TruncDate
    from django.db.utils import OperationalError
    from django.shortcuts import get_object_or_404

    player = get_object_or_404(Player.objects.select_related("user"), id=player_id)
    profile_user = player.user

    exp_to = getattr(player, "exp_to_level", 100) or 100
    exp_cur = getattr(player, "exp", 0) or 0
    level_progress = min(100, int(exp_cur / exp_to * 100)) if exp_to else 0

    latest_activities = list(
        WorkoutSet.objects.filter(user=profile_user).order_by("-date_completed")[:6]
    )

    sessions = WorkoutSession.objects.filter(player=player)
    agg = sessions.aggregate(
        total_reps=Sum("reps_count"),
        total_sets=Count("id"),
        max_reps=Max("reps_count"),
    )
    days_active = (
        sessions.annotate(day=TruncDate("date")).values("day").distinct().count()
    )
    total_reps = agg["total_reps"] or 0
    total_sets = agg["total_sets"] or 0
    max_reps_overall = agg["max_reps"] or 0

    try:
        stats = player.stats
        total_reps = stats.total_reps or total_reps
        total_sets = stats.total_workouts or total_sets
        max_reps_overall = max(
            max_reps_overall,
            getattr(stats, "max_pushups_set", 0) or 0,
            getattr(stats, "max_squats_set", 0) or 0,
        )
        current_streak = getattr(stats, "current_streak", 0) or 0
    except (PlayerStats.DoesNotExist, OperationalError):
        current_streak = getattr(player, "login_streak", 0) or 0

    completed_quests = Quest.objects.filter(player=player, completed=True).count()

    return render(
        request,
        "main/profile.html",
        {
            "player": player,
            "profile_user": profile_user,
            "is_view_only": True,
            "level_progress": level_progress,
            "latest_activities": latest_activities,
            "total_reps": total_reps,
            "total_sets": total_sets,
            "max_reps_overall": max_reps_overall,
            "days_active": days_active,
            "completed_quests": completed_quests,
            "current_streak": current_streak,
            "skill_points": getattr(player, "skill_points", 0) or 0,
        },
    )


@login_required
def workouts_page(request):
    """Страница тренировок"""
    return render(request, "main/workouts.html")


@login_required
def workout_builder_page(request):
    """Страница создания персональной тренировки через чат с ИИ."""
    from main.workout_builder import INITIAL_STATE
    if "workout_builder_state" not in request.session:
        request.session["workout_builder_state"] = INITIAL_STATE
    return render(request, "main/workout_builder.html")


@login_required
def quests_page(request):
    """Страница квестов"""
    from main.models import Quest, Player

    player, _ = Player.objects.get_or_create(user=request.user)
    quests = Quest.objects.filter(player=player, completed=False)

    return render(
        request,
        "main/quests.html",
        {
            "quests": quests,
            "player": player,
        },
    )


@login_required
def stats_page(request):
    """Страница статистики"""
    from main.models import Player, WorkoutSession

    player, _ = Player.objects.get_or_create(user=request.user)

    sessions = WorkoutSession.objects.filter(player=player)
    total_sessions = sessions.count()
    total_reps = sessions.aggregate(total=Sum("reps_count"))["total"] or 0

    return render(
        request,
        "main/stats.html",
        {
            "player": player,
            "total_sessions": total_sessions,
            "total_reps": total_reps,
        },
    )


def _total_xp(player):
    """Приблизительный общий XP: сумма за прошлые уровни + текущий exp."""
    level = getattr(player, "level", 1) or 1
    exp = getattr(player, "exp", 0) or 0
    # exp_to_level = level * 100, уровень k даёт 100*k XP до следующего
    return int(100 * level * (level - 1) / 2 + exp)


def _level_class(level):
    """Текстовый класс по уровню."""
    if level >= 20:
        return "МАСТЕР"
    if level >= 15:
        return "ЭКСПЕРТ"
    if level >= 10:
        return "БОЕЦ"
    if level >= 5:
        return "АТЛЕТ"
    return "НОВИЧОК"


PAGE_SIZE_LEADERBOARD = 10


@login_required
def leaderboard_page(request):
    """Лидерборд: топ игроков по уровню и опыту, пагинация по 10, поиск по имени."""
    from main.models import Player
    from main.leaderboard_service import public_players_queryset
    from django.core.paginator import Paginator

    q = request.GET.get("q", "").strip()
    base_qs = public_players_queryset().order_by("-level", "-exp")
    if q:
        base_qs = base_qs.filter(user__username__icontains=q)
    paginator = Paginator(base_qs, PAGE_SIZE_LEADERBOARD)
    page_num = request.GET.get("page", "1")
    try:
        page_num = max(1, int(page_num))
    except ValueError:
        page_num = 1
    page = paginator.get_page(page_num)
    current_player, _ = Player.objects.get_or_create(user=request.user)

    leaders = []
    for rank_offset, p in enumerate(page.object_list, start=(page.number - 1) * PAGE_SIZE_LEADERBOARD):
        total = _total_xp(p)
        leaders.append({
            "player_id": p.id,
            "name": p.user.username if p.user else "Игрок",
            "score": total,
            "level": getattr(p, "level", 1) or 1,
            "class": _level_class(getattr(p, "level", 1) or 1),
            "is_current": p.id == current_player.id,
            "rank": rank_offset + 1,
        })

    return render(
        request,
        "main/leaderboard.html",
        {
            "leaders": leaders,
            "player": current_player,
            "page": page,
            "search_query": q,
        },
    )


@login_required
def settings_page(request):
    """Настройки"""
    return render(request, "main/settings.html")


@login_required
def skills_page(request):
    """Навыки"""
    from main.models import Player
    player, _ = Player.objects.get_or_create(user=request.user)

    return render(request, "main/skills.html", {"player": player})


@login_required
def training_page(request, exercise):
    """Страница тренировки по упражнению"""
    from main.models import Player, ActiveWorkout

    EXERCISE_MAP = {
        "pushups": "PUSHUP",
        "squats": "SQUAT",
        "crunches": "CRUNCH",
        "pullups": "PULLUP",
        "planks": "PLANK",
    }

    exercise = exercise.lower()
    exercise_type = EXERCISE_MAP.get(exercise)

    if not exercise_type:
        messages.error(request, f"❌ Упражнение '{exercise}' не найдено")
        return redirect("dashboard")

    player, _ = Player.objects.get_or_create(user=request.user)

    workout, _ = ActiveWorkout.get_or_create_active(
        player=player,
        exercise_type=exercise_type,
    )

    EXERCISE_NAMES = {
        "PUSHUP": "Отжимания",
        "SQUAT": "Приседания",
        "CRUNCH": "Скручивания",
        "PULLUP": "Подтягивания",
        "PLANK": "Планка",
    }

    return render(
        request,
        "main/training.html",
        {
            "exercise": exercise_type,
            "exercise_name": EXERCISE_NAMES.get(exercise_type, exercise_type),
            "workout_id": workout.id,
            "player": player,
        },
    )


@login_required
def fitness_profile_page(request):
    """Страница настройки профиля для ИИ-тренера (возраст, цели, здоровье, оборудование и т.д.)."""
    import json
    from main.models import FitnessProfile
    profile, _ = FitnessProfile.objects.get_or_create(user=request.user)
    profile_data = json.dumps({
        "age": profile.age,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "target_weight_kg": profile.target_weight_kg,
        "goals": profile.goals or [],
        "muscle_focus": profile.muscle_focus or [],
        "health_limits": profile.health_limits or [],
        "equipment": profile.equipment or [],
        "fitness_level": profile.fitness_level or "",
        "activity_level": profile.activity_level or "",
        "workouts_per_week": profile.workouts_per_week or 3,
        "motivation": profile.motivation or [],
        "notes": profile.notes or "",
    })
    return render(request, "main/fitness_profile.html", {"profile": profile, "profile_data": profile_data})


@login_required
@require_http_methods(["POST"])
def api_save_fitness_profile(request):
    """Сохранение профиля фитнеса (JSON)."""
    from main.models import FitnessProfile
    import json
    try:
        data = json.loads(request.body) if request.body else {}
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    profile, _ = FitnessProfile.objects.get_or_create(user=request.user)
    if "age" in data and data["age"] is not None:
        profile.age = data.get("age")
    if "height_cm" in data and data["height_cm"] is not None:
        profile.height_cm = data.get("height_cm")
    if "weight_kg" in data and data["weight_kg"] is not None:
        profile.weight_kg = data.get("weight_kg")
    if "target_weight_kg" in data and data["target_weight_kg"] is not None:
        profile.target_weight_kg = data.get("target_weight_kg")
    if "goals" in data:
        profile.goals = data["goals"] if isinstance(data["goals"], list) else []
    if "muscle_focus" in data:
        profile.muscle_focus = data["muscle_focus"] if isinstance(data["muscle_focus"], list) else []
    if "health_limits" in data:
        profile.health_limits = data["health_limits"] if isinstance(data["health_limits"], list) else []
    if "equipment" in data:
        profile.equipment = data["equipment"] if isinstance(data["equipment"], list) else []
    if "fitness_level" in data and data["fitness_level"]:
        profile.fitness_level = data["fitness_level"]
    if "activity_level" in data and data["activity_level"]:
        profile.activity_level = data["activity_level"]
    if "workouts_per_week" in data and data["workouts_per_week"] is not None:
        w = int(data["workouts_per_week"])
        profile.workouts_per_week = max(1, min(7, w))
    if "motivation" in data:
        profile.motivation = data["motivation"] if isinstance(data["motivation"], list) else []
    if "notes" in data:
        profile.notes = (data["notes"] or "").strip()
    profile.save()
    return JsonResponse({"ok": True, "is_complete": profile.is_complete()})


@subscription_required
@login_required
@require_http_methods(["POST"])
def api_generate_workout_plan(request):
    """Генерация плана тренировок по сохранённому профилю (ИИ или правило-бэкофф)."""
    from main.models import FitnessProfile
    from main.ai_workout_plan import generate_workout_plan
    profile, _ = FitnessProfile.objects.get_or_create(user=request.user)
    if not profile.is_complete():
        return JsonResponse({
            "ok": False,
            "need_profile": True,
            "message": "Fill in at least age and goals / fitness level in your fitness profile.",
        }, status=400)
    plan, is_ai = generate_workout_plan(profile)
    return JsonResponse({"ok": True, "plan": plan, "generated_by": "ai" if is_ai else "template"})


@login_required
@require_http_methods(["POST"])
def api_workout_builder_chat(request):
    """API чата с ИИ-тренером: принимает ответ пользователя, возвращает сообщение и опции или план."""
    from main.workout_builder import get_ai_reply, INITIAL_STATE, get_next_question, build_plan

    state = request.session.get("workout_builder_state", INITIAL_STATE)
    option_value = None
    try:
        import json
        body = json.loads(request.body) if request.body else {}
        option_value = body.get("option_value")
        if option_value is None:
            option_value = body.get("selected")
    except Exception:
        pass

    # Запрос без ответа — возвращаем текущий вопрос или сохранённый план
    if option_value is None or option_value == "":
        if state.get("step") == "done":
            plan = build_plan(state)
            return JsonResponse({
                "message": "Вот твоя сохранённая тренировка. Можешь начать с любого упражнения.",
                "plan": plan,
                "options": [],
            })
        next_q = get_next_question(state)
        return JsonResponse({
            "message": next_q["message"],
            "plan": None,
            "options": next_q.get("options", []),
        })

    state, reply = get_ai_reply(state, option_value=option_value)
    request.session["workout_builder_state"] = state
    return JsonResponse({
        "message": reply["message"],
        "plan": reply.get("plan"),
        "options": reply.get("options", []),
    })


# ======================================================
# LANGUAGE SWITCH (EN/RU)
# ======================================================

def set_language_view(request):
    """Устанавливает cookie temina_lang (ru/en/uz) и редиректит обратно."""
    from django.http import HttpResponseRedirect
    from main.url_safety import safe_relative_path
    lang = request.GET.get("lang", "ru")
    if lang not in ("ru", "en", "uz"):
        lang = "ru"
    next_url = safe_relative_path(request.GET.get("next", "").strip())
    response = HttpResponseRedirect(next_url)
    response.set_cookie("temina_lang", lang, max_age=365 * 24 * 60 * 60, samesite="Lax")
    return response


# ======================================================
# ERROR PAGES
# ======================================================

def handler404(request, exception):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)


def handler403(request, exception):
    return render(request, "errors/403.html", status=403)


def handler400(request, exception):
    return render(request, "errors/400.html", status=400)
