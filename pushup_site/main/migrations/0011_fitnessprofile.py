# Generated for AI Coach fitness profile

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0010_add_plank_stats'),
    ]

    operations = [
        migrations.CreateModel(
            name='FitnessProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('height_cm', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('weight_kg', models.FloatField(blank=True, null=True)),
                ('target_weight_kg', models.FloatField(blank=True, null=True)),
                ('goals', models.JSONField(blank=True, default=list)),
                ('muscle_focus', models.JSONField(blank=True, default=list)),
                ('health_limits', models.JSONField(blank=True, default=list)),
                ('equipment', models.JSONField(blank=True, default=list)),
                ('fitness_level', models.CharField(blank=True, choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')], default='beginner', max_length=20)),
                ('activity_level', models.CharField(blank=True, choices=[('sedentary', 'Sedentary'), ('light', 'Light'), ('moderate', 'Moderate'), ('active', 'Active'), ('very_active', 'Very Active')], default='moderate', max_length=20)),
                ('workouts_per_week', models.PositiveSmallIntegerField(blank=True, default=3, null=True)),
                ('motivation', models.JSONField(blank=True, default=list)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='fitness_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Fitness profile',
                'verbose_name_plural': 'Fitness profiles',
            },
        ),
    ]
