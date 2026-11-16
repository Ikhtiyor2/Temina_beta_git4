# Generated manually for soft email verification

from django.db import migrations, models


def mark_existing_verified(apps, schema_editor):
    Player = apps.get_model("main", "Player")
    Player.objects.all().update(email_verified=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0020_merge_subscription_competitive"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_verified, noop_reverse),
    ]
