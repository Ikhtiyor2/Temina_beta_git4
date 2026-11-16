# 1Generated manually for API v1 run tracking.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0013_fitnessassessment"),
    ]

    operations = [
        migrations.CreateModel(
            name="RunSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[("running", "Running"), ("paused", "Paused"), ("finished", "Finished")],
                        default="running",
                        max_length=16,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("paused_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("distance_km", models.FloatField(default=0)),
                ("duration_sec", models.PositiveIntegerField(default=0)),
                ("pace_min_per_km", models.FloatField(default=0)),
                ("avg_speed", models.FloatField(default=0)),
                ("calories_estimate", models.FloatField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="run_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="RunTrackPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lat", models.FloatField()),
                ("lng", models.FloatField()),
                ("timestamp", models.DateTimeField()),
                ("accuracy", models.FloatField(blank=True, null=True)),
                ("speed_mps", models.FloatField(blank=True, null=True)),
                ("sequence", models.PositiveIntegerField(default=0)),
                (
                    "run_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="points",
                        to="main.runsession",
                    ),
                ),
            ],
            options={
                "ordering": ["sequence", "timestamp", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="runsession",
            index=models.Index(fields=["user", "-started_at"], name="main_runses_user_id_d3e0b9_idx"),
        ),
        migrations.AddIndex(
            model_name="runsession",
            index=models.Index(fields=["status"], name="main_runses_status_f8a809_idx"),
        ),
        migrations.AddIndex(
            model_name="runtrackpoint",
            index=models.Index(fields=["run_session", "sequence"], name="main_runtra_run_ses_02db70_idx"),
        ),
        migrations.AddIndex(
            model_name="runtrackpoint",
            index=models.Index(fields=["timestamp"], name="main_runtra_timesta_6c2b85_idx"),
        ),
    ]
