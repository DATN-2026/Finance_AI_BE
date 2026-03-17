from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InvalidatedToken",
            fields=[
                (
                    "id",
                    models.CharField(max_length=64, primary_key=True, serialize=False),
                ),
                ("expiryTime", models.DateTimeField()),
            ],
            options={
                "db_table": "invalidated_tokens",
                "indexes": [
                    models.Index(
                        fields=["expiryTime"], name="invalidated__expiryT_eb047f_idx"
                    )
                ],
            },
        ),
    ]
