from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0022_support_thread_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="institution",
            name="name_en",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="institution",
            name="name_uz",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
    ]
