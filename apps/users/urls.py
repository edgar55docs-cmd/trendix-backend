from django.urls import path
from .views import register, app_start, logs

urlpatterns = [

    path("auth/register/", register),
    path("app/start/", app_start),
    path("logs/", logs),
]