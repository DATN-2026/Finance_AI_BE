from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0003_alter_aichatmessage_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="aichatmessage",
            name="deleted_by_user_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="aichatmessage",
            name="deleted_by_admin_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="aichatmessage",
            name="purge_after",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
