from django.urls import path
from .views import (app_start,
                    logs)

urlpatterns = [
    path("app/start/", app_start),
    path('logs/', logs),
]