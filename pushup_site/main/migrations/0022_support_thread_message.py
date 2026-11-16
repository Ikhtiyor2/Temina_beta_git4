from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0021_player_email_verified"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportThread",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=200)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("general", "General"),
                            ("technical", "Technical"),
                            ("billing", "Billing"),
                            ("account", "Account"),
                        ],
                        default="general",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("waiting_staff", "Waiting staff"),
                            ("waiting_user", "Waiting user"),
                            ("closed", "Closed"),
                        ],
                        default="waiting_staff",
                        max_length=20,
                    ),
                ),
                ("unread_by_user", models.PositiveIntegerField(default=0)),
                ("last_message_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_threads",
                        to="main.player",
                    ),
                ),
            ],
            options={
                "ordering": ["-last_message_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SupportMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "sender_type",
                    models.CharField(
                        choices=[("user", "User"), ("staff", "Staff"), ("system", "System")],
                        default="user",
                        max_length=16,
                    ),
                ),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "sender_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="main.supportthread",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="supportthread",
            index=models.Index(fields=["player", "-last_message_at"], name="main_suppor_player__a8f0e1_idx"),
        ),
        migrations.AddIndex(
            model_name="supportthread",
            index=models.Index(fields=["status", "-updated_at"], name="main_suppor_status_7c2a1b_idx"),
        ),
        migrations.AddIndex(
            model_name="supportmessage",
            index=models.Index(fields=["thread", "created_at"], name="main_suppor_thread__b4d9c2_idx"),
        ),
    ]
