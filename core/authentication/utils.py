import secrets
import string


def generate_password(length: int = 8) -> str:
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*()-_=+[]{}<>?/|~"
    all_chars = upper + lower + digits + special

    # ensure at least one of each category
    pw = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    for _ in range(length - len(pw)):
        pw.append(secrets.choice(all_chars))

    secrets.SystemRandom().shuffle(pw)
    return "".join(pw)
