# main/urls.py
from django.urls import path
from django.shortcuts import redirect

# ========================
# PAGE VIEWS (HTML PAGES)
# ========================
from .views.page_views import (
    service_worker_js,
    set_language_view,
    home_page,
    privacy_policy_page,
    login_page,
    skills_page,
    register_page,
    welcome_page,
    logout_view,
    quick_login,
    miniapp_page,

    dashboard_page,
    profile_page,
    profile_view_page,
    fitness_profile_page,
    workouts_page,
    workout_builder_page,
    quests_page,
    stats_page,
    leaderboard_page,
    settings_page,
    training_page,
    api_workout_builder_chat,
    api_save_fitness_profile,
    api_generate_workout_plan,

    handler404,
    handler500,
    handler403,
    handler400,
)

# ========================
# AI VIEWS
# ========================
from .views.assessment_views import api_v1_post_user_assessment, api_v1_post_user_assessment_dev
from .views.ai_views import (
    process_ai_frame,
    process_landmarks,
    get_ai_state,
    reset_ai_state,
    get_csrf_token,
)

from .views.auth_api_views import (
    api_auth_me,
    api_auth_login,
    api_auth_register,
    api_auth_logout,
    api_auth_telegram,
    api_auth_resend_verification,
    api_auth_verify_email,
    verify_email_page,
)

from .views.api_v1_dashboard import api_v1_dashboard
from .views.api_v1_form_rules import api_v1_form_rules
from .views.api_v1_runs import (
    api_v1_run_detail,
    api_v1_run_finish,
    api_v1_run_history,
    api_v1_run_pause,
    api_v1_run_resume,
    api_v1_run_start,
    api_v1_run_track,
)
from .views.api_v1_stats import (
    api_v1_stats_activity,
    api_v1_stats_calories,
    api_v1_stats_calories_breakdown,
    api_v1_stats_steps,
)
from .views.api_v1_workouts import (
    api_v1_workout_detail,
    api_v1_workout_session_finish,
    api_v1_workout_start,
    api_v1_workouts,
)
from .views.api_v1_quests import (
    api_v1_quest_claim,
    api_v1_quest_detail,
    api_v1_quest_start,
    api_v1_quests,
)
from .views.api_v1_plan import api_v1_plan_current, api_v1_plan_generate
from .views.api_v1_weekly_plan import (
    api_v1_week_plan_current,
    api_v1_week_plan_log_session,
    api_v1_week_plan_refresh,
    api_v1_week_plan_rollover,
)
from .views.api_v1_leaderboard import api_v1_leaderboard, api_v1_player_public
from .views.api_v1_billing import (
    api_v1_billing_rcat,
    api_v1_subscription,
)
from .views.api_v1_profile import api_v1_users_me, api_v1_users_me_upgrade_skill
from .views.api_v1_institutions import api_v1_institutions_search, api_v1_institutions_create
from .views.api_v1_geo import api_v1_geo_regions, api_v1_geo_cities
from .views.api_v1_friends import (
    api_v1_friends_list,
    api_v1_friends_request,
    api_v1_friends_accept,
    api_v1_friends_delete,
    api_v1_friends_reject,
    api_v1_invites_redeem,
)
from .views.api_v1_support import (
    api_v1_support_threads_list,
    api_v1_support_threads_create,
    api_v1_support_thread_detail,
    api_v1_support_thread_message,
    api_v1_support_thread_close,
)
from .views.api_v1_challenges import (
    api_v1_challenges_list,
    api_v1_challenges_create,
    api_v1_challenges_accept,
    api_v1_challenges_decline,
    api_v1_challenges_cancel,
    api_v1_challenges_submit,
)
from .views.api_v1_seasons import api_v1_seasons_current, api_v1_season_rankings
from .views.api_v1_players import api_v1_players_search, api_v1_friends_mutual

# ========================
# WORKOUT VIEWS
# ========================
from .views.workout_views import (
    start_workout,
    complete_workout,
    save_workout_set,
    get_current_workout,
    reset_workout,
)

# ========================
# PLAYER VIEWS
# ========================
from .views.player_views import (
    get_player_profile,
    upgrade_skill,
    add_currency,
    update_login_streak,
)

