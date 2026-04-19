from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True
    )

    email = models.EmailField(unique=True)

    language = models.CharField(max_length=5, default='en')

    name = models.CharField(max_length=255, null=True, blank=True)

    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    cover = models.ImageField(upload_to="covers/", null=True, blank=True)

    is_email_verified = models.BooleanField(default=False)

    google_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    apple_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    provider = models.CharField(max_length=20, default="email")

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class OTP(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)

    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    @staticmethod
    def generate_code():
        import random
        return str(random.randint(100000, 999999))

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"{self.email} - {self.code}"