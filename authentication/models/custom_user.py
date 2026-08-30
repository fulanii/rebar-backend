"""The project's user model. Email is the login; there is no username."""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field must be set.")
        if not extra_fields.get("first_name"):
            raise ValueError("Users must have a first name.")
        if not extra_fields.get("last_name"):
            raise ValueError("Users must have a last name.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    class AuthProvider(models.TextChoices):
        EMAIL = "email", "Email"
        GOOGLE = "google", "Google"

    username = None

    email = models.EmailField(unique=True, blank=False)
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    phone_number = models.CharField(max_length=15, blank=True, default="")

    sessions_revoked_at = models.DateTimeField(null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False, db_index=True)

    auth_provider = models.CharField(
        max_length=15,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
