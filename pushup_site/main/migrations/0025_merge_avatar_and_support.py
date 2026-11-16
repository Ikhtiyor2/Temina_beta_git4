# Merge parallel branches: telegram/avatar and support/institution

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0023_player_avatar_url_length"),
        ("main", "0024_rename_main_suppor_thread__b4d9c2_idx_main_suppor_thread__3e29ef_idx_and_more"),
    ]

    operations = []
