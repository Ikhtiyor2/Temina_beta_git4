from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0021_player_email_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="telegram_id",
            field=models.BigIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="player",
            name="telegram_username",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
