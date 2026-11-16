from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0022_player_telegram"),
    ]

    operations = [
        migrations.AlterField(
            model_name="player",
            name="avatar_url",
            field=models.URLField(blank=True, default="", max_length=512),
        ),
    ]
