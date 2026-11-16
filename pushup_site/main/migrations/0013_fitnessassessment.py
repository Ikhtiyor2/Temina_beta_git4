# Generated manually for FitnessAssessment API

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0012_remove_activeworkout_unique_active_workout_per_player_exercise_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FitnessAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profile_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                ("gender", models.CharField(blank=True, max_length=32)),
                ("age_years", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("height_cm", models.FloatField(blank=True, null=True)),
                ("weight_kg", models.FloatField(blank=True, null=True)),
                ("primary_goal", models.CharField(blank=True, max_length=32)),
                ("fitness_level", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("workouts_per_week", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("preferred_session_minutes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("has_chronic_conditions", models.BooleanField(default=False)),
                ("body_scan_consent", models.BooleanField(default=False)),
                ("body_scan_skipped", models.BooleanField(default=False)),
                ("assessment_confirmed", models.BooleanField(default=False)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("assessment_completed_at", models.DateTimeField(auto_now_add=True)),
                ("next_recommended_program_id", models.CharField(blank=True, max_length=64, null=True)),
                ("generated_plan_version", models.CharField(blank=True, default="", max_length=32)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fitness_assessments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-assessment_completed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="fitnessassessment",
            index=models.Index(fields=["user", "-assessment_completed_at"], name="main_fitnes_user_id_bcd372_idx"),
        ),
    ]
# Generated manually for FitnessAssessment API

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0012_remove_activeworkout_unique_active_workout_per_player_exercise_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FitnessAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profile_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                ("gender", models.CharField(blank=True, max_length=32)),
                ("age_years", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("height_cm", models.FloatField(blank=True, null=True)),
                ("weight_kg", models.FloatField(blank=True, null=True)),
                ("primary_goal", models.CharField(blank=True, max_length=32)),
                ("fitness_level", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("workouts_per_week", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("preferred_session_minutes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("has_chronic_conditions", models.BooleanField(default=False)),
                ("body_scan_consent", models.BooleanField(default=False)),
                ("body_scan_skipped", models.BooleanField(default=False)),
                ("assessment_confirmed", models.BooleanField(default=False)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("assessment_completed_at", models.DateTimeField(auto_now_add=True)),
                ("next_recommended_program_id", models.CharField(blank=True, max_length=64, null=True)),
                ("generated_plan_version", models.CharField(blank=True, default="", max_length=32)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fitness_assessments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-assessment_completed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="fitnessassessment",
            index=models.Index(fields=["user", "-assessment_completed_at"], name="main_fitnes_user_id_bcd372_idx"),
        ),
    ]
