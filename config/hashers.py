from django.contrib.auth.hashers import BCryptPasswordHasher


class BCrypt10PasswordHasher(BCryptPasswordHasher):
    rounds = 10
