# Generated manually for UZ default country

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0018_competitive_badges_prizes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="institution",
            name="country",
            field=models.CharField(default="UZ", max_length=80),
        ),
    ]
