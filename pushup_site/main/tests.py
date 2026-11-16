import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from main.models import FitnessAssessment, Player, RunSession, WeeklyPlan, WeeklyPlanDay, WeeklyPlanDayExercise, WorkoutSession


class ApiV1Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="Makise", password="pass12345")
        self.player = Player.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_dashboard_returns_expected_structure(self):
        res = self.client.get("/api/v1/dashboard/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("profile", data)
        self.assertIn("metrics", data)
        self.assertIn("featuredWorkout", data)
        self.assertIn("aiSuggestion", data)
        self.assertIn("recentWorkouts", data)
        metrics = data["metrics"]
        self.assertEqual(metrics["stepsToday"], 0)
        self.assertEqual(metrics["caloriesToday"], 0)
        self.assertEqual(metrics["calorieGoal"], 0)
        self.assertEqual(metrics["stepsGoal"], 0)
        self.assertEqual(metrics["workoutStreak"], 0)

    def test_dashboard_metrics_come_from_workouts(self):
        WorkoutSession.objects.create(
            player=self.player,
            exercise_type="PUSHUP",
            reps_count=20,
            duration_seconds=600,
            calories_burned=120,
        )
        res = self.client.get("/api/v1/dashboard/")
        metrics = res.json()["metrics"]
        self.assertEqual(metrics["caloriesToday"], 120)
        self.assertEqual(metrics["activeMinutes"], 10)
        self.assertEqual(metrics["workoutsToday"], 1)
        self.assertEqual(metrics["repsToday"], 20)
        self.assertEqual(metrics["workoutStreak"], 1)
        self.assertEqual(metrics["stepsToday"], 0)

    def test_stats_endpoints_return_points(self):
        WorkoutSession.objects.create(
            player=self.player,
            exercise_type="PUSHUP",
            reps_count=20,
            duration_seconds=600,
            calories_burned=120,
        )
        for path in (
            "/api/v1/stats/calories/?period=week",
            "/api/v1/stats/steps/?period=week",
            "/api/v1/stats/activity/?period=week",
        ):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["period"], "week")
            self.assertIn("points", data)
            self.assertTrue(len(data["points"]) > 0)

    def test_invalid_period_returns_400_json(self):
        res = self.client.get("/api/v1/stats/calories/?period=year")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "invalid_period")

    def test_workouts_list_returns_workouts(self):
        res = self.client.get("/api/v1/workouts/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()["workouts"]) > 0)

    def test_workout_detail_returns_one_workout(self):
        res = self.client.get("/api/v1/workouts/pushup_classic/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], "pushup_classic")
        self.assertIn("exercises", res.json())

    def test_workout_start_creates_session(self):
        res = self.client.post("/api/v1/workouts/pushup_classic/start/")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "started")
        self.assertTrue(WorkoutSession.objects.filter(id=int(data["sessionId"])).exists())

    def test_workout_finish_completes_session(self):
        start = self.client.post("/api/v1/workouts/pushup_classic/start/")
        session_id = start.json()["sessionId"]
        payload = {
            "durationSec": 1200,
            "calories": 220,
            "exercises": [{"exerciseId": "pushups", "reps": 36, "sets": 3}],
        }
        res = self.client.post(
            f"/api/v1/workout-sessions/{session_id}/finish/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "finished")
        self.assertEqual(data["durationSec"], 1200)
        self.assertEqual(data["reps"], 36)

    def test_workout_finish_clamps_unrealistic_duration(self):
        start = self.client.post("/api/v1/workouts/pushup_classic/start/")
        self.assertEqual(start.status_code, 201)
        session_id = start.json()["sessionId"]
        payload = {
            "durationSec": 9_000_000,
            "calories": 0,
            "exercises": [{"exerciseId": "pushups", "reps": 0, "sets": 1}],
        }
        res = self.client.post(
            f"/api/v1/workout-sessions/{session_id}/finish/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["durationSec"], 4 * 60 * 60)
        session = WorkoutSession.objects.get(id=int(session_id))
        self.assertEqual(session.duration_seconds, 4 * 60 * 60)

    def test_runs_start_creates_running_session(self):
        res = self.client.post("/api/v1/runs/start/")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["status"], "running")

    def test_runs_track_accepts_points_and_recalculates_metrics(self):
        start = self.client.post("/api/v1/runs/start/")
        run_id = start.json()["runId"]
        now = timezone.now()
        payload = {
            "points": [
                {
                    "lat": 43.238,
                    "lng": 76.945,
                    "timestamp": now.isoformat(),
                    "accuracy": 8.5,
                    "speedMps": 2.8,
                },
                {
                    "lat": 43.239,
                    "lng": 76.946,
                    "timestamp": (now + timedelta(seconds=60)).isoformat(),
                    "accuracy": 8.0,
                    "speedMps": 2.9,
                },
            ]
        }
        res = self.client.patch(
            f"/api/v1/runs/{run_id}/track/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["distanceKm"], 0)
        self.assertEqual(len(data["points"]), 2)

    def test_runs_pause_resume_changes_status(self):
        run_id = self.client.post("/api/v1/runs/start/").json()["runId"]
        paused = self.client.post(f"/api/v1/runs/{run_id}/pause/")
        self.assertEqual(paused.status_code, 200)
        self.assertEqual(paused.json()["status"], "paused")
        resumed = self.client.post(f"/api/v1/runs/{run_id}/resume/")
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()["status"], "running")

    def test_runs_finish_completes_session(self):
        run_id = self.client.post("/api/v1/runs/start/").json()["runId"]
        res = self.client.post(f"/api/v1/runs/{run_id}/finish/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "finished")

    def test_runs_history_returns_user_runs(self):
        RunSession.objects.create(user=self.user, status=RunSession.STATUS_FINISHED)
        res = self.client.get("/api/v1/runs/history/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["runs"]), 1)

    def test_unauthenticated_user_gets_json_401(self):
        self.client.logout()
        res = self.client.get("/api/v1/dashboard/")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json(), {"detail": "Authentication required"})

    def test_week_plan_current_localizes_saved_russian_content_for_uz(self):
        assessment = FitnessAssessment.objects.create(
            user=self.user,
            fitness_level=1,
            workouts_per_week=3,
            payload={},
        )
        plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=timezone.localdate() - timedelta(days=timezone.localdate().weekday()),
            difficulty_tier=1,
            assessment=assessment,
            source="assessment",
        )
        day = WeeklyPlanDay.objects.create(
            plan=plan,
            day_index=0,
            is_rest=False,
            display_title="Силовой комплекс",
            focus_note="Классические отжимания · Классические приседания · Классические скручивания",
        )
        WeeklyPlanDayExercise.objects.create(
            day=day,
            sort_order=0,
            counter_profile_id="pushup_classic",
            display_title="Классические отжимания",
            target_sets=3,
            target_reps=12,
        )
        WeeklyPlanDayExercise.objects.create(
            day=day,
            sort_order=1,
            counter_profile_id="squat_classic",
            display_title="Классические приседания",
            target_sets=3,
            target_reps=15,
        )
        WeeklyPlanDayExercise.objects.create(
            day=day,
            sort_order=2,
            counter_profile_id="crunch_classic",
            display_title="Классические скручивания",
            target_sets=3,
            target_reps=16,
        )
        WeeklyPlanDay.objects.create(
            plan=plan,
            day_index=1,
            is_rest=True,
            display_title="Отдых",
            focus_note="Восстановление и сон",
        )

        res = self.client.get("/api/v1/week-plan/current/", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(res.status_code, 200)
        payload = res.json()["weekPlan"]["days"]

        train_day = next(d for d in payload if d["dayIndex"] == 0)
        self.assertEqual(train_day["title"], "Kuch kompleksi")
        self.assertEqual(
            train_day["focusNote"],
            "Klassik otjimaniyalar · Klassik o‘tirib-turishlar · Klassik bukilishlar",
        )
        self.assertEqual(train_day["exercises"][0]["title"], "Klassik otjimaniyalar")

        rest_day = next(d for d in payload if d["dayIndex"] == 1)
        self.assertEqual(rest_day["title"], "Dam olish")
        self.assertEqual(rest_day["focusNote"], "Tiklanish va uyqu")


class CompetitivePlatformTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="athlete", password="pass12345")
        self.player = Player.objects.create(user=self.user, city="Алматы")
        self.client.force_login(self.user)

    def test_users_me_profile(self):
        res = self.client.get("/api/v1/users/me/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["username"], "athlete")
        self.assertIn("inviteCode", data)
        self.assertIn("workoutStreak", data)
        self.assertEqual(data["totalWorkouts"], 0)

    def test_leaderboard_scoped_city(self):
        res = self.client.get("/api/v1/leaderboard/?scope=city")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["scope"], "city")
        self.assertGreaterEqual(data["totalPlayers"], 1)

    def test_leaderboard_excludes_staff_and_superusers(self):
        staff_user = User.objects.create_user(username="staffer", password="pass12345", is_staff=True)
        Player.objects.create(user=staff_user, city="Алматы", level=99, exp=999)
        admin_user = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="pass12345"
        )
        Player.objects.create(user=admin_user, city="Алматы", level=100, exp=1000)

        res = self.client.get("/api/v1/leaderboard/?scope=city")
        self.assertEqual(res.status_code, 200)
        usernames = [e["username"] for e in res.json()["entries"]]
        self.assertIn("athlete", usernames)
        self.assertNotIn("staffer", usernames)
        self.assertNotIn("boss", usernames)

    def test_workout_complete_awards_xp(self):
        res = self.client.post(
            "/api/workouts/complete/",
            data=json.dumps({"exercise_type": "PUSHUP", "reps": 10, "duration_sec": 60}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertGreater(body.get("xp_earned", 0), 0)
        self.player.refresh_from_db()
        self.assertGreater(float(self.player.exp), 0)
        self.assertIn("baseXp", body)
        self.assertIn("skillBonus", body)

    def test_invite_redeem_auto_accepts_friendship(self):
        inviter = User.objects.create_user(username="inviter", password="pass12345")
        inviter_player = Player.objects.create(user=inviter)
        code = inviter_player.invite_code
        friend = User.objects.create_user(username="friend", password="pass12345")
        Player.objects.create(user=friend)
        self.client.logout()
        self.client.force_login(friend)
        res = self.client.post(
            "/api/v1/invites/redeem/",
            data=json.dumps({"inviteCode": code}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("autoAccepted"))

    def test_player_search(self):
        User.objects.create_user(username="athlete2", password="pass12345")
        Player.objects.create(user=User.objects.get(username="athlete2"))
        res = self.client.get("/api/v1/players/search/?q=athlete2")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(p["username"] == "athlete2" for p in res.json()["players"]))

    def test_challenge_xp_transfer(self):
        from main.models import Challenge, Friendship

        opponent_user = User.objects.create_user(username="rival", password="pass12345")
        opponent = Player.objects.create(user=opponent_user, level=5, exp=200)
        self.player.level = 5
        self.player.exp = 200
        self.player.save()
        Friendship.objects.create(
            from_player=self.player,
            to_player=opponent,
            status=Friendship.STATUS_ACCEPTED,
        )
        ch = Challenge.objects.create(
            challenger=self.player,
            opponent=opponent,
            exercise_type="PUSHUP",
            wager_xp=20,
            deadline=timezone.now() + timedelta(hours=48),
            status=Challenge.STATUS_ACTIVE,
        )
        self.player.xp_escrow = 20
        opponent.xp_escrow = 20
        self.player.save(update_fields=["xp_escrow"])
        opponent.save(update_fields=["xp_escrow"])
        loser_xp_before = float(opponent.exp)
        self.client.post(
            f"/api/v1/challenges/{ch.id}/submit/",
            data=json.dumps({"result": 30}),
            content_type="application/json",
        )
        self.client.force_login(opponent_user)
        self.client.post(
            f"/api/v1/challenges/{ch.id}/submit/",
            data=json.dumps({"result": 10}),
            content_type="application/json",
        )
        opponent.refresh_from_db()
        self.assertLess(float(opponent.exp), loser_xp_before)
        ch.refresh_from_db()
        self.assertEqual(ch.status, Challenge.STATUS_COMPLETED)
        self.assertEqual(ch.winner_id, self.player.id)


def _signed_init_data(bot_token, user, auth_date=None):
    payload = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "query_id": "AAE",
        "user": json.dumps(user, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret, check.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


@override_settings(TELEGRAM_BOT_TOKEN="123456:TESTTOKEN")
class TelegramAuthTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_rotated_csrf_cookie_allows_profile_save_after_login(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/app/")
        previous_token = client.cookies["csrftoken"].value
        init_data = _signed_init_data("123456:TESTTOKEN", {"id": 4242})
        res = client.post(
            "/api/auth/telegram/", data=json.dumps({"initData": init_data}),
            content_type="application/json", HTTP_X_CSRFTOKEN=previous_token,
        )
        self.assertEqual(res.status_code, 200)
        current_token = client.cookies["csrftoken"].value
        self.assertNotEqual(current_token, previous_token)
        res = client.patch(
            "/api/v1/users/me/", data=json.dumps({"city": "Tashkent"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=current_token,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Player.objects.get(telegram_id=4242).city, "Tashkent")

    def test_existing_username_is_not_linked_to_telegram(self):
        existing = User.objects.create_user(username="tg_4242", password="existing-password")
        init_data = _signed_init_data("123456:TESTTOKEN", {"id": 4242, "first_name": "Amina"})
        res = self.client.post(
            "/api/auth/telegram/", data=json.dumps({"initData": init_data}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        player = Player.objects.get(telegram_id=4242)
        self.assertNotEqual(player.user_id, existing.pk)
        self.assertFalse(player.user.has_usable_password())
        self.assertEqual(int(self.client.session["_auth_user_id"]), player.user_id)

    def test_disabled_telegram_account_cannot_log_in(self):
        user = User.objects.create_user(username="disabled", is_active=False)
        Player.objects.create(user=user, telegram_id=4242)
        init_data = _signed_init_data("123456:TESTTOKEN", {"id": 4242})
        res = self.client.post(
            "/api/auth/telegram/", data=json.dumps({"initData": init_data}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], "account_disabled")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_payload_types_return_400(self):
        for payload in ([], None, {"initData": 123}):
            with self.subTest(payload=payload):
                res = self.client.post(
                    "/api/auth/telegram/", data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(res.status_code, 400)

    def test_future_init_data_is_rejected(self):
        init_data = _signed_init_data(
            "123456:TESTTOKEN", {"id": 4242}, auth_date=int(time.time()) + 3600,
        )
        res = self.client.post(
            "/api/auth/telegram/", data=json.dumps({"initData": init_data}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], "stale")

    def test_creates_player_and_session(self):
        photo = "https://t.me/i/userpic/320/" + ("x" * 220) + ".jpg"
        init_data = _signed_init_data(
            "123456:TESTTOKEN",
            {
                "id": 4242,
                "first_name": "Amina",
                "last_name": "Karimova",
                "username": "amina",
                "photo_url": photo,
            },
        )
        res = self.client.post(
            "/api/auth/telegram/",
            data=json.dumps({"initData": init_data}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["isNew"])
        self.assertEqual(body["user"]["displayName"], "Amina Karimova")
        self.assertEqual(body["user"]["avatarUrl"], photo)
        player = Player.objects.get(telegram_id=4242)
        self.assertEqual(player.user.username, "tg_4242")
        self.assertFalse(player.user.has_usable_password())
        self.assertEqual(player.display_name, "Amina Karimova")
        self.assertEqual(player.telegram_username, "amina")
        self.assertEqual(player.avatar_url, photo)
        me = self.client.get("/api/auth/me/")
        self.assertTrue(me.json()["authenticated"])
        profile = self.client.get("/api/v1/users/me/").json()
        self.assertTrue(profile["fromTelegram"])
        self.assertEqual(profile["avatarUrl"], photo)
        self.assertEqual(profile["workoutStreak"], 0)

    def test_repeat_login_syncs_telegram_profile(self):
        init_data = _signed_init_data("123456:TESTTOKEN", {"id": 7, "first_name": "Ali"})
        self.client.post(
            "/api/auth/telegram/",
            data=json.dumps({"initData": init_data}),
            content_type="application/json",
        )
        player = Player.objects.get(telegram_id=7)
        player.display_name = "Качмен"
        player.save(update_fields=["display_name"])
        self.client.logout()
        again = _signed_init_data(
            "123456:TESTTOKEN",
            {
                "id": 7,
                "first_name": "Ali",
                "last_name": "Nur",
                "username": "ali_new",
                "photo_url": "https://t.me/i/userpic/320/ali.jpg",
            },
        )
        res = self.client.post(
            "/api/auth/telegram/",
            data=json.dumps({"initData": again}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["isNew"])
        player.refresh_from_db()
        self.assertEqual(player.display_name, "Ali Nur")
        self.assertEqual(player.telegram_username, "ali_new")
        self.assertEqual(player.avatar_url, "https://t.me/i/userpic/320/ali.jpg")

    def test_bad_signature_is_rejected(self):
        init_data = _signed_init_data("123456:TESTTOKEN", {"id": 1, "first_name": "A"})
        broken = init_data.replace("hash=", "hash=00", 1)
        res = self.client.post(
            "/api/auth/telegram/",
            data=json.dumps({"initData": broken}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], "bad_signature")
        self.assertFalse(Player.objects.filter(telegram_id=1).exists())

    def test_stale_init_data_is_rejected(self):
        init_data = _signed_init_data(
            "123456:TESTTOKEN",
            {"id": 9, "first_name": "Old"},
            auth_date=int(time.time()) - 90000,
        )
        res = self.client.post(
            "/api/auth/telegram/",
            data=json.dumps({"initData": init_data}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], "stale")

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_missing_bot_token_is_not_configured(self):
        res = self.client.post(
            "/api/auth/telegram/",
            data=json.dumps({"initData": "auth_date=1&hash=abc"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["error"], "telegram_not_configured")


class MiniAppPageTests(TestCase):
    def test_app_page_is_its_own_document(self):
        res = self.client.get("/app/", HTTP_HOST="localhost")
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertIn("miniapp.js", body)
        self.assertIn("miniapp-i18n.js", body)
        self.assertIn("temina-camera-pose.css", body)
        self.assertIn("telegram-web-app.js", body)
        self.assertIn("data-tab=\"competitions\"", body)
        self.assertNotIn("sidebar", body)

    def test_set_language_accepts_uzbek(self):
        res = self.client.get("/set-language/?lang=uz&next=/app/")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.cookies["temina_lang"].value, "uz")


class RegistrationCaptchaTests(TestCase):
    def _post(self):
        return self.client.post(
            "/register/",
            {
                "username": "captcha_bot_user",
                "email": "captcha-bot@example.com",
                "first_name": "Bot",
                "password1": "s3cret-pass",
                "password2": "s3cret-pass",
            },
            HTTP_HOST="localhost",
        )

    @override_settings(TURNSTILE_SITE_KEY="site-key", TURNSTILE_SECRET_KEY="secret-key")
    def test_register_without_token_does_not_create_user(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(username="captcha_bot_user").exists())
        self.assertIn("challenges.cloudflare.com/turnstile", res.content.decode())
        self.assertIn("interaction-only", res.content.decode())

    @override_settings(DEBUG=False, TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="")
    def test_production_without_keys_closes_signup(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(username="captcha_bot_user").exists())
        self.assertIn("disabled", res.content.decode())

    @override_settings(DEBUG=True, TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="")
    def test_debug_without_keys_skips_widget(self):
        res = self.client.get("/register/", HTTP_HOST="localhost")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("challenges.cloudflare.com/turnstile", res.content.decode())
