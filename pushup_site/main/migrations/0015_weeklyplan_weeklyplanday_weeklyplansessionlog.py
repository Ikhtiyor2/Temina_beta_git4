# Generated manually: weekly training plan.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0014_runsession_runtrackpoint"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeeklyPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("week_start", models.DateField(db_index=True)),
                ("difficulty_tier", models.PositiveSmallIntegerField(default=1)),
                ("source", models.CharField(default="assessment", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assessment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="weekly_plans",
                        to="main.fitnessassessment",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="weekly_plans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-week_start"]},
        ),
        migrations.CreateModel(
            name="WeeklyPlanDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day_index", models.PositiveSmallIntegerField()),
                ("is_rest", models.BooleanField(default=False)),
                ("counter_profile_id", models.CharField(blank=True, default="", max_length=64)),
                ("display_title", models.CharField(blank=True, default="", max_length=160)),
                ("target_sets", models.PositiveSmallIntegerField(default=0)),
                ("target_reps", models.PositiveSmallIntegerField(default=0)),
                ("duration_sec", models.PositiveIntegerField(blank=True, null=True)),
                ("focus_note", models.CharField(blank=True, default="", max_length=256)),
                ("completed", models.BooleanField(default=False)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="days",
                        to="main.weeklyplan",
                    ),
                ),
            ],
            options={"ordering": ["day_index"]},
        ),
        migrations.CreateModel(
            name="WeeklyPlanSessionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("counter_profile_id", models.CharField(max_length=64)),
                ("reps", models.PositiveIntegerField(default=0)),
                ("duration_sec", models.PositiveIntegerField(default=0)),
                ("quality_score", models.FloatField(blank=True, null=True)),
                ("errors_json", models.JSONField(blank=True, default=list)),
                ("ai_feedback", models.TextField(blank=True, default="")),
                ("logged_at", models.DateTimeField(auto_now_add=True)),
                (
                    "day",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_logs",
                        to="main.weeklyplanday",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_logs",
                        to="main.weeklyplan",
                    ),
                ),
            ],
            options={"ordering": ["-logged_at"]},
        ),
        migrations.AddConstraint(
            model_name="weeklyplan",
            constraint=models.UniqueConstraint(fields=("user", "week_start"), name="uniq_weekly_plan_user_week"),
        ),
        migrations.AddConstraint(
            model_name="weeklyplanday",
            constraint=models.UniqueConstraint(fields=("plan", "day_index"), name="uniq_weekly_plan_day_index"),
        ),
    ]
