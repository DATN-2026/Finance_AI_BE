from django.db import models


class InvalidatedToken(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    expiryTime = models.DateTimeField()

    class Meta:
        db_table = "invalidated_tokens"
        indexes = [
            models.Index(fields=["expiryTime"]),
        ]
