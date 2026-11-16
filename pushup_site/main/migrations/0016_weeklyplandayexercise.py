# Multi-exercise weekly plan days.

import django.db.models.deletion
from django.db import migrations, models


def migrate_day_to_exercises(apps, schema_editor):
    WeeklyPlanDay = apps.get_model("main", "WeeklyPlanDay")
    WeeklyPlanDayExercise = apps.get_model("main", "WeeklyPlanDayExercise")
    for day in WeeklyPlanDay.objects.filter(is_rest=False).exclude(counter_profile_id=""):
        WeeklyPlanDayExercise.objects.create(
            day_id=day.id,
            sort_order=0,
            counter_profile_id=day.counter_profile_id,
            display_title=day.display_title,
            target_sets=day.target_sets or 3,
            target_reps=day.target_reps or 0,
            duration_sec=day.duration_sec,
            completed=day.completed,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0015_weeklyplan_weeklyplanday_weeklyplansessionlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeeklyPlanDayExercise",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("counter_profile_id", models.CharField(max_length=64)),
                ("display_title", models.CharField(blank=True, default="", max_length=160)),
                ("target_sets", models.PositiveSmallIntegerField(default=3)),
                ("target_reps", models.PositiveSmallIntegerField(default=0)),
                ("duration_sec", models.PositiveIntegerField(blank=True, null=True)),
                ("completed", models.BooleanField(default=False)),
                (
                    "day",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exercises",
                        to="main.weeklyplanday",
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="weeklyplandayexercise",
            constraint=models.UniqueConstraint(
                fields=("day", "sort_order"),
                name="uniq_weekly_plan_day_exercise_order",
            ),
        ),
        migrations.AddField(
            model_name="weeklyplansessionlog",
            name="exercise",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="session_logs",
                to="main.weeklyplandayexercise",
            ),
        ),
        migrations.RunPython(migrate_day_to_exercises, migrations.RunPython.noop),
    ]
