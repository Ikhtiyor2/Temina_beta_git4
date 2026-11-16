# Subscription model for RevenueCat-based premium access.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0016_weeklyplandayexercise"),
    ]

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(default="revenuecat", max_length=20)),
                ("app_user_id", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("entitlement_id", models.CharField(blank=True, default="", max_length=120)),
                ("product_id", models.CharField(blank=True, default="", max_length=160)),
                ("store", models.CharField(blank=True, default="", max_length=40)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("expired", "Expired"),
                            ("canceled", "Canceled"),
                            ("grace_period", "Grace period"),
                            ("paused", "Paused"),
                        ],
                        default="expired",
                        max_length=20,
                    ),
                ),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("auto_renewing", models.BooleanField(default=False)),
                ("last_event_id", models.CharField(blank=True, default="", max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Subscription",
                "verbose_name_plural": "Subscriptions",
            },
        ),
    ]
