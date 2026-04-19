from django.urls import path
from .views import register, app_start, logs, google_auth, apple_auth

urlpatterns = [

    path("auth/register/", register),
    path("app/start/", app_start),
    path("logs/", logs),
    path("auth/google/", google_auth),
    path("auth/apple/", apple_auth),
]