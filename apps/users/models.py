import uuid
import time
from django.contrib.auth.models import AbstractUser
from django.db import models
from .utils import process_image
from django.utils import timezone
from datetime import timedelta

def avatar_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"avatars/{uuid.uuid4()}.{ext}"


def cover_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"covers/{instance.id}_{uuid.uuid4()}.{ext}"


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

    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        null=True,
        blank=True
    )

    cover = models.ImageField(
        upload_to=cover_upload_path,
        null=True,
        blank=True
    )

    avatar_version = models.IntegerField(default=0)
    cover_version = models.IntegerField(default=0)

    is_email_verified = models.BooleanField(default=False)
    is_profile_completed = models.BooleanField(default=False)
    is_verified_for_reset = models.BooleanField(default=False)

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

    def save(self, *args, **kwargs):

        if self.pk:
            old = CustomUser.objects.filter(pk=self.pk).first()
        else:
            old = None

        if self.avatar and (not old or old.avatar != self.avatar):
            self.avatar = process_image(
                self.avatar,
                max_width=400,
                quality=70
            )
            self.avatar.name = f"avatar_{int(time.time())}.jpg"
            self.avatar_version += 1

        if self.cover and (not old or old.cover != self.cover):
            self.cover = process_image(
                self.cover,
                max_width=1200,
                quality=75
            )
            self.cover.name = f"cover_{int(time.time())}.jpg"
            self.cover_version += 1

        super().save(*args, **kwargs)


class UserSession(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    device_id = models.CharField(max_length=255)

    refresh_token = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.device_id}"


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
        return timezone.now() > self.created_at + timedelta(seconds=60)

    def __str__(self):
        return f"{self.email} - {self.code}"