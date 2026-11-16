from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0017_competitive_platform"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayerBadge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120)),
                ("icon", models.CharField(blank=True, default="", max_length=32)),
                ("earned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="badges",
                        to="main.player",
                    ),
                ),
                (
                    "season",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="badges",
                        to="main.season",
                    ),
                ),
            ],
            options={"ordering": ["-earned_at"]},
        ),
        migrations.CreateModel(
            name="SeasonPrizeTier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rank_from", models.PositiveIntegerField()),
                ("rank_to", models.PositiveIntegerField()),
                (
                    "prize_type",
                    models.CharField(
                        choices=[("virtual", "Virtual"), ("physical", "Physical")],
                        default="virtual",
                        max_length=16,
                    ),
                ),
                ("description", models.TextField(blank=True, default="")),
                (
                    "fulfillment_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("claimed", "Claimed"),
                            ("shipped", "Shipped"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "season",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prize_tiers",
                        to="main.season",
                    ),
                ),
            ],
        ),
    ]