# ========================
# QUEST VIEWS
# ========================
from .views.quest_views import (
    get_quests,
    quests_data,      # <-- ВАЖНО: добавили
    start_quest,
    cancel_quest,
    complete_quest,
)

# ========================
# STATS VIEWS
# ========================
from .views.stats_views import (
    get_basic_stats,
    get_workout_history,
    get_daily_activity,
    get_exercise_breakdown,
)

# ========================
# HUD VIEWS
# ========================
from .views.hud_views import (
    get_hud_state,
    get_real_time_hud_data,
    get_unified_hud_data,
    get_hud_data,
    api_stats_combined,   # <-- ВАЖНО: берём напрямую
)

# ========================
# VIDEO VIEWS (LEGACY)
# ========================
from .views.video_views import (
    video_feed_pushups,
    video_feed_squats,
    video_feed_pullups,
    video_feed_crunches,
    video_feed_planks,
    video_feed,
    video_feed1,
    video_feed2,
    video_feed3,
)

urlpatterns = [
    # ========================
    # API V1 (Android / JSON-only)
    # ========================
    path("api/v1/dashboard", api_v1_dashboard, name="api_v1_dashboard_no_slash"),
    path("api/v1/dashboard/", api_v1_dashboard, name="api_v1_dashboard"),
    path("api/v1/form-rules", api_v1_form_rules, name="api_v1_form_rules_no_slash"),
    path("api/v1/form-rules/", api_v1_form_rules, name="api_v1_form_rules"),
    path("api/v1/stats/calories", api_v1_stats_calories, name="api_v1_stats_calories_no_slash"),
    path("api/v1/stats/calories/", api_v1_stats_calories, name="api_v1_stats_calories"),
    path("api/v1/stats/calories/breakdown", api_v1_stats_calories_breakdown, name="api_v1_stats_calories_breakdown_no_slash"),
    path("api/v1/stats/calories/breakdown/", api_v1_stats_calories_breakdown, name="api_v1_stats_calories_breakdown"),
    path("api/v1/stats/steps", api_v1_stats_steps, name="api_v1_stats_steps_no_slash"),
    path("api/v1/stats/steps/", api_v1_stats_steps, name="api_v1_stats_steps"),
    path("api/v1/stats/activity", api_v1_stats_activity, name="api_v1_stats_activity_no_slash"),
    path("api/v1/stats/activity/", api_v1_stats_activity, name="api_v1_stats_activity"),
    path("api/v1/workouts", api_v1_workouts, name="api_v1_workouts_no_slash"),
    path("api/v1/workouts/", api_v1_workouts, name="api_v1_workouts"),
    path("api/v1/workouts/<str:workout_id>", api_v1_workout_detail, name="api_v1_workout_detail_no_slash"),
    path("api/v1/workouts/<str:workout_id>/", api_v1_workout_detail, name="api_v1_workout_detail"),
    path("api/v1/workouts/<str:workout_id>/start", api_v1_workout_start, name="api_v1_workout_start_no_slash"),
    path("api/v1/workouts/<str:workout_id>/start/", api_v1_workout_start, name="api_v1_workout_start"),
    path(
        "api/v1/workout-sessions/<int:session_id>/finish",
        api_v1_workout_session_finish,
        name="api_v1_workout_session_finish_no_slash",
    ),
    path(
        "api/v1/workout-sessions/<int:session_id>/finish/",
        api_v1_workout_session_finish,
        name="api_v1_workout_session_finish",
    ),
    path("api/v1/runs/start", api_v1_run_start, name="api_v1_run_start_no_slash"),
    path("api/v1/runs/start/", api_v1_run_start, name="api_v1_run_start"),
    path("api/v1/runs/<int:run_id>/track", api_v1_run_track, name="api_v1_run_track_no_slash"),
    path("api/v1/runs/<int:run_id>/track/", api_v1_run_track, name="api_v1_run_track"),
    path("api/v1/runs/<int:run_id>/pause", api_v1_run_pause, name="api_v1_run_pause_no_slash"),
    path("api/v1/runs/<int:run_id>/pause/", api_v1_run_pause, name="api_v1_run_pause"),
    path("api/v1/runs/<int:run_id>/resume", api_v1_run_resume, name="api_v1_run_resume_no_slash"),
    path("api/v1/runs/<int:run_id>/resume/", api_v1_run_resume, name="api_v1_run_resume"),
    path("api/v1/runs/<int:run_id>/finish", api_v1_run_finish, name="api_v1_run_finish_no_slash"),
    path("api/v1/runs/<int:run_id>/finish/", api_v1_run_finish, name="api_v1_run_finish"),
    path("api/v1/runs/history", api_v1_run_history, name="api_v1_run_history_no_slash"),
    path("api/v1/runs/history/", api_v1_run_history, name="api_v1_run_history"),
    path("api/v1/runs/<int:run_id>", api_v1_run_detail, name="api_v1_run_detail_no_slash"),
    path("api/v1/runs/<int:run_id>/", api_v1_run_detail, name="api_v1_run_detail"),
    path("api/v1/quests", api_v1_quests, name="api_v1_quests_no_slash"),
    path("api/v1/quests/", api_v1_quests, name="api_v1_quests"),
    path("api/v1/quests/<int:quest_id>", api_v1_quest_detail, name="api_v1_quest_detail_no_slash"),
    path("api/v1/quests/<int:quest_id>/", api_v1_quest_detail, name="api_v1_quest_detail"),
    path("api/v1/quests/<int:quest_id>/start", api_v1_quest_start, name="api_v1_quest_start_no_slash"),
    path("api/v1/quests/<int:quest_id>/start/", api_v1_quest_start, name="api_v1_quest_start"),
    path("api/v1/quests/<int:quest_id>/claim", api_v1_quest_claim, name="api_v1_quest_claim_no_slash"),
    path("api/v1/quests/<int:quest_id>/claim/", api_v1_quest_claim, name="api_v1_quest_claim"),
    path("api/v1/leaderboard", api_v1_leaderboard, name="api_v1_leaderboard_no_slash"),
    path("api/v1/leaderboard/", api_v1_leaderboard, name="api_v1_leaderboard"),

    # ========================
    # BILLING / SUBSCRIPTION (RevenueCat)
    # ========================
    path("api/v1/subscription", api_v1_subscription, name="api_v1_subscription_no_slash"),
    path("api/v1/subscription/", api_v1_subscription, name="api_v1_subscription"),
    path("api/v1/billing/rcat", api_v1_billing_rcat, name="api_v1_billing_rcat_no_slash"),
    path("api/v1/billing/rcat/", api_v1_billing_rcat, name="api_v1_billing_rcat"),

    # ========================
    # COMPETITIVE PLATFORM
    # ========================
    path("api/v1/players/search", api_v1_players_search, name="api_v1_players_search_no_slash"),
    path("api/v1/players/search/", api_v1_players_search, name="api_v1_players_search"),
    path("api/v1/friends/mutual/<int:player_id>", api_v1_friends_mutual, name="api_v1_friends_mutual_no_slash"),
    path("api/v1/friends/mutual/<int:player_id>/", api_v1_friends_mutual, name="api_v1_friends_mutual"),
    path("api/v1/players/<int:player_id>", api_v1_player_public, name="api_v1_player_public_no_slash"),
    path("api/v1/players/<int:player_id>/", api_v1_player_public, name="api_v1_player_public"),
    path("api/v1/users/me", api_v1_users_me, name="api_v1_users_me_no_slash"),
    path("api/v1/users/me/", api_v1_users_me, name="api_v1_users_me"),
    path("api/v1/users/me/skills/upgrade", api_v1_users_me_upgrade_skill, name="api_v1_users_me_upgrade_skill_no_slash"),
    path("api/v1/users/me/skills/upgrade/", api_v1_users_me_upgrade_skill, name="api_v1_users_me_upgrade_skill"),
    path("api/v1/institutions/search", api_v1_institutions_search, name="api_v1_institutions_search_no_slash"),
    path("api/v1/institutions/search/", api_v1_institutions_search, name="api_v1_institutions_search"),
    path("api/v1/institutions", api_v1_institutions_create, name="api_v1_institutions_create_no_slash"),
    path("api/v1/institutions/", api_v1_institutions_create, name="api_v1_institutions_create"),
    path("api/v1/geo/regions", api_v1_geo_regions, name="api_v1_geo_regions_no_slash"),
    path("api/v1/geo/regions/", api_v1_geo_regions, name="api_v1_geo_regions"),
    path("api/v1/geo/cities", api_v1_geo_cities, name="api_v1_geo_cities_no_slash"),
    path("api/v1/geo/cities/", api_v1_geo_cities, name="api_v1_geo_cities"),
    path("api/v1/friends", api_v1_friends_list, name="api_v1_friends_list_no_slash"),
    path("api/v1/friends/", api_v1_friends_list, name="api_v1_friends_list"),
    path("api/v1/friends/request", api_v1_friends_request, name="api_v1_friends_request_no_slash"),
    path("api/v1/friends/request/", api_v1_friends_request, name="api_v1_friends_request"),
    path("api/v1/friends/<int:friendship_id>/accept", api_v1_friends_accept, name="api_v1_friends_accept_no_slash"),
    path("api/v1/friends/<int:friendship_id>/accept/", api_v1_friends_accept, name="api_v1_friends_accept"),
    path("api/v1/friends/<int:friendship_id>/reject", api_v1_friends_reject, name="api_v1_friends_reject_no_slash"),
    path("api/v1/friends/<int:friendship_id>/reject/", api_v1_friends_reject, name="api_v1_friends_reject"),
    path("api/v1/friends/<int:friendship_id>", api_v1_friends_delete, name="api_v1_friends_delete_no_slash"),
    path("api/v1/friends/<int:friendship_id>/", api_v1_friends_delete, name="api_v1_friends_delete"),
    path("api/v1/invites/redeem", api_v1_invites_redeem, name="api_v1_invites_redeem_no_slash"),
    path("api/v1/invites/redeem/", api_v1_invites_redeem, name="api_v1_invites_redeem"),
    path("api/v1/support/threads", api_v1_support_threads_list, name="api_v1_support_threads_list_no_slash"),
    path("api/v1/support/threads/", api_v1_support_threads_list, name="api_v1_support_threads_list"),
    path("api/v1/support/threads/create", api_v1_support_threads_create, name="api_v1_support_threads_create_no_slash"),
    path("api/v1/support/threads/create/", api_v1_support_threads_create, name="api_v1_support_threads_create"),
    path("api/v1/support/threads/<int:thread_id>", api_v1_support_thread_detail, name="api_v1_support_thread_detail_no_slash"),
    path("api/v1/support/threads/<int:thread_id>/", api_v1_support_thread_detail, name="api_v1_support_thread_detail"),
    path(
        "api/v1/support/threads/<int:thread_id>/messages",
        api_v1_support_thread_message,
        name="api_v1_support_thread_message_no_slash",
    ),
    path(
        "api/v1/support/threads/<int:thread_id>/messages/",
        api_v1_support_thread_message,
        name="api_v1_support_thread_message",
    ),
    path(
        "api/v1/support/threads/<int:thread_id>/close",
        api_v1_support_thread_close,
        name="api_v1_support_thread_close_no_slash",
    ),
    path(
        "api/v1/support/threads/<int:thread_id>/close/",
        api_v1_support_thread_close,
        name="api_v1_support_thread_close",
    ),
    path("api/v1/challenges", api_v1_challenges_list, name="api_v1_challenges_list_no_slash"),
    path("api/v1/challenges/", api_v1_challenges_list, name="api_v1_challenges_list"),
    path("api/v1/challenges/create", api_v1_challenges_create, name="api_v1_challenges_create_no_slash"),
    path("api/v1/challenges/create/", api_v1_challenges_create, name="api_v1_challenges_create"),
    path("api/v1/challenges/<int:challenge_id>/accept", api_v1_challenges_accept, name="api_v1_challenges_accept_no_slash"),
    path("api/v1/challenges/<int:challenge_id>/accept/", api_v1_challenges_accept, name="api_v1_challenges_accept"),
    path("api/v1/challenges/<int:challenge_id>/decline", api_v1_challenges_decline, name="api_v1_challenges_decline_no_slash"),
    path("api/v1/challenges/<int:challenge_id>/decline/", api_v1_challenges_decline, name="api_v1_challenges_decline"),
    path("api/v1/challenges/<int:challenge_id>/cancel", api_v1_challenges_cancel, name="api_v1_challenges_cancel_no_slash"),
    path("api/v1/challenges/<int:challenge_id>/cancel/", api_v1_challenges_cancel, name="api_v1_challenges_cancel"),
    path("api/v1/challenges/<int:challenge_id>/submit/", api_v1_challenges_submit, name="api_v1_challenges_submit"),
    path("api/v1/seasons/<int:season_id>/rankings", api_v1_season_rankings, name="api_v1_season_rankings_no_slash"),
    path("api/v1/seasons/<int:season_id>/rankings/", api_v1_season_rankings, name="api_v1_season_rankings"),
    path("api/v1/seasons/current", api_v1_seasons_current, name="api_v1_seasons_current_no_slash"),
    path("api/v1/seasons/current/", api_v1_seasons_current, name="api_v1_seasons_current"),
    path("api/v1/plan/current", api_v1_plan_current, name="api_v1_plan_current_no_slash"),
    path("api/v1/plan/current/", api_v1_plan_current, name="api_v1_plan_current"),
    path("api/v1/plan/generate", api_v1_plan_generate, name="api_v1_plan_generate_no_slash"),
    path("api/v1/plan/generate/", api_v1_plan_generate, name="api_v1_plan_generate"),
    path("api/v1/week-plan/current", api_v1_week_plan_current, name="api_v1_week_plan_current_no_slash"),
    path("api/v1/week-plan/current/", api_v1_week_plan_current, name="api_v1_week_plan_current"),
    path("api/v1/week-plan/refresh", api_v1_week_plan_refresh, name="api_v1_week_plan_refresh_no_slash"),
    path("api/v1/week-plan/refresh/", api_v1_week_plan_refresh, name="api_v1_week_plan_refresh"),
    path("api/v1/week-plan/log-session", api_v1_week_plan_log_session, name="api_v1_week_plan_log_no_slash"),
    path("api/v1/week-plan/log-session/", api_v1_week_plan_log_session, name="api_v1_week_plan_log"),
    path("api/v1/week-plan/rollover", api_v1_week_plan_rollover, name="api_v1_week_plan_rollover_no_slash"),
    path("api/v1/week-plan/rollover/", api_v1_week_plan_rollover, name="api_v1_week_plan_rollover"),

    # ========================
    # ASSESSMENT API (mobile / клиентский JSON)
    # ========================
    path("api/v1/users/me/assessment/", api_v1_post_user_assessment, name="api_v1_assessment"),
    path("api/v1/users/me/assessment/dev/", api_v1_post_user_assessment_dev, name="api_v1_assessment_dev"),

    # ========================
    # PWA
    # ========================
    path("sw.js", service_worker_js, name="service_worker"),
    path("set-language/", set_language_view, name="set_language"),

    # ========================
    # PUBLIC PAGES
    # ========================
    path("", home_page, name="home"),
    path("home/", home_page, name="home_alt"),
    path("index/", home_page, name="index"),
    path("privacy/", privacy_policy_page, name="privacy_policy"),
    path("privacy-policy/", privacy_policy_page, name="privacy_policy_alt"),
    path("registration/", register_page, name="registration"),

    # Authentication
    # --- Native app JSON auth (session cookie) ---
    path("api/auth/me/", api_auth_me, name="api_auth_me"),
    path("api/auth/login/", api_auth_login, name="api_auth_login"),
    path("api/auth/telegram/", api_auth_telegram, name="api_auth_telegram"),
    path("api/auth/register/", api_auth_register, name="api_auth_register"),
    path("api/auth/logout/", api_auth_logout, name="api_auth_logout"),
    path(
        "api/auth/resend-verification/",
        api_auth_resend_verification,
        name="api_auth_resend_verification",
    ),
    path(
        "api/auth/verify-email/",
        api_auth_verify_email,
        name="api_auth_verify_email",
    ),
    path(
        "verify-email/<str:token>/",
        verify_email_page,
        name="verify_email",
    ),

    path("login/", login_page, name="login_page"),
    path("signin/", login_page, name="signin"),
    path("register/", register_page, name="register_page"),
    path("signup/", register_page, name="signup"),
    path("welcome/", welcome_page, name="welcome_page"),
    path("logout/", logout_view, name="logout"),
    path("signout/", logout_view, name="signout"),
    path("app/", miniapp_page, name="miniapp"),
    path("quick-login/", quick_login, name="quick_login"),
    path("demo/", quick_login, name="demo_login"),

    # ========================
    # AUTHENTICATED PAGES
    # ========================
    path("dashboard/", dashboard_page, name="dashboard"),
    path("profile/", profile_page, name="profile"),
    path("fitness-profile/", fitness_profile_page, name="fitness_profile"),
    path("workouts/", workouts_page, name="workouts"),
    path("workouts/create/", workout_builder_page, name="workout_builder"),
    path("training/", workouts_page, name="training"),
    path("exercises/", workouts_page, name="exercises"),
    path("quests/", quests_page, name="quests"),
    path("missions/", quests_page, name="missions"),
    path("stats/", stats_page, name="stats"),
    path("statistics/", stats_page, name="statistics"),
    path("analytics/", stats_page, name="analytics"),
    path("leaderboard/", leaderboard_page, name="leaderboard"),
    path("leaderboard/player/<int:player_id>/", profile_view_page, name="profile_view"),
    path("rating/", leaderboard_page, name="rating"),
    path("settings/", settings_page, name="settings"),
    path("account/", settings_page, name="account"),
    path("skills/", skills_page, name="skills"),

    # ========================
    # TRAINING PAGES
    # ========================
    path("train/pushups/", training_page, kwargs={"exercise": "pushups"}, name="train_pushups"),
    path("train/squats/", training_page, kwargs={"exercise": "squats"}, name="train_squats"),
    path("train/crunches/", training_page, kwargs={"exercise": "crunches"}, name="train_crunches"),
    path("train/planks/", training_page, kwargs={"exercise": "planks"}, name="train_planks"),
    path("train/pullups/", training_page, kwargs={"exercise": "pullups"}, name="train_pullups"),
    path("train/<str:exercise>/", training_page, name="training"),

    # ========================
    # AI API ENDPOINTS
    # ========================
    path("api/ai/process-frame/", process_ai_frame, name="api_process_frame"),
    path("api/ai/process/", process_ai_frame, name="api_ai_process"),
    path("api/ai/process-landmarks/", process_landmarks, name="api_process_landmarks"),
    path("api/ai/state/", get_ai_state, name="api_ai_state"),
    path("api/ai/status/", get_ai_state, name="api_ai_status"),
    path("api/ai/reset/", reset_ai_state, name="api_ai_reset"),
    path("api/ai/clear/", reset_ai_state, name="api_ai_clear"),
    path("api/csrf-token/", get_csrf_token, name="api_csrf_token"),
    path("api/csrf/", get_csrf_token, name="api_csrf"),

    # ========================
    # HUD API ENDPOINTS
    # ========================
    path("api/hud/state/", get_hud_state, name="api_hud_state"),
    path("api/hud/status/", get_hud_state, name="api_hud_status"),
    path("api/hud/real-time/", get_real_time_hud_data, name="api_hud_real_time"),
    path("api/hud/unified/", get_unified_hud_data, name="api_hud_unified"),
    path("api/hud/data/", get_hud_data, name="api_hud_data"),
    path("api/hud/", get_hud_data, name="api_hud"),

    # ========================
    # WORKOUT API ENDPOINTS
    # ========================
    path("api/workouts/start/", start_workout, name="api_workout_start"),
    path("api/workouts/begin/", start_workout, name="api_workout_begin"),
    path("api/workouts/complete/", complete_workout, name="api_workout_complete"),
    path("api/workouts/finish/", complete_workout, name="api_workout_finish"),
    path("api/save-set/<str:exercise_type>/", save_workout_set, name="api_save_set"),
    path("api/workouts/current/<str:exercise_type>/", get_current_workout, name="api_workout_current"),
    path("api/workouts/status/<str:exercise_type>/", get_current_workout, name="api_workout_status"),
    path("api/workouts/reset/", reset_workout, name="api_workout_reset"),
    path("api/workouts/clear/", reset_workout, name="api_workout_clear"),
    path("api/workout-builder/chat/", api_workout_builder_chat, name="api_workout_builder_chat"),
    path("api/fitness-profile/save/", api_save_fitness_profile, name="api_fitness_profile_save"),
    path("api/ai/workout-plan/", api_generate_workout_plan, name="api_ai_workout_plan"),

    # ========================
    # QUEST API ENDPOINTS
    # ========================
    path("api/quests/", get_quests, name="api_quests"),
    path("api/quests/all/", get_quests, name="api_quests_all"),

    # ВАЖНО: это нужно для автообновления (quests.html)
    path("api/quests-data/", quests_data, name="api_quests_data"),

    path("api/quests/start/", start_quest, name="api_quests_start"),
    path("api/quests/cancel/", cancel_quest, name="api_quests_cancel"),
    path("api/quests/complete/", complete_quest, name="api_quests_complete"),
    path("api/quests/finish/", complete_quest, name="api_quests_finish"),

    # ========================
    # STATS API ENDPOINTS
    # ========================
    path("api/stats/basic/", get_basic_stats, name="api_stats_basic"),
    path("api/stats/", get_basic_stats, name="api_stats"),
    path("api/stats/history/", get_workout_history, name="api_stats_history"),
    path("api/stats/workouts/", get_workout_history, name="api_stats_workouts"),
    path("api/stats/daily/", get_daily_activity, name="api_stats_daily"),
    path("api/stats/activity/", get_daily_activity, name="api_stats_activity"),
    path("api/stats/exercise/", get_exercise_breakdown, name="api_stats_exercise"),
    path("api/stats/breakdown/", get_exercise_breakdown, name="api_stats_breakdown"),

    # ВАЖНО: твой stats.html ждёт это
    path("api/stats/combined/", api_stats_combined, name="api_stats_combined"),

    # ========================
    # PLAYER API ENDPOINTS
    # ========================
    path("api/player/profile/", get_player_profile, name="api_player_profile"),
    path("api/player/", get_player_profile, name="api_player"),
    path("api/player/upgrade-skill/", upgrade_skill, name="api_player_upgrade_skill"),
    path("api/player/upgrade/", upgrade_skill, name="api_player_upgrade"),
    path("api/player/add-currency/", add_currency, name="api_player_add_currency"),
    path("api/player/currency/add/", add_currency, name="api_player_currency_add"),
    path("api/player/update-streak/", update_login_streak, name="api_player_update_streak"),
    path("api/player/streak/", update_login_streak, name="api_player_streak"),

    # ========================
    # LEGACY VIDEO ENDPOINTS
    # ========================
    path("video/feed/pushups/", video_feed_pushups, name="video_feed_pushups"),
    path("video/feed/squats/", video_feed_squats, name="video_feed_squats"),
    path("video/feed/pullups/", video_feed_pullups, name="video_feed_pullups"),
    path("video/feed/crunches/", video_feed_crunches, name="video_feed_crunches"),
    path("video/feed/planks/", video_feed_planks, name="video_feed_planks"),
    path("video_feed/", video_feed, name="video_feed"),
    path("video_feed1/", video_feed1, name="video_feed1"),
    path("video_feed2/", video_feed2, name="video_feed2"),
    path("video_feed3/", video_feed3, name="video_feed3"),

    # ========================
    # LEGACY REDIRECTS
    # ========================
    path("workouts/pushups/", lambda request: redirect("/train/pushups/")),
    path("workouts/squats/", lambda request: redirect("/train/squats/")),
    path("workouts/pull-ups/", lambda request: redirect("/train/pullups/")),
    path("workouts/crunches/", lambda request: redirect("/train/crunches/")),
    path("workouts/planks/", lambda request: redirect("/train/planks/")),
]

# ========================
# ERROR HANDLERS
# ========================
handler404 = "main.views.page_views.handler404"
handler500 = "main.views.page_views.handler500"
handler403 = "main.views.page_views.handler403"
handler400 = "main.views.page_views.handler400"
