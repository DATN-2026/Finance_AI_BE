from django.db import models
import uuid


class User(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.CharField(max_length=255, unique=True)

    password = models.TextField()

    name = models.CharField(max_length=100)

    role = models.CharField(max_length=20, default="user")

    status = models.CharField(max_length=20, default="active")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
