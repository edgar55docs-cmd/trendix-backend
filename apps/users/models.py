from django.contrib.auth.models import AbstractUser
from django.db import models
import random

class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)

    language = models.CharField(max_length=5, default='en')
    name = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    cover = models.ImageField(upload_to="covers/", null=True, blank=True)

    is_email_verified = models.BooleanField(default=False)

    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    apple_id = models.CharField(max_length=255, null=True, blank=True)
    provider = models.CharField(max_length=20, default="email")

    created_at = models.DateTimeField(auto_now_add=True)

    # 🔥 LOGIN EMAIL-ով
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class OTP(models.Model):
    email = models.EmailField(null=True, blank=True)
    code = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)

    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    def generate_code(self):
        return str(random.randint(100000, 999999))

    def __str__(self):
        return f"{self.email} - {self.code}"