# Generated manually for Plank exercise

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_remove_activeworkout_unique_active_workout_per_player_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='playerstats',
            name='planks_total',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerstats',
            name='max_plank_hold_seconds',
            field=models.IntegerField(default=0),
        ),
    ]
